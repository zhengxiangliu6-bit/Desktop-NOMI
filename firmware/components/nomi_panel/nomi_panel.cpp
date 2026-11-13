// Desktop-NOMI: display-only adaptation of Waveshare's 1.85B BSP.
// Original initialization flow/tables: Apache-2.0, see LICENSE and NOTICE.md.
#include "nomi_panel.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "driver/ledc.h"
#include "esp_check.h"
#include "esp_heap_caps.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_st77916.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

namespace {
constexpr gpio_num_t CLK = GPIO_NUM_40, D0 = GPIO_NUM_46, D1 = GPIO_NUM_45;
constexpr gpio_num_t D2 = GPIO_NUM_42, D3 = GPIO_NUM_41, CS = GPIO_NUM_21;
constexpr gpio_num_t RST = GPIO_NUM_3, BL = GPIO_NUM_5;
constexpr int WIDTH = 360, HEIGHT = 360, LINES = 16;
constexpr size_t BUFFER_BYTES = WIDTH * LINES * sizeof(uint16_t);
const char *TAG = "nomi_panel";
esp_lcd_panel_handle_t panel;
esp_lcd_panel_io_handle_t io;
lv_display_t *display;
SemaphoreHandle_t dma_done;
#include "panel_tables.inc"

bool transferred(esp_lcd_panel_io_handle_t, esp_lcd_panel_io_event_data_t *, void *)
{
    BaseType_t wake = pdFALSE;
    xSemaphoreGiveFromISR(dma_done, &wake);
    return wake == pdTRUE;
}
void flush(lv_display_t *, const lv_area_t *area, uint8_t *pixels)
{
    const size_t count = (area->x2 - area->x1 + 1) * (area->y2 - area->y1 + 1);
    lv_draw_sw_rgb565_swap(pixels, count);
    ESP_ERROR_CHECK(esp_lcd_panel_draw_bitmap(panel, area->x1, area->y1,
                                            area->x2 + 1, area->y2 + 1, pixels));
}
void wait_flush(lv_display_t *)
{
    // Yield to FreeRTOS while DMA owns the buffer; never spin on the bus.
    if (xSemaphoreTake(dma_done, pdMS_TO_TICKS(1000)) != pdTRUE) {
        ESP_LOGE(TAG, "QSPI DMA timeout");
        ESP_ERROR_CHECK(ESP_ERR_TIMEOUT);
    }
}
}

lv_display_t *nomi_panel_start()
{
    // Keep the backlight dark until the initial NOMI face has been flushed.
    ESP_ERROR_CHECK(gpio_set_direction(BL, GPIO_MODE_OUTPUT));
    ESP_ERROR_CHECK(gpio_set_level(BL, 0));
    ESP_ERROR_CHECK(gpio_set_direction(RST, GPIO_MODE_OUTPUT));
    ESP_ERROR_CHECK(gpio_set_level(RST, 0));
    vTaskDelay(pdMS_TO_TICKS(10));
    ESP_ERROR_CHECK(gpio_set_level(RST, 1));
    vTaskDelay(pdMS_TO_TICKS(10));
    spi_bus_config_t bus = {};
    bus.sclk_io_num = CLK;
    bus.data0_io_num = D0; bus.data1_io_num = D1;
    bus.data2_io_num = D2; bus.data3_io_num = D3;
    bus.data4_io_num = bus.data5_io_num = bus.data6_io_num = bus.data7_io_num = -1;
    bus.flags = SPICOMMON_BUSFLAG_QUAD;
    bus.max_transfer_sz = BUFFER_BYTES;
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_CH_AUTO));
    esp_lcd_panel_io_spi_config_t cfg = {};
    cfg.cs_gpio_num = CS; cfg.dc_gpio_num = -1;
    cfg.spi_mode = 0; cfg.pclk_hz = 3000000;
    cfg.trans_queue_depth = 10;
    cfg.lcd_cmd_bits = 32; cfg.lcd_param_bits = 8;
    cfg.flags.quad_mode = true;
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &cfg, &io));
    uint8_t id[4] = {};
    const esp_err_t id_result = esp_lcd_panel_io_rx_param(io, (0x0B << 24) | (0x04 << 8), id, sizeof(id));
    ESP_LOGI(TAG, "LCD ID (%s): %02x %02x %02x %02x", esp_err_to_name(id_result), id[0], id[1], id[2], id[3]);
    ESP_ERROR_CHECK(esp_lcd_panel_io_del(io));
    cfg.pclk_hz = 80000000;
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &cfg, &io));
    st77916_vendor_config_t vendor = {};
    vendor.flags.use_qspi_interface = true;
    if (id_result == ESP_OK && id[0] == 0 && id[1] == 0x7f && id[2] == 0x7f && id[3] == 0x7f) {
        vendor.init_cmds = vendor_specific_init_version_1;
        vendor.init_cmds_size = sizeof(vendor_specific_init_version_1) / sizeof(st77916_lcd_init_cmd_t);
        ESP_LOGI(TAG, "Waveshare panel table v1");
    } else if (id_result == ESP_OK && id[0] == 0 && id[1] == 2 && id[2] == 0x7f && id[3] == 0x7f) {
        vendor.init_cmds = vendor_specific_init_version_2;
        vendor.init_cmds_size = sizeof(vendor_specific_init_version_2) / sizeof(st77916_lcd_init_cmd_t);
        ESP_LOGI(TAG, "Waveshare panel table v2");
    } else {
        ESP_LOGW(TAG, "Unknown LCD ID: official driver default table; verify on hardware");
    }
    esp_lcd_panel_dev_config_t dev = {};
    dev.reset_gpio_num = RST;
    dev.rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB;
    dev.bits_per_pixel = 16; dev.vendor_config = &vendor;
    ESP_ERROR_CHECK(esp_lcd_new_panel_st77916(io, &dev, &panel));
    ESP_ERROR_CHECK(esp_lcd_panel_reset(panel));
    ESP_ERROR_CHECK(esp_lcd_panel_init(panel));
    ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(panel, true));
    dma_done = xSemaphoreCreateBinary();
    ESP_ERROR_CHECK(dma_done ? ESP_OK : ESP_ERR_NO_MEM);
    esp_lcd_panel_io_callbacks_t callbacks = {};
    callbacks.on_color_trans_done = transferred;
    ESP_ERROR_CHECK(esp_lcd_panel_io_register_event_callbacks(io, &callbacks, nullptr));
    void *a = heap_caps_malloc(BUFFER_BYTES, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    void *b = heap_caps_malloc(BUFFER_BYTES, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    ESP_ERROR_CHECK(a && b ? ESP_OK : ESP_ERR_NO_MEM);
    display = lv_display_create(WIDTH, HEIGHT);
    ESP_ERROR_CHECK(display ? ESP_OK : ESP_ERR_NO_MEM);
    lv_display_set_color_format(display, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(display, a, b, BUFFER_BYTES, LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(display, flush);
    lv_display_set_flush_wait_cb(display, wait_flush);
    ESP_LOGI(TAG, "ST77916 QSPI 80MHz RGB565, 2 x %u-byte DMA buffers", unsigned(BUFFER_BYTES));
    return display;
}

void nomi_panel_show()
{
    lv_refr_now(display);
    ESP_ERROR_CHECK(esp_lcd_panel_io_tx_param(io, -1, nullptr, 0));
    ledc_timer_config_t timer = {};
    timer.speed_mode = LEDC_LOW_SPEED_MODE; timer.timer_num = LEDC_TIMER_0;
    timer.duty_resolution = LEDC_TIMER_10_BIT; timer.freq_hz = 20000; timer.clk_cfg = LEDC_AUTO_CLK;
    ESP_ERROR_CHECK(ledc_timer_config(&timer));
    ledc_channel_config_t channel = {};
    channel.gpio_num = BL; channel.speed_mode = LEDC_LOW_SPEED_MODE;
    channel.channel = LEDC_CHANNEL_1; channel.timer_sel = LEDC_TIMER_0;
    channel.duty = 614; // 60%; no saved settings or flash writes.
    ESP_ERROR_CHECK(ledc_channel_config(&channel));
    ESP_LOGI(TAG, "First NOMI frame ready; backlight 60%%");
}
