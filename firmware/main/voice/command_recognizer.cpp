#include "command_recognizer.h"
#if CONFIG_NOMI_VOICE_COMMANDS
#include <algorithm>
#include <cstring>
#include <cstdio>
#include <cmath>
#include "esp_mn_speech_commands.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "driver/usb_serial_jtag.h"
extern const uint8_t official_start[] asm("_binary_official_command_pcm_start");
extern const uint8_t official_end[] asm("_binary_official_command_pcm_end");
namespace nomi {
namespace { const char *TAG = "voice"; }
bool CommandRecognizer::open(srmodel_list_t *models)
{
    last_us_=max_us_=mean_us_=over_budget_=0;timing_sum_=0;timing_count_=0;selftest_passed_=false;
    frames_ = detections_ = timeouts_ = rejected_ = 0; candidate_id_=0;candidate_score_=0;used_ = 0;
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
    const auto *language=mn_->get_language(data_);
    if(!language || std::strcmp(language,ESP_MN_CHINESE))return false;
    selftest_passed_=self_test();
    if(!install_commands(false) || !selftest_passed_)return false;
    active_=requested_.load();
    mn_->set_det_threshold(data_, threshold());
    mn_->clean(data_);
    esp_mn_active_commands_print(); // Actual model dictionary, not just our requested labels.
    ESP_LOGI(TAG, "VOICE_READY engine=MultiNet7 model=mn7_cn wake=%s pinyin=%s chunk=%u threshold=%.2f; continuous local command matching, NOT WakeNet",
             CONFIG_NOMI_VOICE_WAKE_LABEL, CONFIG_NOMI_VOICE_WAKE_PINYIN, unsigned(chunk_),double(threshold()));
    for (const auto &c : voice_commands) ESP_LOGI(TAG, "VOICE_COMMAND id=%d phrase=%s", c.id, c.label);
    return true;
}
bool CommandRecognizer::install_commands(bool diagnostic) {
    if(esp_mn_commands_clear()!=ESP_OK)return false;
    if(diagnostic) {
        if(esp_mn_commands_add(1,"da kai kong tiao")!=ESP_OK)return false;
    } else {
        if(esp_mn_commands_add(1,CONFIG_NOMI_VOICE_WAKE_PINYIN)!=ESP_OK)return false;
        for(const auto &c:voice_commands)if(esp_mn_commands_add(c.id,c.pinyin)!=ESP_OK)return false;
    }
    return esp_mn_commands_update()==nullptr;
}
bool CommandRecognizer::self_test() {
    if(!install_commands(true))return false;
    mn_->set_det_threshold(data_,0.60f);mn_->clean(data_);
    // Silence negative control, then a known public sample; never enqueue UI events.
    std::fill_n(buffer_,chunk_,0);
    bool silence_ok=true;
    for(unsigned i=0;i<130;++i) {
        const auto state=mn_->detect(data_,buffer_);
        if(state==ESP_MN_STATE_DETECTED){
            auto *r=mn_->get_results(data_);
            if(!r || r->num>0){silence_ok=false;break;}
        }
        if(state==ESP_MN_STATE_TIMEOUT)mn_->clean(data_);
        vTaskDelay(1);
    }
    mn_->clean(data_);
    const size_t samples=size_t(official_end-official_start)/2;
    const auto *pcm=reinterpret_cast<const int16_t *>(official_start);
    bool reference_ok=false;float score=0;
    for(size_t offset=0;offset<samples+16000;offset+=chunk_) {
        std::fill_n(buffer_,chunk_,0);
        if(offset<samples)std::copy_n(pcm+offset,std::min(chunk_,samples-offset),buffer_);
        const auto state=mn_->detect(data_,buffer_);
        if(state==ESP_MN_STATE_DETECTED) {
            auto *r=mn_->get_results(data_);
            if(r && r->num>0 && r->num<=ESP_MN_RESULT_MAX_NUM) {
                score=r->prob[0];reference_ok=r->command_id[0]==1 && std::isfinite(score) && score>=0.60f && score<=1.f;
            }
            break;
        }
        if(state==ESP_MN_STATE_TIMEOUT)break;
        vTaskDelay(1);
    }
    ESP_LOGI(TAG,"MN_SELFTEST %s silence=%d reference=%d score=%.3f; direct public PCM, microphone NOT tested",
             silence_ok&&reference_ok?"PASS":"FAIL",silence_ok,reference_ok,double(score));
    mn_->clean(data_);return silence_ok && reference_ok;
}
void CommandRecognizer::report_result(const esp_mn_results_t *r,const char *source) {
    if(!r || r->num<1 || r->num>ESP_MN_RESULT_MAX_NUM)return;
    candidate_id_=r->command_id[0];candidate_score_=r->prob[0];
    const auto *cmd=voice_command(candidate_id_);
    const char *label=candidate_id_==1?CONFIG_NOMI_VOICE_WAKE_LABEL:cmd?cmd->label:"unknown_id";
    char line[240];
    const int size=std::snprintf(line,sizeof(line),"\n@NRES1 id=%d label=%s score=%.3f gate=%.2f source=%s\n",
        candidate_id_.load(),label,double(candidate_score_),double(threshold()),source);
    if(size>0 && size_t(size)<sizeof(line))usb_serial_jtag_write_bytes(line,size,pdMS_TO_TICKS(2));

}
void CommandRecognizer::status() const {
    ESP_LOGI(TAG,"MN_RUNTIME selftest=%s infer_wall_last_us=%lu mean_us=%lu max_us=%lu frame_budget_us=%u over_budget=%lu",
        selftest_passed_?"PASS":"NOT_PASSED",(unsigned long)last_us_.load(),(unsigned long)mean_us_.load(),
        (unsigned long)max_us_.load(),unsigned(chunk_*1000000/16000),(unsigned long)over_budget_.load());
    ESP_LOGI(TAG,"MN_DIAGNOSTIC detected=%lu timeouts=%lu below_gate=%lu last_id=%d last_score=%.3f active_threshold=%.2f requested=%u",
        (unsigned long)detections_.load(),(unsigned long)timeouts_.load(),(unsigned long)rejected_.load(),candidate_id_.load(),
        double(candidate_score_),double(threshold()),requested_.load());
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
    if(requested_!=active_) {
        const auto next=requested_.load();
        mn_->set_det_threshold(data_,float(next)/100.f);active_=next;reset();
        ESP_LOGI(TAG,"VOICE_THRESHOLD_APPLIED score=%.2f; decoder reset; not an accuracy percentage",double(threshold()));
    }
    while (samples) {
        const size_t n = std::min(chunk_-used_, samples);
        std::copy_n(pcm, n, buffer_+used_); used_ += n; pcm += n; samples -= n;
        if (used_ != chunk_) continue;
        used_ = 0;
        const auto begin=esp_timer_get_time();
        const auto state = mn_->detect(data_, buffer_); ++frames_;
        const uint32_t elapsed=uint32_t(esp_timer_get_time()-begin);
        last_us_=elapsed;if(elapsed>max_us_)max_us_=elapsed;
        if(elapsed>chunk_*1000000/16000)++over_budget_;
        timing_sum_+=elapsed;if(++timing_count_==32){mean_us_=timing_sum_/32;timing_sum_=timing_count_=0;}
        if (state == ESP_MN_STATE_DETECTED) {
            ++detections_;
            auto *r = mn_->get_results(data_);
            report_result(r,"detected");
            if (!r || r->num < 1 || r->num > ESP_MN_RESULT_MAX_NUM) return false;
            if(!std::isfinite(r->prob[0]) || r->prob[0]<threshold() || r->prob[0]>1.f){++rejected_;mn_->clean(data_);continue;}
            VoiceEvent event{epoch, r->command_id[0], r->prob[0], uint64_t(esp_timer_get_time()/1000)};
            if (xQueueSend(events, &event, 0) != pdTRUE) return false;
            mn_->clean(data_); // New utterance: no duplicate detections from the same decoder result.
        } else if (state == ESP_MN_STATE_TIMEOUT) {
            ++timeouts_; mn_->clean(data_);
        } // Always return to local detection.
        else if (state != ESP_MN_STATE_DETECTING) return false;
    }
    return true;
}
}
#endif
