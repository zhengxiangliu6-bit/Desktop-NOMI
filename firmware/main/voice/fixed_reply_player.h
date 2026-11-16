#pragma once
#include <cstddef>
#include <cstdint>
#include <algorithm>
#include "playback_guard.h"
namespace nomi {
// One capture-task owner. RX sample clock paces TX; no UI delays or heap buffers.
class FixedReplyPlayer {
public:
    template<class Sink> bool begin(Sink &sink,const int16_t *pcm,size_t samples) {
        if(active() || !pcm || !samples || samples>48000) return false;
        if(sink.speaker_begin()!=0) { sink.speaker_end(); return false; }
        pcm_=pcm;credit_=0;return guard_.begin(samples);
    }
    bool active() const {return guard_.active();}
    template<class Sink> bool pump(Sink &sink,size_t captured_samples) {
        if(!active())return true;
        if(!captured_samples || captured_samples>1024){cancel(sink);return false;}
        credit_+=captured_samples;
        while(credit_>=320 && active()) {
            credit_-=320;
            if(guard_.writing()) {
                std::fill_n(stereo_,640,0);
                for(size_t i=0;i<guard_.copy_samples();++i)
                    stereo_[2*i]=stereo_[2*i+1]=pcm_[guard_.offset()+i];
                if(sink.speaker_write(stereo_,sizeof(stereo_))!=0) {cancel(sink);return false;}
            }
            if(guard_.should_mute())sink.speaker_end();
            guard_.step();
        }
        return true;
    }
    template<class Sink> void cancel(Sink &sink) {sink.speaker_end();guard_.cancel();credit_=0;pcm_=nullptr;}
private:
    PlaybackGuard guard_;
    const int16_t *pcm_=nullptr;
    size_t credit_=0;
    int16_t stereo_[640]{};
};
}
