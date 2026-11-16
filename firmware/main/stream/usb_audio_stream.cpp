#include "usb_audio_stream.h"
#if CONFIG_NOMI_USB_ASR
#include "pcm_frame.h"
#include "remote_control.h"
#include <cstring>
#include "driver/usb_serial_jtag.h"
#include "esp_log.h"
#include "esp_timer.h"
extern const uint8_t okay_start[] asm("_binary_okay_pcm_start");
extern const uint8_t okay_end[] asm("_binary_okay_pcm_end");
namespace nomi {
namespace { const char *TAG = "usb_audio"; uint32_t clock_ms() { return uint32_t(esp_timer_get_time()/1000); } }
bool UsbAudioStream::start() {
    if (task_) return false;
    replies_=xQueueCreate(8,sizeof(Reply));
    if (!replies_) { state_=3; return false; }
    if (xTaskCreatePinnedToCore(entry, "usb_audio", 8192, this, 4, &task_, 0) != pdPASS) { vQueueDelete(replies_); replies_=nullptr; state_=3; return false; }
    ESP_LOGI(TAG, "USB_ASR_READY; microphone OFF until host starts; no device ASR; ctl ACK1 remote control supported");
    return true;
}
bool UsbAudioStream::reply(const char *text, size_t size, bool spoken, uint32_t token, uint32_t sequence) {
    if (!replies_ || !text || !size || size>=120) return false;
    Reply item{}; item.size=size; item.spoken=spoken; item.token=token; item.sequence=sequence; std::memcpy(item.text,text,size);
    return xQueueSend(replies_,&item,0)==pdTRUE;
}
void UsbAudioStream::speech_event(const char *event, uint32_t token, uint32_t sequence) {
    if (!token) { token=speech_token_; sequence=speech_sequence_; }
    const auto digest=frame_hash(token,sequence,0,reinterpret_cast<const uint8_t *>(event),std::strlen(event));
    char line[100];
    const int n=std::snprintf(line,sizeof(line),"\n@NOMI_SAY1 %08lx %08lx %s %08lx\n",
                             (unsigned long)token,(unsigned long)sequence,event,(unsigned long)digest);
    if (n>0 && size_t(n)<sizeof(line)) usb_serial_jtag_write_bytes(line,n,pdMS_TO_TICKS(20));
}
void UsbAudioStream::send_replies() {
    Reply item;
    for (int i=0;i<4 && xQueueReceive(replies_,&item,0)==pdTRUE;++i) {
        usb_serial_jtag_write_bytes(item.text,item.size,pdMS_TO_TICKS(20));
        if (item.spoken && session_active(item.token)) {
            if (!playback_.active() && !speech_pending_) {
                speech_pending_=true; speech_token_=item.token; speech_sequence_=item.sequence;
            } else speech_event("BUSY",item.token,item.sequence);
        }
    }
}
void UsbAudioStream::on(uint32_t token, unsigned channel) {
    if (!task_ || !token || (channel != 1 && channel != 2)) return;
    channel_ = channel; heartbeat_ = clock_ms(); token_ = token;
}
void UsbAudioStream::off() { token_ = 0; }
void UsbAudioStream::ping(uint32_t token) { if (token && token == token_) heartbeat_ = clock_ms(); }
bool UsbAudioStream::session_active(uint32_t token) const { return token && token==token_ && clock_ms()-heartbeat_.load()<=2000; }
void UsbAudioStream::status() const { ESP_LOGI(TAG, "state=%u frames=%lu mic=%u (PCM16LE/16000Hz/mono; 2s heartbeat lease)", state(), (unsigned long)frames_.load(), unsigned(channel_.load())); }
void UsbAudioStream::run() {
    int16_t stereo[stream_samples*2], mono[stream_samples];
    char line[1024];
    for (;;) {
        send_replies();
        const uint32_t session = token_;
        if (!session) { vTaskDelay(pdMS_TO_TICKS(20)); continue; }
        state_ = 1; frames_ = 0;
        playback_.cancel(audio_);
        bool bad = audio_.open() != ESP_OK;
        uint32_t sequence = 0, observed = audio_.overflows();
        size_t filled = 0; unsigned empty = 0, warmup = 10;
        const unsigned channel = channel_;
        while (!bad && token_ == session) {
            send_replies();
            if (clock_ms()-heartbeat_.load() > 2000) { ESP_LOGW(TAG, "Host heartbeat expired; stopping microphone"); break; }
            size_t received = 0;
            const auto result = audio_.read(stereo+filled/2, sizeof(stereo)-filled, &received);
            if ((result != ESP_OK && result != ESP_ERR_TIMEOUT) || received % 4 || received > sizeof(stereo)-filled) { bad=true; break; }
            if (!received) { if (++empty >= 5) bad=true; continue; }
            empty = 0; filled += received;
            if (filled != sizeof(stereo)) continue;
            filled = 0;
            if (warmup) { --warmup; observed=audio_.overflows(); continue; }
            if (audio_.overflows() != observed) { bad=true; break; }
            for (size_t i=0; i<stream_samples; ++i) mono[i] = stereo[i*2+channel-1];
            if (speech_pending_) {
                speech_pending_=false;
                if (speech_token_==session) {
                    if (!playback_.begin(audio_,reinterpret_cast<const int16_t *>(okay_start),size_t(okay_end-okay_start)/2)) {
                        speech_event("ERROR"); bad=true; break;
                    }
                    speech_event("START");
                }
            }
            const bool guarded=playback_.active();
            if (guarded) {
                std::memset(mono,0,sizeof(mono)); // Never stream our own reply back into ASR.
                if (!playback_.pump(audio_,stream_samples)) { speech_event("ERROR"); bad=true; break; }
            }

            const auto size = encode_frame(line, sizeof(line), session, sequence++, channel, mono, stream_samples, guarded?1:0);
            if (!size || token_ != session) break;
            // Finite timeout: a vanished/slow host must never block capture indefinitely.
            if (usb_serial_jtag_write_bytes(line, size, pdMS_TO_TICKS(20)) != int(size)) { bad=true; break; }
            ++frames_; state_ = 2;
            if (guarded && !playback_.active()) speech_event("DONE");
        }
        playback_.cancel(audio_); speech_pending_=false;
        audio_.close();
        uint32_t expected = session;
        token_.compare_exchange_strong(expected, 0); // Do not erase a newer host's request.
        state_ = bad ? 3 : 0;
        if (bad) ESP_LOGE(TAG, "STREAM_FAULT: init/I2S overflow/read/USB backpressure; microphone stopped; restart host");
        else ESP_LOGI(TAG, "STREAM_STOPPED; microphone OFF");
    }
}
}
#endif
