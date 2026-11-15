#include "pcm_frame.h"
#include <cassert>
#include <cstring>
int main() {
    int16_t pcm[nomi::stream_samples];
    const int16_t values[] = {0,1,-1,-32768,32767};
    for (unsigned i=0;i<nomi::stream_samples;++i) pcm[i]=values[i%5];
    char line[1024];
    const auto n=nomi::encode_frame(line,sizeof(line),0x12345678,0,1,pcm,nomi::stream_samples);
    assert(n>850 && n<1024 && line[n-1]=='\n' && line[n]==0);
    assert(!std::strncmp(line,"\n@NOMI1 12345678 00000000 1 ",28));
    assert(std::strstr(line,"AAABAP//AID/fw")); // PCM16 little-endian extrema base64
    assert(!nomi::encode_frame(line,100,1,0,1,pcm,320));
    assert(!nomi::encode_frame(line,1024,1,0,3,pcm,320));
    assert(!nomi::encode_frame(line,1024,1,0,1,pcm,319));
    uint8_t bytes[640];
    for (unsigned i=0;i<320;++i){ bytes[2*i]=uint16_t(pcm[i])&255; bytes[2*i+1]=uint16_t(pcm[i])>>8; }
    assert(nomi::frame_hash(0x12345678,0,1,bytes,sizeof(bytes))==0xbbde03bcu);
}
