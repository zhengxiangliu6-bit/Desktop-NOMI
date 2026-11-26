#include "face_model.h"
#include "wifi_voice.h"
#include "face_catalog.h"
#include "face_view.h"
#include "wake_word_controller.h"
#include "nomi_panel.h"
#include "usb_audio_stream.h"
#include "remote_control.h"
#include <cstdio>
#include "esp_check.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "esp_psram.h"
#include "driver/usb_serial_jtag.h"
#include "driver/usb_serial_jtag_vfs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <cstring>

namespace {
const char *TAG = "nomi";
uint64_t now_ms() { return uint64_t(esp_timer_get_time()) / 1000; }
uint32_t lv_clock() { return uint32_t(now_ms()); }
nomi::FaceModel model;
nomi::FaceView view;
nomi::WakeWordController wake;
#if CONFIG_NOMI_USB_ASR
nomi::UsbAudioStream usb_audio;
nomi::RemoteControl remote_control;
#endif
nomi::WakeLatch wake_latch;
nomi::VoiceSession voice_session;
bool voice_hold = false;
uint64_t voice_feedback_until = 0;
uint32_t max_frame_gap_ms = 0;
#if CONFIG_NOMI_VOICE_COMMANDS || CONFIG_NOMI_USB_ASR
lv_obj_t *voice_indicator = nullptr;
uint32_t indicator_color = 0;
void update_voice_indicator(uint64_t now, bool demo_active) {
    uint32_t color = 0xe8a26e; // Initialization or demo: voice control unavailable.
#if CONFIG_NOMI_USB_ASR
    const unsigned state = usb_audio.state();
    color = state == 3 ? 0xd64242 : state == 2 ? 0x287cc4 : state == 1 ? 0xe8a26e : 0x8b9199;
    (void)now; (void)demo_active;
#else
    switch (wake.state()) {
    case nomi::WakeState::Fault: color = 0xd64242; break;
    case nomi::WakeState::Disabled: color = 0x8b9199; break;
    case nomi::WakeState::Monitoring:
    case nomi::WakeState::Listening:
        if (!demo_active && !wake.voice_guarded()) color = voice_session.listening(now) ? 0x287cc4 : 0x36865d;
        break;
    default: break;
    }
#endif
    if (color != indicator_color) {
        lv_obj_set_style_bg_color(voice_indicator, lv_color_hex(color), 0); indicator_color = color;
    }
}
#endif
bool demo = false;
unsigned demo_step = 0;
uint64_t demo_at = 0;
const auto &sequence = nomi::face_designs;
void status()
{
#if CONFIG_NOMI_USB_ASR
    usb_audio.status();
#else
    wake.status();
#endif
#if !CONFIG_NOMI_USB_ASR
    ESP_LOGI(TAG, "VOICE_SESSION active=%d; local finite commands only", voice_session.listening(now_ms()));
#endif
    ESP_LOGI(TAG, "uptime_ms=%llu main_stack_free_bytes=%u max_frame_gap_ms=%lu",
             (unsigned long long)now_ms(), unsigned(uxTaskGetStackHighWaterMark(nullptr)), (unsigned long)max_frame_gap_ms);
    ESP_LOGI(TAG, "phase=%d emotion=%d internal_free=%u psram_free=%u min_heap=%u",
             int(model.phase()), int(model.emotion()),
             unsigned(heap_caps_get_free_size(MALLOC_CAP_INTERNAL)),
             unsigned(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)),
             unsigned(esp_get_minimum_free_heap_size()));
}
void command(const char *text, uint64_t now)
{
    if (!std::strcmp(text, "status")) { status(); return; }
#if CONFIG_NOMI_VOICE_COMMANDS
    unsigned long trace_token=0;char trace_tail=0;unsigned trace_channels=3;
    const auto trace_fields=std::sscanf(text,"trace on %8lx %u %c",&trace_token,&trace_channels,&trace_tail);
    if((trace_fields==1 || trace_fields==2) && trace_token && trace_channels>=1 && trace_channels<=3) {wake.trace_on(uint32_t(trace_token),trace_channels);ESP_LOGI(TAG,"TRACE_STARTED: raw MIC1 + restored AFE; host display only");return;}
    if(std::sscanf(text,"trace ping %8lx %c",&trace_token,&trace_tail)==1) {wake.trace_ping(uint32_t(trace_token));return;}
    if(!std::strcmp(text,"trace off")){wake.trace_off();ESP_LOGI(TAG,"TRACE_OFF");return;}
    unsigned score=0;char extra=0;
    if(!std::strncmp(text,"voice threshold",15)) {
        if(std::sscanf(text,"voice threshold %u %c",&score,&extra)!=1 || !wake.request_threshold(score)) {
            ESP_LOGW(TAG,"Use voice threshold N, N=30..95; model score, not accuracy");return;
        }
        voice_session.reset(now);voice_hold=false;model.reset(now);
        ESP_LOGI(TAG,"Threshold requested=%u; wait for VOICE_THRESHOLD_APPLIED; session reset; volatile until reboot",score);return;
    }
#endif
#if CONFIG_NOMI_USB_ASR
    if (!std::strcmp(text, "stream off") || !std::strcmp(text, "wake off")) { usb_audio.off(); return; }
    if (!std::strcmp(text, "stream status")) { usb_audio.status(); return; }
    unsigned long token = 0; unsigned mic = 0; char tail = 0;
    unsigned long seq = 0; char action[12]{}; unsigned spoken=0;
    if (std::sscanf(text,"ctl %8lx %8lx %11s %u %c",&token,&seq,action,&spoken,&tail)==4 && spoken<=1) {
        auto reply=remote_control.apply(uint32_t(token),uint32_t(seq),action,now,usb_audio.session_active(uint32_t(token)),spoken!=0);
        if (reply.effect!=nomi::RemoteEffect::None) {
            wake_latch.clear(); voice_session.reset(now); voice_hold=false; demo=false;
            model.reset(now);
            if (reply.effect==nomi::RemoteEffect::Face) model.command(action,now);
        }
        char ack[120];
        const auto length=nomi::encode_control_ack(ack,sizeof(ack),uint32_t(token),uint32_t(seq),action,reply.status);
        // Queue without blocking UI. The capture owner sends each ACK in one driver call.
        if (length) usb_audio.reply(ack,length,spoken && reply.effect==nomi::RemoteEffect::Face,uint32_t(token),uint32_t(seq));
        return;
    }

    if (std::sscanf(text, "stream on %8lx %u %c", &token, &mic, &tail) == 2) { usb_audio.on(uint32_t(token), mic); return; }
    if (std::sscanf(text, "stream ping %8lx %c", &token, &tail) == 1) { usb_audio.ping(uint32_t(token)); return; }
    if (!std::strncmp(text, "wake ", 5)) { ESP_LOGI(TAG, "USB ASR diagnostic: start/stop with host application, not wake commands"); return; }
#endif
    if (!std::strcmp(text, "wake status")) { wake.status(); return; }
#if CONFIG_NOMI_USB_ASR
    remote_control.clear();
#endif
    voice_session.reset(now); voice_hold = false;
    if (!std::strcmp(text, "wake on") || !std::strcmp(text, "wake reinit") || !std::strcmp(text, "wake off")) {
        wake_latch.clear();
        if (!demo) model.reset(now);
        wake.enable(std::strcmp(text, "wake off") != 0);
        return;
    }
    wake_latch.clear();
    demo = false;
    if (!std::strcmp(text, "demo")) {
        model.reset(now); demo = true; demo_step = 0; demo_at = now;
        ESP_LOGI(TAG, "One demo cycle; any expression command cancels it");
        return;
    }
    if (model.command(text, now)) ESP_LOGI(TAG, "Command accepted: %s (5s TTL)", text);
    else ESP_LOGW(TAG, "Unknown/oversized command; reset to idle");
}
void read_commands(uint64_t now)
{
    static char line[48];
    static size_t used = 0;
    static bool overflow = false;
    char chunk[32];
    // Timeout zero and bounded bytes: a partial line never stalls animation.
    const int count = usb_serial_jtag_read_bytes(chunk, sizeof(chunk), 0);
    for (int i = 0; i < count; ++i) {
        const char c = chunk[i];
        if (c == '\r' || c == '\n') {
            if (used || overflow) {
                line[used] = 0;
                command(overflow ? "" : line, now);
            }
            used = 0; overflow = false;
        } else if (c >= 32 && c <= 126) {
            if (used + 1 < sizeof(line) && !overflow) line[used++] = c;
            else overflow = true;
        }
    }
}
}
extern "C" void app_main()
{
    ESP_LOGI(TAG, "Desktop-NOMI H2; Waveshare ESP32-S3-Touch-LCD-1.85B; local audio/finite command profiles; no LLM/TTS/network");
    ESP_LOGI(TAG, "ESP-IDF %s; LVGL %d.%d.%d", esp_get_idf_version(),
             LVGL_VERSION_MAJOR, LVGL_VERSION_MINOR, LVGL_VERSION_PATCH);
    ESP_LOGI(TAG, "PSRAM initialized=%d size=%u", esp_psram_is_initialized(), unsigned(esp_psram_get_size()));
    usb_serial_jtag_driver_config_t serial = {};
    serial.rx_buffer_size = 256;
#if CONFIG_NOMI_USB_ASR || CONFIG_NOMI_VOICE_COMMANDS
    serial.tx_buffer_size = 4096; // PCM + bounded complete control replies.
#else
    serial.tx_buffer_size = 1024;
#endif
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&serial));
#if CONFIG_NOMI_VOICE_COMMANDS
    // Do not let default polling stdout bypass the driver and inject bytes inside PCM packets.
    usb_serial_jtag_vfs_use_driver();
#endif
    lv_init();
    lv_tick_set_cb(lv_clock);
    nomi_panel_start();
    model = nomi::FaceModel(uint32_t(esp_timer_get_time()));
    model.reset(now_ms());
    view.create();
    view.render(model.update(now_ms()), model.phase());
#if CONFIG_NOMI_VOICE_COMMANDS || CONFIG_NOMI_USB_ASR
    voice_indicator = lv_obj_create(lv_screen_active());
    lv_obj_remove_style_all(voice_indicator);
    lv_obj_remove_flag(voice_indicator, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_size(voice_indicator, 8, 8); lv_obj_set_pos(voice_indicator, 176, 304);
    lv_obj_set_style_radius(voice_indicator, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_opa(voice_indicator, LV_OPA_COVER, 0);
    update_voice_indicator(now_ms(), false);
#endif
    nomi_panel_show();
    ESP_LOGI(TAG, "Commands + Enter: idle blink happy sad curious thinking listening speaking angry surprised sleepy wink love confused demo status");
#if CONFIG_NOMI_USB_ASR
    usb_audio.start();
#elif CONFIG_NOMI_WIFI_VOICE
    nomi::wifi_voice_start();
#else
    wake.start();
#endif
#if CONFIG_NOMI_USB_ASR
    ESP_LOGI(TAG, "USB ASR: microphone OFF until Windows host starts; ctl ACK1 remote control");
#else
    ESP_LOGI(TAG, "Local microphone requested. Commands: wake off | wake on | wake reinit | wake status");
#endif
    status();
    uint64_t previous_frame = 0;
    uint64_t frame_at = 0;
    while (true) {
#if CONFIG_NOMI_WIFI_VOICE
        if (const auto *action = nomi::wifi_voice_poll()) command(action, now_ms());
#endif
        uint64_t now = now_ms();
        read_commands(now);
        nomi::WakeEvent event;
        while (wake.poll(event)) {
            if (wake_latch.accept(event, wake.epoch(), demo)) {
                model.reset(now);
                ESP_LOGI(TAG, "LISTENING_HELD source=benchmark_xiaoai_tongxue; use idle or wake off to leave");
            } else ESP_LOGW(TAG, "Wake UI event ignored (demo, stale generation, or duplicate)");
        }
        nomi::VoiceEvent voice_event;
        while (wake.poll_voice(voice_event)) {
            now = now_ms(); // Serial output may have yielded while inference queued a newer event.
            const auto action = voice_session.accept(voice_event, wake.epoch(), now, demo || wake.faulted(),wake.threshold());
            if (action == nomi::VoiceAction::Wake) {
                wake_latch.clear(); model.reset(now); voice_hold = true;
                wake.say_okay(voice_event.epoch);
                ESP_LOGI(TAG, "WAKE_WORD_DETECTED source=multinet_command id=1 probability=%.3f; window=20s", double(voice_event.probability));
            } else if (action == nomi::VoiceAction::Extend) {
                ESP_LOGI(TAG, "VOICE_SESSION_EXTEND; no repeat playback or face reset");
            } else if (action == nomi::VoiceAction::Expression) {
                const auto *c = nomi::voice_command(voice_event.id);
                voice_hold = false;
                model.reset(now);
                if (!std::strcmp(c->face, "demo")) {
                    command("demo", now);
                } else {
                    model.command(c->face, now);
                    voice_feedback_until = now+5000;
                }
                wake.say_okay(voice_event.epoch);
                ESP_LOGI(TAG, "VOICE_COMMAND_ACCEPTED id=%d action=%s probability=%.3f", c->id, c->face, double(voice_event.probability));
            } else if (action == nomi::VoiceAction::Sleep) {
                voice_hold = false; model.reset(now);
                wake.say_okay(voice_event.epoch);
                ESP_LOGI(TAG, "VOICE_SLEEP id=%d", voice_event.id);
            } else ESP_LOGI(TAG, "VOICE_IGNORED id=%d (asleep/demo/stale/threshold/debounce)", voice_event.id);
        }
        if (voice_session.tick(now) == nomi::VoiceAction::Timeout) {
            voice_hold = false; model.reset(now); ESP_LOGI(TAG, "VOICE_SESSION_TIMEOUT; idle");
        }
#if CONFIG_NOMI_USB_ASR
        if (remote_control.expire(now,usb_audio.session_active(remote_control.token()))) model.reset(now);
        if (remote_control.hold(now) && !demo) model.set_phase(nomi::Phase::Listening,now);
#endif
        if (wake.faulted()) { voice_session.reset(now); if (voice_hold) model.reset(now); voice_hold = false; }
        if (voice_session.listening(now) && !demo && !voice_hold && now >= voice_feedback_until) voice_hold = true;
        if (voice_hold) model.set_phase(nomi::Phase::Listening, now);
        if (wake.faulted() && wake_latch.held()) { wake_latch.clear(); model.reset(now); }
        if (wake_latch.held()) model.set_phase(nomi::Phase::Listening, now);
        if (demo && now >= demo_at) {
            if (demo_step == sizeof(sequence) / sizeof(sequence[0])) {
                demo = false; model.reset(now); voice_session.reset(now); ESP_LOGI(TAG, "Demo complete; idle");
            } else {
                // Isolated previews: previous phase/emotion cannot mask the next one.
                model.reset(now);
                model.command(sequence[demo_step].command, now);
                ESP_LOGI(TAG, "Demo: %s", sequence[demo_step++].command);
                demo_at = now + 3000;
            }
        }
        if (now >= frame_at) {
            if (previous_frame && now - previous_frame > max_frame_gap_ms) max_frame_gap_ms = now - previous_frame;
            previous_frame = now;
#if CONFIG_NOMI_VOICE_COMMANDS || CONFIG_NOMI_USB_ASR
            update_voice_indicator(now, demo);
#endif
            auto frame = model.update(now);
            view.render(frame, model.phase());
            frame_at = now + 20;
        }
        lv_timer_handler();
        // Scheduler yield only: animations/commands use monotonic deadlines.
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}
