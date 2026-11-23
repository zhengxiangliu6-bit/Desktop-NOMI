#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cmath>
namespace nomi {
struct ProbeDecision {int state=0,id=0;float score=0;};
struct ProbeReport {unsigned frames=0;int last_state=0,id=0;float score=0;bool pass=false;};
// Feed known PCM exactly once, with bounded zero tail. No dictionary changes or actions.
template<class Detect> ProbeReport probe_reference(const int16_t *pcm,size_t samples,int16_t *scratch,size_t chunk,
                                                 int expected_id,Detect detect) {
    ProbeReport report;
    if(!pcm || !scratch || !samples || !chunk || chunk>1024)return report;
    for(size_t offset=0;offset<samples+32000;offset+=chunk) {
        std::fill_n(scratch,chunk,0);
        if(offset<samples)std::copy_n(pcm+offset,std::min(chunk,samples-offset),scratch);
        const auto result=detect(scratch);++report.frames;report.last_state=result.state;
        if(result.state==1) {
            report.id=result.id;report.score=result.score;
            report.pass=result.id==expected_id && std::isfinite(result.score) && result.score>=0.60f && result.score<=1.f;
            break;
        }
        if(result.state!=0)break;
    }
    return report;
}
}
