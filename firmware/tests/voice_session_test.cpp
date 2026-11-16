#include "voice_session.h"
#include <cassert>
#include <limits>
using namespace nomi;
int main() {
    VoiceSession s;
    auto send = [&](int id, uint64_t at, float p=0.95f, uint32_t epoch=1, bool demo=false) {
        return s.accept({epoch,id,p,at},1,at,demo);
    };
    VoiceSession calibrated;
    assert(calibrated.accept({1,1,0.65f,10},1,10,false)==VoiceAction::Ignore);
    assert(calibrated.accept({1,1,0.65f,20},1,20,false,0.60f)==VoiceAction::Wake);
    assert(calibrated.accept({1,2,0.59f,30},1,30,false,0.60f)==VoiceAction::Ignore);
    assert(calibrated.accept({1,2,0.65f,40},1,40,false,0.60f)==VoiceAction::Expression);
    assert(calibrated.accept({1,1,0.99f,50},1,50,false,0.1f)==VoiceAction::Ignore);
    // Expressions cannot bypass activation; failed activation doesn't open a window.
    assert(send(2,100)==VoiceAction::Ignore);
    assert(send(1,200,0.89f)==VoiceAction::Ignore);
    assert(send(1,300,std::numeric_limits<float>::quiet_NaN())==VoiceAction::Ignore);
    assert(send(1,400,0.95f,2)==VoiceAction::Ignore);
    assert(send(1,500,0.95f,1,true)==VoiceAction::Ignore);
    assert(!s.listening(500));
    assert(send(1,1000)==VoiceAction::Wake);
    assert(s.listening(1000));
    assert(send(1,1100)==VoiceAction::Ignore); // same utterance/debounce
    assert(send(2,1500)==VoiceAction::Expression);
    assert(send(2,1600)==VoiceAction::Ignore);
    for (const auto &c : voice_commands) assert(voice_command(c.id)==&c);
    assert(send(1,1800)==VoiceAction::Extend);
    for(int id=12;id<=17;++id)assert(send(id,1800+(id-11)*10)==VoiceAction::Expression);
    assert(send(999,1800)==VoiceAction::Ignore);
    assert(send(10,2000)==VoiceAction::Sleep);
    assert(send(2,2100)==VoiceAction::Ignore);
    assert(send(1,3000)==VoiceAction::Wake);
    assert(s.tick(22999)==VoiceAction::Ignore);
    assert(s.tick(23000)==VoiceAction::Timeout);
    assert(send(2,23001)==VoiceAction::Ignore);
    assert(send(1,23500)==VoiceAction::Wake);
    // An event at expiry must not silently consume the UI's timeout transition.
    assert(send(2,43500)==VoiceAction::Ignore);
    assert(s.tick(43500)==VoiceAction::Timeout);
    // Queued old events, manual reset/off/reinit and decoder latency cannot wake UI.
    s.reset(44000);
    assert(s.accept({1,1,0.95f,43999},1,44001,false)==VoiceAction::Ignore);
    assert(s.accept({1,1,0.95f,45000},1,47000,false)==VoiceAction::Ignore);
    assert(s.accept({1,1,0.95f,49000},1,48000,false)==VoiceAction::Ignore);
    assert(send(1,50000)==VoiceAction::Wake);
    assert(send(9,51000)==VoiceAction::Sleep);
    assert(send(1,52000)==VoiceAction::Wake);
    assert(send(11,53000)==VoiceAction::Expression);
    assert(send(3,72999)==VoiceAction::Expression); // accepted commands renew window
    assert(s.tick(92999)==VoiceAction::Timeout);
}
