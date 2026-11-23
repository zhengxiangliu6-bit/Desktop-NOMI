#pragma once
#include "sdkconfig.h"
#include <atomic>
#if CONFIG_NOMI_VOICE_COMMANDS
#include "esp_mn_models.h"
#include "voice_session.h"
#include "model_path.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
namespace nomi {
class CommandRecognizer {
public:
    bool open(srmodel_list_t *models);
    void reset(); // Fetch-task owner only; discard decoder history across playback.
    void close(); // Only after the fetch worker has stopped.
    bool consume(const int16_t *pcm, size_t samples, QueueHandle_t events, uint32_t epoch);
    bool request_threshold(unsigned score) { if(score<30 || score>95)return false;requested_=score;return true; }
    float threshold() const { return float(active_.load())/100.f; }
    void status() const;
    uint32_t frames() const { return frames_.load(); }
private:
    const esp_mn_iface_t *mn_ = nullptr;
    model_iface_data_t *data_ = nullptr;
    int16_t *buffer_ = nullptr;
    size_t chunk_ = 0, used_ = 0;
    std::atomic<uint32_t> frames_{0}, detections_{0}, timeouts_{0}, rejected_{0};
    std::atomic<unsigned> requested_{90},active_{90};
    std::atomic<int> candidate_id_{0};
    std::atomic<float> candidate_score_{0};
    bool install_commands(bool diagnostic);
    bool self_test();
    std::atomic<bool> selftest_passed_{false};
    std::atomic<uint32_t> last_us_{0},max_us_{0},mean_us_{0},over_budget_{0};
    uint64_t timing_sum_=0;
    unsigned timing_count_=0;
    void report_result(const esp_mn_results_t *result,const char *source);
};
}
#endif
