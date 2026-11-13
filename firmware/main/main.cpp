#include "face_model.h"
#include "face_view.h"
#include "nomi_panel.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "esp_psram.h"
#include "driver/usb_serial_jtag.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <cstring>

namespace {
const char *TAG = "nomi";
uint64_t now_ms() { return uint64_t(esp_timer_get_time()) / 1000; }
uint32_t lv_clock() { return uint32_t(now_ms()); }
nomi::FaceModel model;
nomi::FaceView view;
bool demo = false;
unsigned demo_step = 0;
uint64_t demo_at = 0;
const char *const sequence[] = {"idle", "blink", "happy", "sad", "curious", "thinking", "listening", "speaking"};
void status()
{
    ESP_LOGI(TAG, "phase=%d emotion=%d internal_free=%u psram_free=%u min_heap=%u",
             int(model.phase()), int(model.emotion()),
             unsigned(heap_caps_get_free_size(MALLOC_CAP_INTERNAL)),
             unsigned(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)),
             unsigned(esp_get_minimum_free_heap_size()));
}
void command(const char *text, uint64_t now)
{
    if (!std::strcmp(text, "status")) { status(); return; }
    demo = false;
    if (!std::strcmp(text, "demo")) {
        model.reset(now); demo = true; demo_step = 0; demo_at = now;
        ESP_LOGI(TAG, "One demo cycle; any expression command cancels it");
        return;
    }
    if (model.command(text, now)) ESP_LOGI(TAG, "Command accepted: %s (5s TTL)", text);
    else ESP_LOGW(TAG, "Unknown/oversized command; reset to idle");
}
void read_commands(uint64_t now)
{
    static char line[48];
    static size_t used = 0;
    static bool overflow = false;
    char chunk[32];
    // Timeout zero and bounded bytes: a partial line never stalls animation.
    const int count = usb_serial_jtag_read_bytes(chunk, sizeof(chunk), 0);
    for (int i = 0; i < count; ++i) {
        const char c = chunk[i];
        if (c == '\r' || c == '\n') {
            if (used || overflow) {
                line[used] = 0;
                command(overflow ? "" : line, now);
            }
            used = 0; overflow = false;
        } else if (c >= 32 && c <= 126) {
            if (used + 1 < sizeof(line) && !overflow) line[used++] = c;
            else overflow = true;
        }
    }
}
}
extern "C" void app_main()
{
    ESP_LOGI(TAG, "Desktop-NOMI H1; Waveshare ESP32-S3-Touch-LCD-1.85B only; no AI/audio/network");
    ESP_LOGI(TAG, "ESP-IDF %s; LVGL %d.%d.%d", esp_get_idf_version(),
             LVGL_VERSION_MAJOR, LVGL_VERSION_MINOR, LVGL_VERSION_PATCH);
    ESP_LOGI(TAG, "PSRAM initialized=%d size=%u", esp_psram_is_initialized(), unsigned(esp_psram_get_size()));
    usb_serial_jtag_driver_config_t serial = {};
    serial.rx_buffer_size = 256; serial.tx_buffer_size = 1024;
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&serial));
    lv_init();
    lv_tick_set_cb(lv_clock);
    nomi_panel_start();
    model = nomi::FaceModel(uint32_t(esp_timer_get_time()));
    model.reset(now_ms());
    view.create();
    view.render(model.update(now_ms()), model.phase());
    nomi_panel_show();
    ESP_LOGI(TAG, "Commands + Enter: idle blink happy sad curious thinking listening speaking demo status");
    status();
    uint64_t frame_at = 0;
    while (true) {
        const uint64_t now = now_ms();
        read_commands(now);
        if (demo && now >= demo_at) {
            if (demo_step == sizeof(sequence) / sizeof(sequence[0])) {
                demo = false; model.reset(now); ESP_LOGI(TAG, "Demo complete; idle");
            } else {
                // Isolated previews: previous phase/emotion cannot mask the next one.
                model.reset(now);
                model.command(sequence[demo_step], now);
                ESP_LOGI(TAG, "Demo: %s", sequence[demo_step++]);
                demo_at = now + 3000;
            }
        }
        if (now >= frame_at) {
            auto frame = model.update(now);
            view.render(frame, model.phase());
            frame_at = now + 20;
        }
        lv_timer_handler();
        // Scheduler yield only: animations/commands use monotonic deadlines.
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}
