#pragma once
#include "sdkconfig.h"
#if CONFIG_NOMI_VOICE_COMMANDS
#include "trace_framer.h"
#include <atomic>
namespace nomi {
class AudioTrace {
public:
    void on(uint32_t token,unsigned channels=3);
    void off(){token_=0;}
    void ping(uint32_t token);
    void feed(unsigned channel,const int16_t *pcm,size_t samples,bool guarded);
    void status() const;
private:
    TraceFramer raw_,afe_;
    std::atomic<uint32_t> token_{0},heartbeat_{0},channels_{3},frames_[2]{},stopped_{0};
};
}
#endif
