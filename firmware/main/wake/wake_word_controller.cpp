#include "wake_word_controller.h"
#include "sdkconfig.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <cmath>
#include <cstdlib>
#include <initializer_list>
#include <cstring>

namespace nomi {
namespace { const char *TAG = "wake"; constexpr EventBits_t FETCH_DONE = BIT0; }
const char *WakeWordController::profile()
{
#if CONFIG_NOMI_WAKE_BENCHMARK
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
    sync_ = xEventGroupCreate();
    if (!requests_ || !events_ || !sync_) goto failed;
    if (xTaskCreatePinnedToCore(fetch_entry, "wake_fetch", 8192, this, 3, &fetch_task_, 1) != pdPASS) goto failed;
    if (xTaskCreatePinnedToCore(capture_entry, "wake_capture", 8192, this, 4, &capture_task_, 0) != pdPASS) goto failed;
    ESP_LOGW(TAG, "profile=%s; TARGET_MODEL_UNAVAILABLE phrase=小米同学; local capture only, no network", profile());
    enable(true);
    return true;
failed:
    if (fetch_task_) { vTaskDelete(fetch_task_); fetch_task_ = nullptr; }
    if (requests_) { vQueueDelete(requests_); requests_ = nullptr; }
    if (events_) { vQueueDelete(events_); events_ = nullptr; }
    if (sync_) { vEventGroupDelete(sync_); sync_ = nullptr; }
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
void WakeWordController::fault(const char *stage)
{
    failed_ = true; stop_ = true; state_ = WakeState::Fault;
    ESP_LOGE(TAG, "Audio/detector fault: %s; fail closed, use wake reinit", stage);
}
bool WakeWordController::initialize()
{
    ++attempts_; state_ = WakeState::Starting;
    failed_ = false; detected_ = false; stop_ = false;
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
    auto *cfg = afe_config_init("M", models_, AFE_TYPE_SR, AFE_MODE_LOW_COST);
    if (!cfg) { fault("AFE config allocation"); return false; }
    cfg->aec_init = false; cfg->se_init = false;
    cfg->ns_init = true; cfg->vad_init = true;
    cfg->vad_model_name = nullptr; // WebRTC VAD; no VADNet model or voice recognition.
    cfg->wakenet_init = model_name != nullptr;
    cfg->wakenet_model_name = model_name; cfg->wakenet_model_name_2 = nullptr;
    cfg->agc_init = false; cfg->debug_init = false;
    cfg->memory_alloc_mode = AFE_MEMORY_ALLOC_MORE_PSRAM;
    cfg->afe_perferred_core = 0; cfg->afe_perferred_priority = 3; cfg->afe_ringbuf_size = 5;
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
    state_ = WakeState::Monitoring;
    return true;
}
bool WakeWordController::cleanup()
{
    stop_ = true;
    audio_.close(); // capture owner: stop hardware even if AFE cannot shut down.
    // The fetch worker has bounded waits. Never destroy an object used by another task.
    if (fetch_started_ && !(xEventGroupWaitBits(sync_, FETCH_DONE, pdTRUE, pdFALSE, pdMS_TO_TICKS(3000)) & FETCH_DONE)) {
        fault("fetch stop timeout; reboot required, resources retained to prevent use-after-free");
        return false;
    }
    fetch_started_ = false;
    if (afe_data_) { afe_->destroy(afe_data_); afe_data_ = nullptr; }
    afe_ = nullptr;
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
                ++blocks_;
                feeding_ = true;
                const int fed = afe_->feed(afe_data_, mono_);
                feeding_ = false;
                if (fed < 0) { fault("AFE feed"); break; }
            }
        }
        if (!cleanup()) { for (;;) vTaskDelay(pdMS_TO_TICKS(1000)); }
        if (!failed_) state_ = WakeState::Disabled;
    }
}
void WakeWordController::fetch_loop()
{
    for (;;) {
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
