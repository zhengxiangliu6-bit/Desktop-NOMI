#pragma once
#include "sdkconfig.h"
#if CONFIG_NOMI_USB_ASR
#include <atomic>
#include "audio_input.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
namespace nomi {
class UsbAudioStream {
public:
    bool start();
    void on(uint32_t token, unsigned channel);
    void off();
    void ping(uint32_t token);
    void status() const;
    unsigned state() const { return state_.load(); } // 0 stopped, 1 starting, 2 streaming, 3 fault
private:
    static void entry(void *p) { static_cast<UsbAudioStream *>(p)->run(); }
    void run();
    AudioInput audio_;
    TaskHandle_t task_ = nullptr;
    std::atomic<uint32_t> token_{0}, heartbeat_{0}, frames_{0}, channel_{1}, state_{0};
};
}
#endif
