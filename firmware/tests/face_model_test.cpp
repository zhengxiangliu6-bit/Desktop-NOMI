#include "face_model.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>

#define CHECK(x) do { if (!(x)) { std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); std::exit(1); } } while (0)
using namespace nomi;
int main()
{
    FaceModel m;
    m.reset(0);
    CHECK(m.update(0).view == View::Idle);
    struct Example { const char *command; View view; };
    for (auto item : {Example{"happy", View::Happy}, Example{"sad", View::Sad},
                      Example{"curious", View::Curious}, Example{"thinking", View::Thinking},
                      Example{"listening", View::Listening}, Example{"speaking", View::Speaking}}) {
        m.reset(0); CHECK(m.command(item.command, 0));
        CHECK(m.update(200).view == item.view);
        auto expired = m.update(5000);
        CHECK(m.phase() == Phase::Idle && m.emotion() == Emotion::Neutral);
        CHECK(expired.view == View::Idle || expired.view == View::Blink);
    }
    m.reset(0); m.set_emotion(Emotion::Happy, 0, 2000);
    m.update(200);
    m.set_phase(Phase::Thinking, 300, 500);
    CHECK(m.update(300).view == View::Thinking);
    CHECK(m.emotion() == Emotion::Happy);
    CHECK(m.update(800).view == View::Happy);
    m.set_phase(Phase::Speaking, 900, 5000);
    m.update(2000);
    CHECK(m.emotion() == Emotion::Neutral); // A busy phase never extends emotion TTL.
    m.reset(0); m.command("curious", 0); m.update(200);
    m.blink(300);
    CHECK(m.update(370).blink == 1.f);
    CHECK(m.update(480).view == View::Curious);
    CHECK(m.emotion() == Emotion::Curious);
    CHECK(!m.command("invalid", 500));
    CHECK(m.phase() == Phase::Idle && m.emotion() == Emotion::Neutral);
    m.set_phase(static_cast<Phase>(99), 600);
    m.set_emotion(static_cast<Emotion>(99), 600);
    CHECK(m.phase() == Phase::Idle && m.emotion() == Emotion::Neutral);
    m = FaceModel{};
    m.reset(0); m.update(0); m.command("sad", 100);
    auto start = m.update(100).pose;
    auto middle = m.update(190).pose;
    auto end = m.update(280).pose;
    CHECK(start.left_height == 64 && end.left_height == 40);
    CHECK(middle.left_height < start.left_height && middle.left_height > end.left_height);
    // Long running, transitions, clock crossing 32-bit milliseconds: bounded geometry.
    m.reset(0); unsigned blinks = 0; bool was = false;
    for (uint64_t t = 0; t < 120000; t += 20) {
        auto f = m.update(t); bool is = f.view == View::Blink;
        if (is && !was) ++blinks;
        was = is;
        CHECK(f.blink >= 0 && f.blink <= 1 && std::isfinite(f.pose.left_height));
    }
    CHECK(blinks >= 15 && blinks <= 50);
    const uint64_t wrap = uint64_t(1) << 32;
    m.reset(wrap - 100); m.set_phase(Phase::Listening, wrap - 100, 200);
    CHECK(m.update(wrap).view == View::Listening);
    CHECK(m.update(wrap + 100).view == View::Idle);
    m.reset(0); m.set_emotion(Emotion::Happy, 0, 0);
    m.update(1); CHECK(m.emotion() == Emotion::Neutral);
    m.set_phase(Phase::Thinking, 0, 0xffffffff);
    m.update(30000); CHECK(m.phase() == Phase::Idle);
    std::puts("PASS: expressions, TTL, phase/emotion priority, blink overlay, fallback, interpolation, long-run and clock rollover");
}
