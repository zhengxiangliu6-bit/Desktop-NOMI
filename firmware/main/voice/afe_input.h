#pragma once
#include <cstddef>
#include <cstdint>
namespace nomi {
// ESP-SR sizes are BYTES. Cache is omitted speech onset, not a second channel.
template<class Consume> bool consume_afe(const int16_t *data,int bytes,const int16_t *cache,int cache_bytes,Consume consume) {
    if(!data || bytes<=0 || bytes%2 || bytes>4096 || cache_bytes<0 || cache_bytes%2 || cache_bytes>32768 || (cache_bytes && !cache))return false;
    if(cache_bytes && !consume(cache,size_t(cache_bytes)/2,true))return false;
    return consume(data,size_t(bytes)/2,false);
}
}
