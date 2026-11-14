#pragma once
#include <atomic>
#include "audio_input.h"
#include "wake_logic.h"
#include "esp_afe_sr_models.h"
#include "model_path.h"
#include "freertos/event_groups.h"
#include "freertos/queue.h"

namespace nomi {
enum class WakeState { Disabled, Starting, Monitoring, Listening, Fault };
class WakeWordController {
public:
    bool start();
    void enable(bool enabled); // asynchronous; invalidates old queued events immediately
    uint32_t epoch() const { return epoch_.load(); }
    bool poll(WakeEvent &event);
    bool faulted() const { return failed_.load(); }
    void status() const;
    static const char *profile();
private:
    struct Request { bool enabled; uint32_t epoch; };
    static void capture_entry(void *p) { static_cast<WakeWordController *>(p)->capture_loop(); }
    static void fetch_entry(void *p) { static_cast<WakeWordController *>(p)->fetch_loop(); }
    void capture_loop();
    void fetch_loop();
    bool initialize();
    bool cleanup();
    void fault(const char *stage);
    AudioInput audio_;
    QueueHandle_t requests_ = nullptr, events_ = nullptr;
    EventGroupHandle_t sync_ = nullptr;
    TaskHandle_t capture_task_ = nullptr, fetch_task_ = nullptr;
    esp_afe_sr_iface_t *afe_ = nullptr;
    esp_afe_sr_data_t *afe_data_ = nullptr;
    srmodel_list_t *models_ = nullptr;
    int16_t *stereo_ = nullptr, *mono_ = nullptr;
    int chunk_ = 0;
    uint32_t session_epoch_ = 0;
    bool fetch_started_ = false; // capture task owner
    std::atomic<uint32_t> epoch_{0};
    std::atomic<bool> stop_{true}, failed_{false}, detected_{false}, feeding_{false};
    std::atomic<WakeState> state_{WakeState::Disabled};
    std::atomic<uint32_t> blocks_{0}, fetched_{0}, dropped_{0}, timeouts_{0}, overflows_{0};
    std::atomic<uint32_t> peak_[2]{}, rms_[2]{}, clipped_[2]{};
    std::atomic<uint32_t> vad_speech_{0}, attempts_{0};
};
}
