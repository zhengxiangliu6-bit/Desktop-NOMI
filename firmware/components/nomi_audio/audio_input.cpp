#include "audio_input.h"
#include "driver/gpio.h"
#include "esp_check.h"
namespace nomi {
namespace {
const char *TAG = "nomi_audio";
constexpr gpio_num_t PA = GPIO_NUM_9;
esp_err_t codec_result(int r) { return r == ESP_CODEC_DEV_OK ? ESP_OK : ESP_FAIL; }
}
bool AudioInput::overflow(i2s_chan_handle_t, i2s_event_data_t *, void *context)
{
    static_cast<AudioInput *>(context)->overflows_.fetch_add(1, std::memory_order_relaxed);
    return false;
}
esp_err_t AudioInput::open()
{
    if (bus_) return ESP_ERR_INVALID_STATE;
    overflows_ = 0;
    ESP_RETURN_ON_ERROR(gpio_set_direction(PA, GPIO_MODE_OUTPUT), TAG, "PA GPIO");
    ESP_RETURN_ON_ERROR(gpio_set_level(PA, 0), TAG, "PA off");
    auto initialize = [&]() -> esp_err_t {
        i2c_master_bus_config_t bus = {};
        bus.i2c_port = I2C_NUM_1; bus.sda_io_num = GPIO_NUM_11; bus.scl_io_num = GPIO_NUM_10;
        bus.clk_source = I2C_CLK_SRC_DEFAULT; bus.glitch_ignore_cnt = 7;
        bus.flags.enable_internal_pullup = true;
        ESP_RETURN_ON_ERROR(i2c_new_master_bus(&bus, &bus_), TAG, "I2C");
        ESP_RETURN_ON_ERROR(i2c_master_probe(bus_, 0x40, 100), TAG, "ES7210 probe");
        ESP_RETURN_ON_ERROR(i2c_master_probe(bus_, 0x18, 100), TAG, "ES8311 probe");
        i2s_chan_config_t channel = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
        channel.dma_desc_num = 6; channel.dma_frame_num = 240; channel.auto_clear_after_cb = true;
        ESP_RETURN_ON_ERROR(i2s_new_channel(&channel, &tx_, &rx_), TAG, "I2S channels");
        i2s_std_config_t cfg = {};
        cfg.clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(16000);
        cfg.slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO);
        cfg.gpio_cfg.mclk = GPIO_NUM_2; cfg.gpio_cfg.bclk = GPIO_NUM_48;
        cfg.gpio_cfg.ws = GPIO_NUM_38; cfg.gpio_cfg.dout = GPIO_NUM_47; cfg.gpio_cfg.din = GPIO_NUM_39;
        ESP_RETURN_ON_ERROR(i2s_channel_init_std_mode(tx_, &cfg), TAG, "TX mode");
        ESP_RETURN_ON_ERROR(i2s_channel_init_std_mode(rx_, &cfg), TAG, "RX mode");
        i2s_event_callbacks_t callbacks = {}; callbacks.on_recv_q_ovf = overflow;
        ESP_RETURN_ON_ERROR(i2s_channel_register_event_callback(rx_, &callbacks, this), TAG, "Overflow callback");
        ESP_RETURN_ON_ERROR(i2s_channel_enable(tx_), TAG, "TX clock");
        ESP_RETURN_ON_ERROR(i2s_channel_enable(rx_), TAG, "RX enable");
        audio_codec_i2s_cfg_t data_cfg = {};
        data_cfg.port = I2S_NUM_1; data_cfg.tx_handle = tx_; data_cfg.rx_handle = rx_;
        data_ = audio_codec_new_i2s_data(&data_cfg); gpio_ = audio_codec_new_gpio();
        audio_codec_i2c_cfg_t control = {};
        control.port = I2C_NUM_1; control.bus_handle = bus_; control.clock_speed_hz = 400000;
        control.addr = ES7210_CODEC_DEFAULT_ADDR; adc_ctrl_ = audio_codec_new_i2c_ctrl(&control);
        control.addr = ES8311_CODEC_DEFAULT_ADDR; dac_ctrl_ = audio_codec_new_i2c_ctrl(&control);
        if (!data_ || !gpio_ || !adc_ctrl_ || !dac_ctrl_) return ESP_ERR_NO_MEM;
        es7210_codec_cfg_t adc_cfg = {};
        adc_cfg.ctrl_if = adc_ctrl_; adc_cfg.mic_selected = ES7210_SEL_MIC1 | ES7210_SEL_MIC2;
        adc_if_ = es7210_codec_new(&adc_cfg);
        es8311_codec_cfg_t dac_cfg = {};
        dac_cfg.ctrl_if = dac_ctrl_; dac_cfg.gpio_if = gpio_;
        // Driver must never enable the PA, even during codec open/close.
        dac_cfg.codec_mode = ESP_CODEC_DEV_WORK_MODE_DAC; dac_cfg.pa_pin = GPIO_NUM_NC;
        dac_cfg.use_mclk = true; dac_cfg.hw_gain.pa_voltage = 5.f; dac_cfg.hw_gain.codec_dac_voltage = 3.3f;
        dac_if_ = es8311_codec_new(&dac_cfg);
        if (!adc_if_ || !dac_if_) return ESP_ERR_NO_MEM;
        esp_codec_dev_cfg_t dev = {}; dev.data_if = data_;
        dev.codec_if = dac_if_; dev.dev_type = ESP_CODEC_DEV_TYPE_OUT; dac_ = esp_codec_dev_new(&dev);
        dev.codec_if = adc_if_; dev.dev_type = ESP_CODEC_DEV_TYPE_IN; adc_ = esp_codec_dev_new(&dev);
        if (!adc_ || !dac_) return ESP_ERR_NO_MEM;
        esp_codec_dev_sample_info_t format = {};
        format.sample_rate = 16000; format.channel = 2; format.bits_per_sample = 16;
        ESP_RETURN_ON_ERROR(codec_result(esp_codec_dev_open(dac_, &format)), TAG, "DAC clock setup");
        ESP_RETURN_ON_ERROR(codec_result(esp_codec_dev_set_out_mute(dac_, true)), TAG, "DAC mute");
        ESP_RETURN_ON_ERROR(codec_result(esp_codec_dev_open(adc_, &format)), TAG, "ADC open");
        ESP_RETURN_ON_ERROR(codec_result(esp_codec_dev_set_in_gain(adc_, 24.f)), TAG, "Mic gain");
        return gpio_set_level(PA, 0);
    };
    const auto result = initialize();
    if (result != ESP_OK) close();
    else ESP_LOGI(TAG, "ES7210 MIC1=slot0 MIC2=slot1, PCM16 stereo 16000Hz; ES8311 muted; PA off");
    return result;
}
esp_err_t AudioInput::read(int16_t *pcm, size_t bytes, size_t *received)
{
    if (!rx_ || !pcm || !received || bytes % 4) return ESP_ERR_INVALID_ARG;
    return i2s_channel_read(rx_, pcm, bytes, received, 100);
}
void AudioInput::close()
{
    gpio_set_level(PA, 0);
    if (adc_) { esp_codec_dev_close(adc_); esp_codec_dev_delete(adc_); adc_ = nullptr; }
    if (dac_) { esp_codec_dev_set_out_mute(dac_, true); esp_codec_dev_close(dac_); esp_codec_dev_delete(dac_); dac_ = nullptr; }
    if (adc_if_) { audio_codec_delete_codec_if(adc_if_); adc_if_ = nullptr; }
    if (dac_if_) { audio_codec_delete_codec_if(dac_if_); dac_if_ = nullptr; }
    if (adc_ctrl_) { audio_codec_delete_ctrl_if(adc_ctrl_); adc_ctrl_ = nullptr; }
    if (dac_ctrl_) { audio_codec_delete_ctrl_if(dac_ctrl_); dac_ctrl_ = nullptr; }
    if (gpio_) { audio_codec_delete_gpio_if(gpio_); gpio_ = nullptr; }
    if (data_) { audio_codec_delete_data_if(data_); data_ = nullptr; }
    if (rx_) { i2s_channel_disable(rx_); i2s_del_channel(rx_); rx_ = nullptr; }
    if (tx_) { i2s_channel_disable(tx_); i2s_del_channel(tx_); tx_ = nullptr; }
    if (bus_) { i2c_del_master_bus(bus_); bus_ = nullptr; }
}
}
