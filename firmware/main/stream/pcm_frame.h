#pragma once
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
namespace nomi {
constexpr size_t stream_samples = 320; // 20ms, PCM16LE, 16kHz mono
inline uint32_t frame_hash(uint32_t token, uint32_t sequence, unsigned channel, const uint8_t *pcm, size_t size) {
    uint32_t hash = 2166136261u;
    for (uint32_t word : {token, sequence})
        for (unsigned i=0; i<4; ++i) { hash ^= (word >> (8*i)) & 255u; hash *= 16777619u; }
    hash ^= channel; hash *= 16777619u;
    for (size_t i=0; i<size; ++i) { hash ^= pcm[i]; hash *= 16777619u; }
    return hash;
}
// ASCII framed transport survives unrelated UTF-8 logs; checksum covers header + PCM.
inline size_t encode_frame(char *out, size_t capacity, uint32_t token, uint32_t sequence,
                           unsigned channel, const int16_t *pcm, size_t samples, unsigned flags=0) {
    if (!out || !pcm || samples != stream_samples || (channel != 1 && channel != 2) || flags>1 || capacity < 1024) return 0;
    uint8_t bytes[stream_samples*2+1]; bytes[0]=uint8_t(flags);
    for (size_t i=0; i<samples; ++i) { bytes[1+2*i] = uint16_t(pcm[i]) & 255; bytes[2+2*i] = uint16_t(pcm[i]) >> 8; }
    const auto sum = frame_hash(token, sequence, channel, bytes, sizeof(bytes));
    const int n = std::snprintf(out, capacity, "\n@NOMI2 %08lx %08lx %u %u %08lx ",
                               (unsigned long)token, (unsigned long)sequence, channel, flags, (unsigned long)sum);
    if (n < 0 || size_t(n)+860 >= capacity) return 0;
    static constexpr char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    size_t used = size_t(n);
    for (size_t i=1; i<sizeof(bytes); i+=3) {
        const size_t remaining = sizeof(bytes)-i;
        uint32_t v = uint32_t(bytes[i]) << 16;
        if (remaining > 1) v |= uint32_t(bytes[i+1]) << 8;
        if (remaining > 2) v |= bytes[i+2];
        out[used++] = alphabet[(v>>18)&63]; out[used++] = alphabet[(v>>12)&63];
        out[used++] = remaining > 1 ? alphabet[(v>>6)&63] : '=';
        out[used++] = remaining > 2 ? alphabet[v&63] : '=';
    }
    out[used++] = '\n'; out[used] = 0; return used;
}
}
