#pragma once
#include <atomic>
#include "audio_input.h"
#include "wake_logic.h"
#include "voice_session.h"
#include "command_recognizer.h"
#include "fixed_reply_player.h"
#include "audio_trace.h"
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
    bool poll_voice(VoiceEvent &event);
    WakeState state() const { return state_.load(); }
    bool faulted() const { return failed_.load() || state_.load()==WakeState::Fault; }
    void status() const;
    bool say_okay(uint32_t epoch);
    bool trace_on(uint32_t token,unsigned channels=3) {
#if CONFIG_NOMI_VOICE_COMMANDS
        trace_.on(token,channels);return true;
#else
        (void)token;(void)channels;return false;
#endif
    }
    void trace_off(){
#if CONFIG_NOMI_VOICE_COMMANDS
        trace_.off();
#endif
    }
    void trace_ping(uint32_t token){
#if CONFIG_NOMI_VOICE_COMMANDS
        trace_.ping(token);
#else
        (void)token;
#endif
    }
    bool request_threshold(unsigned score) {
#if CONFIG_NOMI_VOICE_COMMANDS
        return recognizer_.request_threshold(score);
#else
        (void)score;return false;
#endif
    }
    float threshold() const {
#if CONFIG_NOMI_VOICE_COMMANDS
        return recognizer_.threshold();
#else
        return 0.90f;
#endif
    }
    bool voice_guarded() const {
#if CONFIG_NOMI_VOICE_COMMANDS
        return reply_muted_.load();
#else
        return false;
#endif
    }
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
    QueueHandle_t voice_events_ = nullptr;
#if CONFIG_NOMI_VOICE_COMMANDS
    std::atomic<bool> detector_ready_{false};
    AudioTrace trace_;
    CommandRecognizer recognizer_;
    std::atomic<uint32_t> afe_peak_{0},afe_rms_{0},afe_zero_{0},cache_samples_{0};
    FixedReplyPlayer player_;
    QueueHandle_t sayings_ = nullptr;
    uint64_t reply_release_at_ = 0; // capture owner
    std::atomic<bool> reply_muted_{false};
#endif
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
