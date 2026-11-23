#include "reference_probe.h"
#include <cassert>
#include <vector>
int main(){
 int16_t pcm[]={1,2,3,4,5},scratch[4];std::vector<int16_t> fed;int calls=0;
 auto result=nomi::probe_reference(pcm,5,scratch,4,25,[&](const int16_t *p){
   fed.insert(fed.end(),p,p+4);++calls;return nomi::ProbeDecision{calls==2?1:0,25,.9f};});
 assert(result.pass && result.frames==2);assert((fed==std::vector<int16_t>{1,2,3,4,5,0,0,0}));
 result=nomi::probe_reference(pcm,5,scratch,4,1,[](const int16_t *){return nomi::ProbeDecision{2,0,0};});
 assert(!result.pass && result.frames==1 && result.last_state==2);
 result=nomi::probe_reference(pcm,5,scratch,4,1,[](const int16_t *){return nomi::ProbeDecision{1,25,.99f};});assert(!result.pass);
 result=nomi::probe_reference(pcm,5,scratch,4,25,[](const int16_t *){return nomi::ProbeDecision{1,25,.1f};});assert(!result.pass);
 result=nomi::probe_reference(pcm,5,scratch,0,1,[](const int16_t *){return nomi::ProbeDecision{};});assert(!result.pass && !result.frames);
}
