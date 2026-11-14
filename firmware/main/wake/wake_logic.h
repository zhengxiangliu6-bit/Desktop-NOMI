#pragma once
#include <cstddef>
#include <cstdint>
namespace nomi {
struct WakeEvent { uint32_t epoch; uint32_t word_index; bool benchmark; };
class WakeLatch {
public:
    bool accept(WakeEvent event, uint32_t current_epoch, bool demo)
    {
        if (demo || event.epoch != current_epoch || event.word_index != 1 || !event.benchmark || held_) return false;
        held_ = true; return true;
    }
    void clear() { held_ = false; }
    bool held() const { return held_; }
private:
    bool held_ = false;
};
struct PcmLevel { uint32_t peak[2]{}; uint32_t clipped[2]{}; uint64_t energy[2]{}; };
// Slot0 MIC1 -> AFE "M", MIC2 measured only. No fabricated reference channel.
inline bool unpack_pcm(const int16_t *stereo, size_t samples, int16_t *mono, size_t capacity, PcmLevel &level)
{
    if (!stereo || !mono || !samples || samples % 2 || samples / 2 > capacity) return false;
    level = {};
    for (size_t i = 0; i < samples / 2; ++i) {
        mono[i] = stereo[i * 2];
        for (unsigned ch = 0; ch < 2; ++ch) {
            const int32_t x = stereo[i*2+ch];
            const uint32_t amplitude = x < 0 ? -x : x;
            if (amplitude > level.peak[ch]) level.peak[ch] = amplitude;
            if (amplitude >= 32760) ++level.clipped[ch];
            level.energy[ch] += int64_t(x) * x;
        }
    }
    return true;
}
}
