#pragma once
#include "pcm_frame.h"
#include <algorithm>
#include <cstring>
namespace nomi {
// One writer per channel; preserves sample continuity across 512->320 chunk conversion.
class TraceFramer {
public:
    template<class Write> bool feed(uint32_t token,unsigned channel,const int16_t *pcm,size_t samples,bool guarded,Write write) {
        if(!token || !pcm || !samples)return false;
        if(token!=token_){token_=token;used_=0;sequence_=0;guarded_=false;}
        while(samples) {
            const auto count=std::min(stream_samples-used_,samples);
            std::copy_n(pcm,count,pcm_+used_);pcm+=count;used_+=count;samples-=count;guarded_|=guarded;
            if(used_==stream_samples) {
                const auto size=encode_frame(line_,sizeof(line_),token_,sequence_,channel,pcm_,stream_samples,guarded_?1:0);
                if(!size)return false;
                std::memcpy(line_+1,"@NTRC1",6); // Separate from PC-ASR NOMI2 transport.
                if(!write(line_,size))return false;
                ++sequence_;used_=0;guarded_=false;
            }
        }
        return true;
    }
private:
    uint32_t token_=0,sequence_=0;
    size_t used_=0;
    bool guarded_=false;
    int16_t pcm_[stream_samples]{};
    char line_[1024]{};
};
}
