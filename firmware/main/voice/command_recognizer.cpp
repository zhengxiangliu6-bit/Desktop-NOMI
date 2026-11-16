#include "command_recognizer.h"
#if CONFIG_NOMI_VOICE_COMMANDS
#include <algorithm>
#include <cstring>
#include "esp_mn_speech_commands.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
namespace nomi {
namespace { const char *TAG = "voice"; }
bool CommandRecognizer::open(srmodel_list_t *models)
{
    frames_ = 0; used_ = 0;
    if (!models || models->num != 2) return false;
    char *name = esp_srmodel_filter(models, "mn7_cn", nullptr);
    if (!name || std::strcmp(name, "mn7_cn")) return false;
    mn_ = esp_mn_handle_from_name(name);
    if (!mn_) return false;
    data_ = mn_->create(name, 4000);
    if (!data_) return false;
    if (mn_->get_samp_rate(data_) != 16000) return false;
    const int chunk = mn_->get_samp_chunksize(data_);
    if (chunk <= 0 || chunk > 1024) return false;
    chunk_ = size_t(chunk);
    buffer_ = static_cast<int16_t *>(heap_caps_malloc(chunk_*sizeof(int16_t), MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if (!buffer_) return false;
    if (esp_mn_commands_alloc(mn_, data_) != ESP_OK) return false;
    commands_allocated_ = true;
    if (esp_mn_commands_clear() != ESP_OK ||
        esp_mn_commands_add(1, CONFIG_NOMI_VOICE_WAKE_PINYIN) != ESP_OK) return false;
    for (const auto &c : voice_commands)
        if (esp_mn_commands_add(c.id, c.pinyin) != ESP_OK) return false;
    if (esp_mn_commands_update()) return false;
    mn_->set_det_threshold(data_, 0.90f);
    mn_->clean(data_);
    ESP_LOGI(TAG, "VOICE_READY engine=MultiNet7 model=mn7_cn wake=%s pinyin=%s chunk=%u threshold=0.90; continuous local command matching, NOT WakeNet",
             CONFIG_NOMI_VOICE_WAKE_LABEL, CONFIG_NOMI_VOICE_WAKE_PINYIN, unsigned(chunk_));
    for (const auto &c : voice_commands) ESP_LOGI(TAG, "VOICE_COMMAND id=%d phrase=%s", c.id, c.label);
    return true;
}
void CommandRecognizer::reset() { used_=0; if(data_) mn_->clean(data_); }
void CommandRecognizer::close()
{
    if (commands_allocated_) { esp_mn_commands_free(); commands_allocated_ = false; }
    if (data_) { mn_->destroy(data_); data_ = nullptr; }
    mn_ = nullptr; heap_caps_free(buffer_); buffer_ = nullptr; used_ = chunk_ = 0;
}
bool CommandRecognizer::consume(const int16_t *pcm, size_t samples, QueueHandle_t events, uint32_t epoch)
{
    if (!data_ || !pcm || !events) return false;
    while (samples) {
        const size_t n = std::min(chunk_-used_, samples);
        std::copy_n(pcm, n, buffer_+used_); used_ += n; pcm += n; samples -= n;
        if (used_ != chunk_) continue;
        used_ = 0;
        const auto state = mn_->detect(data_, buffer_); ++frames_;
        if (state == ESP_MN_STATE_DETECTED) {
            auto *r = mn_->get_results(data_);
            if (!r || r->num < 1 || r->num > ESP_MN_RESULT_MAX_NUM) return false;
            VoiceEvent event{epoch, r->command_id[0], r->prob[0], uint64_t(esp_timer_get_time()/1000)};
            if (xQueueSend(events, &event, 0) != pdTRUE) return false;
            mn_->clean(data_); // New utterance: no duplicate detections from the same decoder result.
        } else if (state == ESP_MN_STATE_TIMEOUT) mn_->clean(data_); // Always return to local detection.
        else if (state != ESP_MN_STATE_DETECTING) return false;
    }
    return true;
}
}
#endif
