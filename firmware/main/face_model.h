#pragma once
#include <cstdint>
#include <string_view>

namespace nomi {
enum class Emotion { Neutral, Happy, Sad, Curious };
enum class Phase { Idle, Thinking, Listening, Speaking };
enum class View { Idle, Blink, Happy, Sad, Curious, Thinking, Listening, Speaking };
struct Pose {
    float left_height = 64, right_height = 64;
    float gaze_x = 0, gaze_y = 0, mouth_curve = 5, mouth_open = 0;
};
struct Frame {
    Pose pose;
    View view;
    float blink = 0; // 0 open, 1 closed; overlays, never changes emotion/phase.
    float activity = 0;
};
// Single owner, monotonic milliseconds. No allocations, timers, I/O or LVGL here.
class FaceModel {
public:
    explicit FaceModel(uint32_t seed = 1) : random_(seed ? seed : 1) {}
    void set_emotion(Emotion emotion, uint64_t now, uint32_t ttl = 5000);
    void set_phase(Phase phase, uint64_t now, uint32_t ttl = 5000);
    void reset(uint64_t now);
    void blink(uint64_t now);
    // Local diagnostic commands only. Unknown input resets to idle and returns false.
    bool command(std::string_view text, uint64_t now);
    Frame update(uint64_t now);
    Emotion emotion() const { return emotion_; }
    Phase phase() const { return phase_; }
private:
    uint32_t next_random();
    Emotion emotion_ = Emotion::Neutral;
    Phase phase_ = Phase::Idle;
    uint64_t emotion_until_ = 0, phase_until_ = 0, next_blink_ = 0, blink_started_ = 0;
    bool blinking_ = false;
    uint32_t random_;
    View view_ = View::Idle;
    Pose current_, from_, target_;
    uint64_t transition_ = 0;
};
const char *view_name(View view);
}
