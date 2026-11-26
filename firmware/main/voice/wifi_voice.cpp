#include "sdkconfig.h"
#if CONFIG_NOMI_WIFI_VOICE
#include "wifi_voice.h"
#include "audio_input.h"
#include "fixed_reply_player.h"
#include "face_catalog.h"
#include "driver/gpio.h"
#include "esp_crt_bundle.h"
#include "esp_event.h"
#include "esp_heap_caps.h"
#include "esp_http_client.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include <ctime>
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "cJSON.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <atomic>
#include <cstdio>
#include <new>
#include <cstring>

extern const uint8_t okay_start[] asm("_binary_okay_pcm_start");
extern const uint8_t okay_end[] asm("_binary_okay_pcm_end");
namespace nomi {
namespace {
constexpr auto button = GPIO_NUM_0;
constexpr size_t samples = 4 * 16000;
constexpr auto tag = "wifi_voice";
std::atomic<const char *> pending{nullptr};
std::atomic<bool> online{false};
std::atomic<bool> clock_started{false};
struct Response { char data[4096]{}; size_t used = 0; };
esp_err_t receive(esp_http_client_event_t *event) {
    auto &body = *static_cast<Response *>(event->user_data);
    if (event->event_id == HTTP_EVENT_ON_DATA) {
        const size_t count = event->data_len;
        if (count >= sizeof(body.data) - body.used) return ESP_FAIL;
        std::memcpy(body.data + body.used, event->data, count);
        body.used += count;
    }
    return ESP_OK;
}
void network(void *, esp_event_base_t base, int32_t id, void *) {
    if (base == IP_EVENT) {
        if (!clock_started.exchange(true)) {
            esp_sntp_config_t config = ESP_NETIF_SNTP_DEFAULT_CONFIG("pool.ntp.org");
            if (esp_netif_sntp_init(&config) != ESP_OK) clock_started = false;
        }
        online = true;
        ESP_LOGI(tag, "Wi-Fi connected, waiting for clock sync before HTTPS");
    }
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) online = false;
}
const char *transcribe(const int16_t *pcm) {
    auto *response = new (std::nothrow) Response;
    if (!response) return nullptr;
    esp_http_client_config_t config{};
    config.url = CONFIG_NOMI_WIFI_VOICE_URL;
    config.crt_bundle_attach = esp_crt_bundle_attach;
    config.timeout_ms = 20000;
    config.disable_auto_redirect = true;
    config.event_handler = receive;
    config.user_data = response;
    auto client = esp_http_client_init(&config);
    const char *action = nullptr;
    if (client) {
        char auth[sizeof(CONFIG_NOMI_WIFI_DEVICE_TOKEN) + 8];
        std::snprintf(auth, sizeof(auth), "Bearer %s", CONFIG_NOMI_WIFI_DEVICE_TOKEN);
        esp_http_client_set_method(client, HTTP_METHOD_POST);
        esp_http_client_set_header(client, "Authorization", auth);
        esp_http_client_set_header(client, "Content-Type", "application/octet-stream");
        esp_http_client_set_post_field(client, reinterpret_cast<const char *>(pcm), samples * 2);
        auto result = esp_http_client_perform(client);
        const int status = esp_http_client_get_status_code(client);
        if (result == ESP_OK && status == 200) {
            auto *json = cJSON_Parse(response->data);
            const auto *text = cJSON_GetObjectItemCaseSensitive(json, "text");
            const auto *face = cJSON_GetObjectItemCaseSensitive(json, "action");
            if (cJSON_IsString(text)) {
                for (char *p = text->valuestring; *p; ++p)
                    if (static_cast<unsigned char>(*p) < 32 || *p == 127) *p = ' ';
                ESP_LOGI(tag, "TRANSCRIPT %s", text->valuestring);
            }
            if (cJSON_IsString(face))
                for (const auto &design : face_designs)
                    if (std::strcmp(design.command, face->valuestring) == 0) action = design.command;
            cJSON_Delete(json);
        } else ESP_LOGW(tag, "Transcription failed: %s HTTP %d", esp_err_to_name(result), status);
        esp_http_client_cleanup(client);
    }
    delete response;
    return action;
}
bool record(AudioInput &audio, int16_t *pcm) {
    int16_t stereo[640];
    for (size_t offset = 0; offset < samples;) {
        size_t got = 0;
        if (audio.read(stereo, sizeof(stereo), &got) != ESP_OK || !got ||
            got > sizeof(stereo) || got % 4 || audio.overflows()) return false;
        for (size_t i = 0; i < got / 4 && offset < samples; ++i) pcm[offset++] = stereo[i * 2];
    }
    return true;
}
void task(void *) {
    AudioInput audio;
    FixedReplyPlayer player;
    bool armed = false;
    while (true) {
        const bool pressed = gpio_get_level(button) == 0;
        if (!pressed) armed = true;
        if (!pressed || !armed) {
            if (!online) {
                esp_wifi_connect();
                vTaskDelay(pdMS_TO_TICKS(1000));
            } else vTaskDelay(pdMS_TO_TICKS(30));
            continue;
        }
        armed = false;
        vTaskDelay(pdMS_TO_TICKS(40));
        if (gpio_get_level(button) != 0) continue;
        if (!online || std::time(nullptr) < 1704067200) {
            ESP_LOGW(tag, "Wi-Fi or clock not ready");
            continue;
        }
        auto *pcm = static_cast<int16_t *>(heap_caps_malloc(samples * 2, MALLOC_CAP_SPIRAM));
        if (!pcm) { ESP_LOGE(tag, "PCM allocation failed"); continue; }
        if (audio.open() != ESP_OK) { heap_caps_free(pcm); continue; }
        pending = "listening";
        ESP_LOGI(tag, "Recording for four seconds");
        const bool recorded = record(audio, pcm);
        audio.close();
        pending = "thinking";
        const auto *action = recorded ? transcribe(pcm) : nullptr;
        heap_caps_free(pcm);
        pending = action ? action : "idle";
        if (action && audio.open() == ESP_OK) {
            if (player.begin(audio, reinterpret_cast<const int16_t *>(okay_start), (okay_end-okay_start)/2)) {
                int16_t stereo[640];
                while (player.active()) {
                    size_t got = 0;
                    if (audio.read(stereo, sizeof(stereo), &got) != ESP_OK || !got ||
                        got % 4 || !player.pump(audio, got / 4)) break;
                }
                player.cancel(audio);
            }
            audio.close();
        }
    }
}
}
void wifi_voice_start() {
    if (std::strncmp(CONFIG_NOMI_WIFI_VOICE_URL, "https://", 8) ||
        std::strlen(CONFIG_NOMI_WIFI_DEVICE_TOKEN) < 24 ||
        !CONFIG_NOMI_WIFI_SSID[0] ||
        sizeof(CONFIG_NOMI_WIFI_SSID) > 32 || sizeof(CONFIG_NOMI_WIFI_PASSWORD) > 64) {
        ESP_LOGE(tag, "Configure Wi-Fi SSID, HTTPS gateway and device token in menuconfig");
        return;
    }
    gpio_config_t input{};
    input.pin_bit_mask = 1ULL << button;
    input.mode = GPIO_MODE_INPUT;
    input.pull_up_en = GPIO_PULLUP_ENABLE;
    if (gpio_config(&input) != ESP_OK || nvs_flash_init() != ESP_OK ||
        esp_netif_init() != ESP_OK || esp_event_loop_create_default() != ESP_OK ||
        !esp_netif_create_default_wifi_sta()) return;
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    wifi_config_t station{};
    std::memcpy(station.sta.ssid, CONFIG_NOMI_WIFI_SSID, sizeof(CONFIG_NOMI_WIFI_SSID));
    std::memcpy(station.sta.password, CONFIG_NOMI_WIFI_PASSWORD, sizeof(CONFIG_NOMI_WIFI_PASSWORD));
    if (esp_wifi_init(&init) != ESP_OK || esp_wifi_set_storage(WIFI_STORAGE_RAM) != ESP_OK ||
        esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, network, nullptr) != ESP_OK ||
        esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, network, nullptr) != ESP_OK ||
        esp_wifi_set_mode(WIFI_MODE_STA) != ESP_OK ||
        esp_wifi_set_config(WIFI_IF_STA, &station) != ESP_OK || esp_wifi_start() != ESP_OK) return;
    if (xTaskCreate(task, "wifi_voice", 8192, nullptr, 4, nullptr) != pdPASS)
        ESP_LOGE(tag, "Cannot start voice task");
}
const char *wifi_voice_poll() { return pending.exchange(nullptr); }
}
#endif
