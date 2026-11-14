#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
#include "driver/i2c_master.h"
#include "driver/i2s_std.h"
#include "esp_codec_dev.h"
#include "esp_codec_dev_defaults.h"
namespace nomi {
// Single capture-task owner. Exact 1.85B pins, based on official Mic Test.
class AudioInput {
public:
    esp_err_t open();
    esp_err_t read(int16_t *stereo, size_t bytes, size_t *received);
    void close();
    uint32_t overflows() const { return overflows_.load(); }
private:
    static bool overflow(i2s_chan_handle_t, i2s_event_data_t *, void *context);
    i2c_master_bus_handle_t bus_ = nullptr;
    i2s_chan_handle_t tx_ = nullptr, rx_ = nullptr;
    const audio_codec_data_if_t *data_ = nullptr;
    const audio_codec_gpio_if_t *gpio_ = nullptr;
    const audio_codec_ctrl_if_t *adc_ctrl_ = nullptr, *dac_ctrl_ = nullptr;
    const audio_codec_if_t *adc_if_ = nullptr, *dac_if_ = nullptr;
    esp_codec_dev_handle_t adc_ = nullptr, dac_ = nullptr;
    std::atomic<uint32_t> overflows_{0};
};
}
