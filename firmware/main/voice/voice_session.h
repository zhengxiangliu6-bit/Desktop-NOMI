#pragma once
#include <cmath>
#include <cstdint>
namespace nomi {
struct VoiceCommand { int id; const char *pinyin; const char *face; const char *label; };
// Positive IDs are stable protocol identifiers. Wake phrase is configured separately.
inline constexpr VoiceCommand voice_commands[] = {
    {2, "kai xin yi dian", "happy", "开心一点"},
    {3, "nan guo yi dian", "sad", "难过一点"},
    {4, "zha yi xia yan", "blink", "眨一下眼"},
    {5, "hao qi yi dian", "curious", "好奇一点"},
    {6, "si kao yi xia", "thinking", "思考一下"},
    {7, "ren zhen ting jiang", "listening", "认真听讲"},
    {8, "shuo hua biao qing", "speaking", "说话表情"},
    {9, "hui dao dai ji", "idle", "回到待机"},
    {10, "xiu xi yi xia", nullptr, "休息一下"},
    {11, "biao qing yan shi", "demo", "表情演示"},
};
inline const VoiceCommand *voice_command(int id) {
    for (const auto &c : voice_commands) if (c.id == id) return &c;
    return nullptr;
}
struct VoiceEvent { uint32_t epoch; int id; float probability; uint64_t at_ms; };
enum class VoiceAction { Ignore, Wake, Expression, Sleep, Timeout };
// UI task owns this gate. Recognition and FaceModel never own conversational state.
class VoiceSession {
public:
    static constexpr uint64_t window_ms = 20000;
    void reset(uint64_t now) { until_ = 0; cutoff_ = now; last_id_ = 0; }
    bool listening(uint64_t now) const { return until_ && now < until_; }
    VoiceAction tick(uint64_t now) {
        if (until_ && now >= until_) { reset(now); return VoiceAction::Timeout; }
        return VoiceAction::Ignore;
    }
    VoiceAction accept(VoiceEvent e, uint32_t epoch, uint64_t now, bool demo) {
        if (demo || e.epoch != epoch || e.at_ms <= cutoff_ || e.at_ms > now ||
            now-e.at_ms > 1500 || !std::isfinite(e.probability) || e.probability < 0.90f ||
            e.probability > 1.0f || (last_id_ && e.at_ms < last_at_) || (e.id != 1 && !voice_command(e.id))) return VoiceAction::Ignore;
        if (e.id == last_id_ && e.at_ms-last_at_ < 1200) return VoiceAction::Ignore;
        if (e.id != 1 && (!listening(now) || !listening(e.at_ms))) return VoiceAction::Ignore;
        last_id_ = e.id; last_at_ = e.at_ms;
        if (e.id == 1) { until_ = e.at_ms+window_ms; return VoiceAction::Wake; }
        if (e.id == 10 || e.id == 9) { reset(now); return VoiceAction::Sleep; }
        until_ = e.at_ms+window_ms;
        return VoiceAction::Expression;
    }
private:
    uint64_t until_ = 0, cutoff_ = 0, last_at_ = 0;
    int last_id_ = 0;
};
}
