#include "wake_word_controller.h"
#include "afe_input.h"
#include "sdkconfig.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <cmath>
#include <algorithm>
#include "esp_system.h"
#include <cstdlib>
#include <initializer_list>
#include <cstring>

extern const uint8_t okay_start[] asm("_binary_okay_pcm_start");
extern const uint8_t okay_end[] asm("_binary_okay_pcm_end");
namespace nomi {
namespace { const char *TAG = "wake"; constexpr EventBits_t FETCH_DONE = BIT0; }
const char *WakeWordController::profile()
{
#if CONFIG_NOMI_VOICE_COMMANDS
    return "OFFLINE_COMMANDS_MultiNet7_xiaomi_configured_NOT_WakeNet";
#elif CONFIG_NOMI_WAKE_BENCHMARK
    return "BENCHMARK_xiaoai_tongxue_NOT_xiaomi";
#else
    return "AUDIO_AFE_ONLY_xiaomi_model_unavailable";
#endif
}
bool WakeWordController::start()
{
    if (capture_task_) return false;
    requests_ = xQueueCreate(1, sizeof(Request));
    events_ = xQueueCreate(4, sizeof(WakeEvent));
    voice_events_ = xQueueCreate(8, sizeof(VoiceEvent));
    sync_ = xEventGroupCreate();
#if CONFIG_NOMI_VOICE_COMMANDS
    sayings_=xQueueCreate(1,sizeof(uint32_t));
    if(!sayings_)goto failed;
#endif
    if (!requests_ || !events_ || !voice_events_ || !sync_) goto failed;
    if (xTaskCreatePinnedToCore(fetch_entry, "wake_fetch", 8192, this, 3, &fetch_task_, 1) != pdPASS) goto failed;
    if (xTaskCreatePinnedToCore(capture_entry, "wake_capture", 8192, this, 4, &capture_task_, 0) != pdPASS) goto failed;
    ESP_LOGW(TAG, "profile=%s; local audio only, no network; see VOICE_READY for active command recognition", profile());
    enable(true);
    return true;
failed:
    if (fetch_task_) { vTaskDelete(fetch_task_); fetch_task_ = nullptr; }
    if (requests_) { vQueueDelete(requests_); requests_ = nullptr; }
    if (events_) { vQueueDelete(events_); events_ = nullptr; }
    if (voice_events_) { vQueueDelete(voice_events_); voice_events_ = nullptr; }
    if (sync_) { vEventGroupDelete(sync_); sync_ = nullptr; }
#if CONFIG_NOMI_VOICE_COMMANDS
    if(sayings_){vQueueDelete(sayings_);sayings_=nullptr;}
#endif
    ESP_LOGE(TAG, "Task/queue allocation failed; face remains available");
    return false;
}
void WakeWordController::enable(bool enabled)
{
    if (!requests_) { ESP_LOGE(TAG, "Controller not started"); return; }
    Request request{enabled, epoch_.fetch_add(1) + 1};
    xQueueOverwrite(requests_, &request);
    ESP_LOGI(TAG, "Request %s epoch=%lu", enabled ? "enable/reinitialize" : "disable", (unsigned long)request.epoch);
}
bool WakeWordController::poll(WakeEvent &event)
{
    return events_ && xQueueReceive(events_, &event, 0) == pdTRUE;
}
bool WakeWordController::poll_voice(VoiceEvent &event)
{
    while(voice_events_ && xQueueReceive(voice_events_, &event, 0)==pdTRUE) {
        if(!voice_guarded())return true;
    }
    return false;
}
bool WakeWordController::say_okay(uint32_t expected_epoch) {
#if CONFIG_NOMI_VOICE_COMMANDS
    if(!sayings_ || expected_epoch!=epoch_ || faulted() || state_!=WakeState::Monitoring) return false;
    bool expected=false;
    if(!reply_muted_.compare_exchange_strong(expected,true))return false;
    if(xQueueSend(sayings_,&expected_epoch,0)!=pdTRUE){reply_muted_=false;return false;}
    return true;
#else
    (void)expected_epoch; return false;
#endif
}
void WakeWordController::fault(const char *stage)
{
    failed_ = true; stop_ = true; state_ = WakeState::Fault;
    ESP_LOGE(TAG, "Audio/detector fault: %s; fail closed, use wake reinit", stage);
}
bool WakeWordController::initialize()
{
    ++attempts_; state_ = WakeState::Starting;
    failed_ = false; detected_ = false; stop_ = false;
#if CONFIG_NOMI_VOICE_COMMANDS
    afe_peak_=afe_rms_=afe_zero_=cache_samples_=0;
#endif
    blocks_ = fetched_ = timeouts_ = overflows_ = vad_speech_ = 0;
    for (int i=0; i<2; ++i) { peak_[i]=0; rms_[i]=0; clipped_[i]=0; }
    char *model_name = nullptr;
#if CONFIG_NOMI_WAKE_BENCHMARK
    models_ = esp_srmodel_init("model");
    if (!models_ || models_->num != 1) { fault("expected exactly one benchmark model"); return false; }
    model_name = esp_srmodel_filter(models_, "wn9_xiaoaitongxue", nullptr);
    // This pinned SR helper returns a malloc-owned string, not a borrowed view.
    char *words = model_name ? esp_srmodel_get_wake_words(models_, model_name) : nullptr;
    if (!model_name || std::strcmp(model_name, "wn9_xiaoaitongxue") || !words || std::strcmp(words, "小爱同学")) {
        std::free(words); fault("model identity mismatch"); return false;
    }
    ESP_LOGW(TAG, "BENCHMARK_ONLY model=%s phrase=%s; NOT 小米同学", model_name, words);
    std::free(words);
#endif
#if CONFIG_NOMI_VOICE_COMMANDS
    models_ = esp_srmodel_init("model");
    detector_ready_=recognizer_.open(models_);
    if(!detector_ready_) {
        recognizer_.close();
        ESP_LOGE(TAG,"DETECTOR_DISABLED: model/selftest failed; raw/AFE audio diagnostics stay available, no voice actions");
    }
#endif
    auto *cfg = afe_config_init("M", models_, AFE_TYPE_SR, AFE_MODE_LOW_COST);
    if (!cfg) { fault("AFE config allocation"); return false; }
    cfg->aec_init = false; cfg->se_init = false;
    cfg->ns_init = true; cfg->vad_init = true;
#if CONFIG_NOMI_VOICE_COMMANDS
    cfg->ns_init = false; // Official SR recommendation: avoid distortion before command recognition.
#endif
    cfg->vad_model_name = nullptr; // WebRTC VAD; no VADNet model. Command recognition is separate.
    cfg->wakenet_init = model_name != nullptr;
    cfg->wakenet_model_name = model_name; cfg->wakenet_model_name_2 = nullptr;
    cfg->agc_init = false; cfg->debug_init = false;
    cfg->memory_alloc_mode = AFE_MEMORY_ALLOC_MORE_PSRAM;
    cfg->afe_perferred_core = 0; cfg->afe_perferred_priority = 3;
    // Pinned ESP-SR 2.0.1 single-mic ring units are 1024 bytes, NOT feed chunks.
    // VAD retains (speech + delay) * 16kHz * sizeof(int16_t) = 8192 bytes.
    // The old 5-unit (5120-byte) ring exhausted its writable space after five
    // fetches. Keep headroom for retained history, fetch and producer scheduling.
    cfg->vad_min_speech_ms = 128; cfg->vad_delay_ms = 128;
    cfg->afe_ringbuf_size = 50;
    ESP_LOGI(TAG, "AFE_BUFFER ring_units=%d vad_speech_ms=%d vad_delay_ms=%d",
             cfg->afe_ringbuf_size, cfg->vad_min_speech_ms, cfg->vad_delay_ms);
    afe_ = esp_afe_handle_from_config(cfg);
    if (afe_) afe_data_ = afe_->create_from_config(cfg);
    afe_config_free(cfg);
    if (!afe_ || !afe_data_) { fault("AFE initialization"); return false; }
    chunk_ = afe_->get_feed_chunksize(afe_data_);
    if (chunk_ < 1 || chunk_ > 1024 || afe_->get_feed_channel_num(afe_data_) != 1 ||
        afe_->get_samp_rate(afe_data_) != 16000 || afe_->get_fetch_channel_num(afe_data_) != 1) {
        fault("AFE PCM contract"); return false;
    }
    stereo_ = static_cast<int16_t *>(heap_caps_malloc(chunk_*4, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    mono_ = static_cast<int16_t *>(heap_caps_malloc(chunk_*2, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (!stereo_ || !mono_) { fault("PCM allocation"); return false; }
    if (audio_.open() != ESP_OK) { fault("ES7210/ES8311 setup"); return false; }
    afe_->print_pipeline(afe_data_);
    ESP_LOGI(TAG, "AFE_READY feed=%d samples, 16000Hz mono PCM16 MIC1; MIC2 diagnostics only; capture starts locally", chunk_);
    xEventGroupClearBits(sync_, FETCH_DONE);
    fetch_started_ = true;
    xTaskNotifyGive(fetch_task_);
#if CONFIG_NOMI_VOICE_COMMANDS
    state_=detector_ready_?WakeState::Monitoring:WakeState::Fault;
#else
    state_=WakeState::Monitoring;
#endif
    return true;
}
bool WakeWordController::cleanup()
{
    stop_ = true;
#if CONFIG_NOMI_VOICE_COMMANDS
    trace_.off();
    player_.cancel(audio_);reply_muted_=false;reply_release_at_=0;
    if(sayings_)xQueueReset(sayings_);
#endif
    audio_.close(); // capture owner: stop hardware even if AFE cannot shut down.
    // The fetch worker has bounded waits. Never destroy an object used by another task.
    if (fetch_started_ && !(xEventGroupWaitBits(sync_, FETCH_DONE, pdTRUE, pdFALSE, pdMS_TO_TICKS(3000)) & FETCH_DONE)) {
        fault("fetch stop timeout; reboot required, resources retained to prevent use-after-free");
        return false;
    }
    fetch_started_ = false;
    if (afe_data_) { afe_->destroy(afe_data_); afe_data_ = nullptr; }
    afe_ = nullptr;
#if CONFIG_NOMI_VOICE_COMMANDS
    recognizer_.close();detector_ready_=false;
#endif
    if (models_) { esp_srmodel_deinit(models_); models_ = nullptr; }
    heap_caps_free(stereo_); heap_caps_free(mono_); stereo_ = mono_ = nullptr;
    return true;
}
void WakeWordController::capture_loop()
{
    Request request;
    while (xQueueReceive(requests_, &request, portMAX_DELAY) == pdTRUE) {
        if (!request.enabled) { state_ = WakeState::Disabled; ESP_LOGI(TAG, "MIC_DISABLED; no capture"); continue; }
        session_epoch_ = request.epoch;
        if (initialize()) {
            const size_t required = chunk_*4;
            size_t filled = 0; unsigned no_data = 0; int warmup = 3200;
            uint32_t observed_overflows = audio_.overflows();
            while (epoch_ == session_epoch_ && !failed_) {
                size_t received = 0;
                const auto result = audio_.read(stereo_ + filled/2, required-filled, &received);
                if ((result != ESP_OK && result != ESP_ERR_TIMEOUT) || received % 4 || received > required-filled) {
                    fault("I2S read/alignment"); break;
                }
                if (!received) { ++timeouts_; if (++no_data >= 5) { fault("I2S stalled"); break; } continue; }
                no_data = 0; filled += received;
                if (filled != required) continue;
                filled = 0;
                overflows_ = audio_.overflows();
                if (warmup > 0) { warmup -= chunk_; observed_overflows = overflows_; continue; }
                if (overflows_ != observed_overflows) { fault("I2S DMA overflow; discontinuous PCM discarded"); break; }
                PcmLevel level;
                if (!unpack_pcm(stereo_, chunk_*2, mono_, chunk_, level)) { fault("PCM deinterleave"); break; }
                for (unsigned ch=0; ch<2; ++ch) {
                    if (level.peak[ch] > peak_[ch]) peak_[ch] = level.peak[ch];
                    rms_[ch] = uint32_t(std::sqrt(double(level.energy[ch])/chunk_));
                    clipped_[ch].fetch_add(level.clipped[ch]);
                }
#if CONFIG_NOMI_VOICE_COMMANDS
                trace_.feed(1,mono_,chunk_,reply_muted_);
                uint32_t requested_epoch=0;
                if(xQueueReceive(sayings_,&requested_epoch,0)==pdTRUE) {
                    if(requested_epoch!=session_epoch_ || epoch_!=session_epoch_)break;
                    if(!player_.begin(audio_,reinterpret_cast<const int16_t *>(okay_start),size_t(okay_end-okay_start)/2)) {
                        fault("speaker begin");break;
                    }
                    reply_release_at_=0;
                    ESP_LOGI(TAG,"LOCAL_REPLY_START; recognition guarded, PA enabled");
                }
                if(reply_muted_) {
                    std::memset(mono_,0,chunk_*sizeof(int16_t));
                    const bool was_playing=player_.active();
                    if(!player_.pump(audio_,chunk_)){fault("speaker write");break;}
                    const auto now=uint64_t(esp_timer_get_time()/1000);
                    // Drain the bounded AFE ring/history with silence before decoder resumes.
                    if(was_playing && !player_.active())reply_release_at_=now+2000;
                    if(reply_release_at_ && now>=reply_release_at_) {
                        reply_release_at_=0;reply_muted_=false;
                        ESP_LOGI(TAG,"LOCAL_REPLY_DONE; VOICE_LISTEN_READY");
                    }
                }
#endif
                ++blocks_;
                feeding_ = true;
                const int fed = afe_->feed(afe_data_, mono_);
                feeding_ = false;
                // In this pinned library, a full ring returns zero (not a negative error).
                // Fail immediately rather than silently discarding PCM until fetch stalls.
                if (fed <= 0) { fault("AFE feed rejected PCM (full ring/error)"); break; }
            }
        }
        if (!cleanup()) { for (;;) vTaskDelay(pdMS_TO_TICKS(1000)); }
        if (!failed_) state_ = WakeState::Disabled;
    }
}
void WakeWordController::fetch_loop()
{
    for (;;) {
#if CONFIG_NOMI_VOICE_COMMANDS
        bool muted_last=false;
#endif
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        unsigned failures = 0;
        while (!stop_ || feeding_) {
            auto *result = afe_->fetch_with_delay(afe_data_, pdMS_TO_TICKS(100));
            if (stop_) { if (!feeding_) break; vTaskDelay(pdMS_TO_TICKS(1)); continue; }
            if (!result || result->ret_value != ESP_OK) {
                if (++failures >= 50 && !failed_) fault("AFE fetch stalled");
                vTaskDelay(pdMS_TO_TICKS(1));
                continue;
            }
            failures = 0;
            if (result->data_size <= 0 || result->data_size % 2 || result->data_size > 4096) { fault("AFE output format"); continue; }
#if CONFIG_NOMI_VOICE_COMMANDS
            const bool muted=reply_muted_.load();
            if(muted!=muted_last)recognizer_.reset();
            muted_last=muted;
            if(muted) {trace_.feed(2,result->data,size_t(result->data_size)/2,true);++fetched_;continue;}
            if(!consume_afe(result->data,result->data_size,result->vad_cache,result->vad_cache_size,
                [&](const int16_t *pcm,size_t samples,bool cache){
                    uint32_t peak=0;uint64_t energy=0;
                    for(size_t i=0;i<samples;++i){const int32_t x=pcm[i];peak=std::max(peak,uint32_t(x<0?-x:x));energy+=int64_t(x)*x;}
                    if(peak>afe_peak_)afe_peak_=peak;
                    afe_rms_=uint32_t(std::sqrt(double(energy)/samples));if(!peak)++afe_zero_;
                    if(cache)cache_samples_.fetch_add(samples);
                    trace_.feed(2,pcm,samples,false);
                    return !detector_ready_ || recognizer_.consume(pcm,samples,voice_events_,session_epoch_);
                })) {++dropped_;fault("AFE cache/PCM or MultiNet inference/result queue");continue;}
#endif
            ++fetched_;
            if (result->vad_state == VAD_SPEECH) ++vad_speech_;
#if CONFIG_NOMI_WAKE_BENCHMARK
            if (result->wakeup_state == WAKENET_DETECTED && !detected_.exchange(true)) {
                if (epoch_ != session_epoch_ || stop_) continue;
                if (result->wake_word_index != 1 || result->wakenet_model_index != 1) { fault("Unexpected model/word index"); continue; }
                WakeEvent event{session_epoch_, 1, true};
                if (xQueueSend(events_, &event, 0) != pdTRUE) { ++dropped_; fault("Wake event queue full"); continue; }
                state_ = WakeState::Listening;
                ESP_LOGW(TAG, "WAKE_WORD_DETECTED model=wn9_xiaoaitongxue phrase=小爱同学 benchmark_only=1 target_xiaomi_available=0 epoch=%lu", (unsigned long)session_epoch_);
            }
#endif
        }
        xEventGroupSetBits(sync_, FETCH_DONE);
    }
}
void WakeWordController::status() const
{
    ESP_LOGI(TAG, "profile=%s state=%d epoch=%lu init_attempts=%lu blocks=%lu fetched=%lu vad_speech=%lu timeouts=%lu overflows=%lu dropped=%lu",
             profile(), int(state_.load()), (unsigned long)epoch(), (unsigned long)attempts_.load(),
             (unsigned long)blocks_.load(), (unsigned long)fetched_.load(), (unsigned long)vad_speech_.load(),
             (unsigned long)timeouts_.load(), (unsigned long)overflows_.load(), (unsigned long)dropped_.load());
    ESP_LOGI(TAG, "MIC1 peak_hold=%lu rms=%lu clip=%lu; MIC2 peak_hold=%lu rms=%lu clip=%lu (levels only, no PCM logs/files)",
             (unsigned long)peak_[0].load(), (unsigned long)rms_[0].load(), (unsigned long)clipped_[0].load(),
             (unsigned long)peak_[1].load(), (unsigned long)rms_[1].load(), (unsigned long)clipped_[1].load());
#if CONFIG_NOMI_VOICE_COMMANDS
    ESP_LOGI(TAG,"DETECTOR ready=%d; audio capture is independent of model success",int(detector_ready_.load()));
    trace_.status();
    ESP_LOGI(TAG,"AFE_PCM peak_hold=%lu rms=%lu zero_chunks=%lu restored_cache_samples=%lu",
        (unsigned long)afe_peak_.load(),(unsigned long)afe_rms_.load(),(unsigned long)afe_zero_.load(),(unsigned long)cache_samples_.load());
    recognizer_.status();
    ESP_LOGI(TAG, "MULTINET frames=%lu wake=%s", (unsigned long)recognizer_.frames(), CONFIG_NOMI_VOICE_WAKE_LABEL);
#endif
    ESP_LOGI(TAG,"HEAP internal_free=%u internal_largest=%u psram_free=%u psram_largest=%u min_total_free=%u",
        unsigned(heap_caps_get_free_size(MALLOC_CAP_INTERNAL)),unsigned(heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL)),
        unsigned(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)),unsigned(heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM)),unsigned(esp_get_minimum_free_heap_size()));
    // Snapshot includes AFE's own tasks and both idle tasks, not just our two workers.
    static TaskStatus_t snapshot[24];
    configRUN_TIME_COUNTER_TYPE total = 0;
    const auto count = uxTaskGetSystemState(snapshot, 24, &total);
    if (!count) ESP_LOGW(TAG, "Task snapshot capacity exceeded; CPU/stack sample unavailable");
    for (UBaseType_t i=0; i<count; ++i) {
        const auto &info = snapshot[i];
        ESP_LOGI(TAG, "task=%s stack_free_bytes=%u runtime_us=%lu (cumulative, not CPU percent)",
                 info.pcTaskName, unsigned(info.usStackHighWaterMark), (unsigned long)info.ulRunTimeCounter);
    }
}
}
