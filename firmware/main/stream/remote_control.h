#pragma once
#include <cstdint>
#include <cstring>
#include <cstdio>
#include "pcm_frame.h"
#include "face_catalog.h"
namespace nomi {
enum class RemoteEffect { None, Face, Reset };
struct RemoteReply { const char *status; RemoteEffect effect = RemoteEffect::None; };
inline bool remote_face(const char *cmd) {
    for (const auto &d:face_designs)
        if (!std::strcmp(d.command,cmd)) return true;
    return false;
}
class RemoteControl {
public:
    RemoteReply apply(uint32_t token, uint32_t seq, const char *cmd, uint64_t now, bool valid_session, bool spoken=false) {
        if (!token || !valid_session) return {"STALE"};
        if (!remote_face(cmd) && std::strcmp(cmd,"probe") && std::strcmp(cmd,"probeall") && std::strcmp(cmd,"extend")) return {"INVALID"};
        const bool new_token=token!=token_;
        if (new_token) { token_=token; have_seq_=false; until_=feedback_=0; }
        if (have_seq_ && seq <= sequence_) {
            if (seq == sequence_ && !std::strcmp(command_,cmd) && spoken==spoken_) return {status_}; // No replay side effects or TTL renewal.
            return {"STALE"};
        }
        sequence_=seq; have_seq_=true; spoken_=spoken; std::snprintf(command_,sizeof(command_),"%s",cmd);
        status_="OK";
        if (!std::strcmp(cmd,"probe") || !std::strcmp(cmd,"probeall")) return {status_,new_token?RemoteEffect::Reset:RemoteEffect::None};
        if (!std::strcmp(cmd,"extend")) {
            if (!until_ || now>=until_) { status_="ASLEEP"; return {status_}; }
            until_=now+20000; return {status_};
        }
        if (!std::strcmp(cmd,"idle")) until_=feedback_=0;
        else { until_=now+20000; feedback_=now+(!std::strcmp(cmd,"listening")?0:5000); }
        return {status_,RemoteEffect::Face};
    }
    bool hold(uint64_t now) const { return until_ && now<until_ && now>=feedback_; }
    bool expire(uint64_t now, bool lease) {
        if (until_ && (now>=until_ || !lease)) { clear(); return true; }
        return false;
    }
    void clear() { until_=feedback_=0; }
    uint32_t token() const { return token_; }
private:
    uint32_t token_=0, sequence_=0;
    bool have_seq_=false, spoken_=false;
    uint64_t until_=0, feedback_=0;
    char command_[12]{};
    const char *status_="OK";
};
inline size_t encode_control_ack(char *out, size_t capacity, uint32_t token, uint32_t seq,
                                 const char *cmd, const char *status) {
    char payload[40];
    const int p=std::snprintf(payload,sizeof(payload),"%s %s",cmd,status);
    if (p<0 || size_t(p)>=sizeof(payload)) return 0;
    const auto sum=frame_hash(token,seq,0,reinterpret_cast<const uint8_t *>(payload),size_t(p));
    const int n=std::snprintf(out,capacity,"\n@NOMI_ACK1 %08lx %08lx %s %08lx\n",
                              (unsigned long)token,(unsigned long)seq,payload,(unsigned long)sum);
    return n>0 && size_t(n)<capacity ? size_t(n):0;
}
}
