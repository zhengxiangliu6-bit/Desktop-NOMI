#include "face_model.h"
#include <algorithm>
#include <cmath>

namespace nomi {
uint32_t FaceModel::next_random()
{
    random_ ^= random_ << 13; random_ ^= random_ >> 17; random_ ^= random_ << 5;
    return random_;
}
void FaceModel::set_emotion(Emotion e, uint64_t now, uint32_t ttl)
{
    if (e < Emotion::Neutral || e > Emotion::Curious) e = Emotion::Neutral;
    emotion_ = e;
    emotion_until_ = now + std::clamp<uint32_t>(ttl, 1, 30000);
}
void FaceModel::set_phase(Phase p, uint64_t now, uint32_t ttl)
{
    if (p < Phase::Idle || p > Phase::Speaking) p = Phase::Idle;
    phase_ = p;
    phase_until_ = now + std::clamp<uint32_t>(ttl, 1, 30000);
}
void FaceModel::reset(uint64_t now)
{
    emotion_ = Emotion::Neutral; phase_ = Phase::Idle;
    emotion_until_ = phase_until_ = 0;
    blinking_ = false;
    next_blink_ = now + 2500 + next_random() % 3500;
}
void FaceModel::blink(uint64_t now)
{
    blinking_ = true; blink_started_ = now;
}
bool FaceModel::command(std::string_view text, uint64_t now)
{
    if (text == "blink") { blink(now); return true; }
    if (text == "idle") { reset(now); return true; }
    if (text == "happy") { set_emotion(Emotion::Happy, now); return true; }
    if (text == "sad") { set_emotion(Emotion::Sad, now); return true; }
    if (text == "curious") { set_emotion(Emotion::Curious, now); return true; }
    if (text == "thinking") { set_phase(Phase::Thinking, now); return true; }
    if (text == "listening") { set_phase(Phase::Listening, now); return true; }
    if (text == "speaking") { set_phase(Phase::Speaking, now); return true; }
    reset(now);
    return false;
}
Frame FaceModel::update(uint64_t now)
{
    if (emotion_until_ && now >= emotion_until_) emotion_ = Emotion::Neutral;
    if (phase_until_ && now >= phase_until_) phase_ = Phase::Idle;
    View next = View::Idle;
    if (phase_ == Phase::Thinking) next = View::Thinking;
    else if (phase_ == Phase::Listening) next = View::Listening;
    else if (phase_ == Phase::Speaking) next = View::Speaking;
    else if (emotion_ == Emotion::Happy) next = View::Happy;
    else if (emotion_ == Emotion::Sad) next = View::Sad;
    else if (emotion_ == Emotion::Curious) next = View::Curious;
    if (next != view_) {
        view_ = next; from_ = current_; target_ = Pose{}; transition_ = now;
        if (next == View::Happy) { target_.left_height = target_.right_height = 24; target_.mouth_curve = 16; }
        if (next == View::Sad) { target_.left_height = target_.right_height = 40; target_.gaze_y = 12; target_.mouth_curve = -10; }
        if (next == View::Curious) { target_.left_height = 76; target_.right_height = 42; target_.gaze_x = 12; target_.mouth_curve = 2; }
        if (next == View::Thinking) { target_.left_height = target_.right_height = 48; target_.gaze_x = -12; target_.gaze_y = -12; target_.mouth_curve = 0; }
        if (next == View::Listening) { target_.left_height = target_.right_height = 74; target_.mouth_curve = 2; }
        if (next == View::Speaking) target_.mouth_open = 12;
    }
    float t = std::clamp(float(now - transition_) / 180.f, 0.f, 1.f);
    t = t * t * (3 - 2 * t);
    auto mix = [t](float a, float b) { return a + (b - a) * t; };
    current_ = {mix(from_.left_height, target_.left_height), mix(from_.right_height, target_.right_height),
                mix(from_.gaze_x, target_.gaze_x), mix(from_.gaze_y, target_.gaze_y),
                mix(from_.mouth_curve, target_.mouth_curve), mix(from_.mouth_open, target_.mouth_open)};
    if (!next_blink_) next_blink_ = now + 2500 + next_random() % 3500;
    if (!blinking_ && now >= next_blink_) blink(now);
    float closure = 0;
    if (blinking_) {
        uint64_t elapsed = now - blink_started_;
        if (elapsed >= 180) {
            blinking_ = false;
            next_blink_ = now + 2500 + next_random() % 3500;
        } else {
            closure = elapsed < 70 ? float(elapsed) / 70 : 1.f - float(elapsed - 70) / 110;
        }
    }
    Pose pose = current_;
    const float wave = (std::sin(float(now % 60000) * 0.009f) + 1) * 0.5f;
    if (view_ == View::Speaking) pose.mouth_open *= 0.4f + wave;
    return {pose, blinking_ ? View::Blink : view_, closure, wave};
}
const char *view_name(View v)
{
    switch (v) {
    case View::Idle: return "idle"; case View::Blink: return "blink";
    case View::Happy: return "happy"; case View::Sad: return "sad";
    case View::Curious: return "curious"; case View::Thinking: return "thinking";
    case View::Listening: return "listening"; case View::Speaking: return "speaking";
    }
    return "idle";
}
}
