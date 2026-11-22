#include "audio_trace.h"
#if CONFIG_NOMI_VOICE_COMMANDS
#include "driver/usb_serial_jtag.h"
#include "esp_timer.h"
#include "esp_log.h"
namespace nomi {
namespace {uint32_t clock_ms(){return uint32_t(esp_timer_get_time()/1000);}}
void AudioTrace::on(uint32_t token){if(!token)return;heartbeat_=clock_ms();token_=token;}
void AudioTrace::ping(uint32_t token){if(token && token==token_)heartbeat_=clock_ms();}
void AudioTrace::feed(unsigned channel,const int16_t *pcm,size_t samples,bool guarded){
    const auto token=token_.load();if(!token || (channel!=1 && channel!=2))return;
    if(clock_ms()-heartbeat_.load()>2000){uint32_t expected=token;token_.compare_exchange_strong(expected,0);return;}
    auto &framer=channel==1?raw_:afe_;
    if(!framer.feed(token,channel,pcm,samples,guarded,[&](const char *line,size_t size){
        if(token_!=token)return false;
        // IDF driver atomically enqueues each complete frame. Bounded wait; never stall inference on host loss.
        if(usb_serial_jtag_write_bytes(line,size,pdMS_TO_TICKS(2))!=int(size))return false;
        ++frames_[channel-1];return true;
    })){
        uint32_t expected=token;token_.compare_exchange_strong(expected,0);++stopped_;
        ESP_LOGW("trace","TRACE_STOPPED: host backpressure/session changed; inference continues");
    }
}
void AudioTrace::status()const{ESP_LOGI("trace","TRACE_STATUS active=%d raw_frames=%lu afe_frames=%lu stopped=%lu; no recordings on device",
    token_.load()!=0,(unsigned long)frames_[0].load(),(unsigned long)frames_[1].load(),(unsigned long)stopped_.load());}
}
#endif
