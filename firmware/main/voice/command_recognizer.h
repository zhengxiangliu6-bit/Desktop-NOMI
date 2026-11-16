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
    uint32_t frames() const { return frames_.load(); }
private:
    const esp_mn_iface_t *mn_ = nullptr;
    model_iface_data_t *data_ = nullptr;
    bool commands_allocated_ = false;
    int16_t *buffer_ = nullptr;
    size_t chunk_ = 0, used_ = 0;
    std::atomic<uint32_t> frames_{0};
};
}
#endif
