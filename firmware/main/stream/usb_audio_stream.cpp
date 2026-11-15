#include "usb_audio_stream.h"
#if CONFIG_NOMI_USB_ASR
#include "pcm_frame.h"
#include "driver/usb_serial_jtag.h"
#include "esp_log.h"
#include "esp_timer.h"
namespace nomi {
namespace { const char *TAG = "usb_audio"; uint32_t clock_ms() { return uint32_t(esp_timer_get_time()/1000); } }
bool UsbAudioStream::start() {
    if (task_) return false;
    if (xTaskCreatePinnedToCore(entry, "usb_audio", 8192, this, 4, &task_, 0) != pdPASS) { state_=3; return false; }
    ESP_LOGI(TAG, "USB_ASR_READY; microphone OFF until host starts; no device ASR or voice actions");
    return true;
}
void UsbAudioStream::on(uint32_t token, unsigned channel) {
    if (!task_ || !token || (channel != 1 && channel != 2)) return;
    channel_ = channel; heartbeat_ = clock_ms(); token_ = token;
}
void UsbAudioStream::off() { token_ = 0; }
void UsbAudioStream::ping(uint32_t token) { if (token && token == token_) heartbeat_ = clock_ms(); }
void UsbAudioStream::status() const { ESP_LOGI(TAG, "state=%u frames=%lu mic=%u (PCM16LE/16000Hz/mono; 2s heartbeat lease)", state(), (unsigned long)frames_.load(), unsigned(channel_.load())); }
void UsbAudioStream::run() {
    int16_t stereo[stream_samples*2], mono[stream_samples];
    char line[1024];
    for (;;) {
        const uint32_t session = token_;
        if (!session) { vTaskDelay(pdMS_TO_TICKS(20)); continue; }
        state_ = 1; frames_ = 0;
        bool bad = audio_.open() != ESP_OK;
        uint32_t sequence = 0, observed = audio_.overflows();
        size_t filled = 0; unsigned empty = 0, warmup = 10;
        const unsigned channel = channel_;
        while (!bad && token_ == session) {
            if (clock_ms()-heartbeat_.load() > 2000) { ESP_LOGW(TAG, "Host heartbeat expired; stopping microphone"); break; }
            size_t received = 0;
            const auto result = audio_.read(stereo+filled/2, sizeof(stereo)-filled, &received);
            if ((result != ESP_OK && result != ESP_ERR_TIMEOUT) || received % 4 || received > sizeof(stereo)-filled) { bad=true; break; }
            if (!received) { if (++empty >= 5) bad=true; continue; }
            empty = 0; filled += received;
            if (filled != sizeof(stereo)) continue;
            filled = 0;
            if (warmup) { --warmup; observed=audio_.overflows(); continue; }
            if (audio_.overflows() != observed) { bad=true; break; }
            for (size_t i=0; i<stream_samples; ++i) mono[i] = stereo[i*2+channel-1];
            const auto size = encode_frame(line, sizeof(line), session, sequence++, channel, mono, stream_samples);
            if (!size || token_ != session) break;
            // Finite timeout: a vanished/slow host must never block capture indefinitely.
            if (usb_serial_jtag_write_bytes(line, size, pdMS_TO_TICKS(20)) != int(size)) { bad=true; break; }
            ++frames_; state_ = 2;
        }
        audio_.close();
        uint32_t expected = session;
        token_.compare_exchange_strong(expected, 0); // Do not erase a newer host's request.
        state_ = bad ? 3 : 0;
        if (bad) ESP_LOGE(TAG, "STREAM_FAULT: init/I2S overflow/read/USB backpressure; microphone stopped; restart host");
        else ESP_LOGI(TAG, "STREAM_STOPPED; microphone OFF");
    }
}
}
#endif
