#include "command_recognizer.h"
#include "reference_probe.h"
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
    data_ = mn_->create(name, 6000);
    if (!data_) return false;
    if (mn_->get_samp_rate(data_) != 16000) return false;
    const int chunk = mn_->get_samp_chunksize(data_);
    if (chunk <= 0 || chunk > 1024) return false;
    chunk_ = size_t(chunk);
    buffer_ = static_cast<int16_t *>(heap_caps_malloc(chunk_*sizeof(int16_t), MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if (!buffer_) return false;
    // Pinned MN7 create() owns/initializes the command registry; never allocate it twice.
    const auto *language=mn_->get_language(data_);
    if(!language || std::strcmp(language,ESP_MN_CHINESE))return false;
    auto matches = [](int index, int id, const char *pinyin) {
        const auto *phrase = esp_mn_commands_get_from_index(index);
        return phrase && phrase->command_id == id && std::strcmp(phrase->string, pinyin) == 0;
    };
    int index = 0;
    if (!matches(index++, 1, CONFIG_NOMI_VOICE_WAKE_PINYIN)) return false;
    for (const auto &command : voice_commands)
        if (!matches(index++, command.id, command.pinyin)) return false;
    if (!matches(index++, 25, "da kai kong tiao") || esp_mn_commands_get_from_index(index)) return false;
    selftest_passed_ = self_test();
    if (!selftest_passed_) return false;
    active_=requested_.load();
    mn_->set_det_threshold(data_, threshold());
    mn_->clean(data_);
    esp_mn_active_commands_print(); // Actual model dictionary, not just our requested labels.
    ESP_LOGI(TAG, "VOICE_READY engine=MultiNet7 model=mn7_cn wake=%s pinyin=%s chunk=%u threshold=%.2f; continuous local command matching, NOT WakeNet",
             CONFIG_NOMI_VOICE_WAKE_LABEL, CONFIG_NOMI_VOICE_WAKE_PINYIN, unsigned(chunk_),double(threshold()));
    for (const auto &c : voice_commands) ESP_LOGI(TAG, "VOICE_COMMAND id=%d phrase=%s", c.id, c.label);
    return true;
}
bool CommandRecognizer::self_test() {
    const size_t samples=size_t(official_end-official_start)/2;
    const auto *pcm=reinterpret_cast<const int16_t *>(official_start);
    auto run=[&](const char *stage,int expected_id) {
        const auto result=probe_reference(pcm,samples,buffer_,chunk_,expected_id,[&](const int16_t *block){
            ProbeDecision out;out.state=int(mn_->detect(data_,const_cast<int16_t *>(block)));
            if(out.state==int(ESP_MN_STATE_DETECTED)) {
                auto *r=mn_->get_results(data_);
                if(r && r->num>0 && r->num<=ESP_MN_RESULT_MAX_NUM){out.id=r->command_id[0];out.score=r->prob[0];}
            }
            vTaskDelay(1);return out;
        });
        ESP_LOGI(TAG,"MN_REFERENCE stage=%s pass=%d expected=%d got=%d score=%.3f state=%d frames=%u samples=%u",
            stage,result.pass,expected_id,result.id,double(result.score),result.last_state,result.frames,unsigned(samples));
        return result.pass;
    };
    const bool passed = run("bundled_table", 25);
    ESP_LOGI(TAG, "MN_SELFTEST %s bundled=%d", passed ? "PASS" : "FAIL", passed);
    mn_->clean(data_);
    return passed;
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
    // Pinned MN7 destroy() releases its registry. Application must not free it first.
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
