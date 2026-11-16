#pragma once
#include "sdkconfig.h"
#if CONFIG_NOMI_USB_ASR
#include <atomic>
#include "audio_input.h"
#include "playback_guard.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
namespace nomi {
class UsbAudioStream {
public:
    bool start();
    void on(uint32_t token, unsigned channel);
    void off();
    void ping(uint32_t token);
    void status() const;
    bool reply(const char *text, size_t size, bool spoken=false, uint32_t token=0, uint32_t sequence=0);
    bool session_active(uint32_t token) const;
    unsigned state() const { return state_.load(); } // 0 stopped, 1 starting, 2 streaming, 3 fault
private:
    static void entry(void *p) { static_cast<UsbAudioStream *>(p)->run(); }
    void run();
    struct Reply { char text[120]; size_t size; bool spoken; uint32_t token, sequence; };
    PlaybackGuard playback_;
    uint32_t speech_token_=0, speech_sequence_=0;
    bool speech_pending_=false;
    void speech_event(const char *event, uint32_t token=0, uint32_t sequence=0);
    void send_replies();
    QueueHandle_t replies_ = nullptr;
    AudioInput audio_;
    TaskHandle_t task_ = nullptr;
    std::atomic<uint32_t> token_{0}, heartbeat_{0}, frames_{0}, channel_{1}, state_{0};
};
}
#endif
