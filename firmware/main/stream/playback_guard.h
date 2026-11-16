#pragma once
#include <cstddef>
namespace nomi {
// 20ms frames. Keep pumping RX while DAC plays; discard mic input, preserve PCM sequencing.
class PlaybackGuard {
public:
    bool begin(size_t samples) {
        if (active() || !samples) return false;
        samples_=samples; offset_=0; remaining_=(samples+319)/320+5+15; return true;
    }
    bool active() const { return remaining_!=0; }
    bool writing() const { return active() && offset_<samples_; }
    size_t offset() const { return offset_; }
    size_t copy_samples() const { return writing() ? (samples_-offset_<320?samples_-offset_:320):0; }
    // Drain 5 DMA frames after the final write, then mute; 15 more frames for acoustic tail.
    bool should_mute() const { return active() && !writing() && remaining_==15; }
    bool step() {
        if (!active()) return false;
        if (writing()) offset_+=copy_samples();
        return --remaining_==0;
    }
    void cancel() { remaining_=offset_=samples_=0; }
private:
    size_t samples_=0,offset_=0,remaining_=0;
};
}
