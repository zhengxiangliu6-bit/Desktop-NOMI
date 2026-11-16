#include "playback_guard.h"
#include "remote_control.h"
#include <cassert>
int main() {
    nomi::PlaybackGuard g;
    assert(!g.active());assert(!g.begin(0));assert(g.begin(7883));
    assert(!g.begin(7883));
    unsigned frames=0,writes=0,mutes=0,finished=0;size_t samples=0;
    while(g.active()) { ++frames; if(g.writing()){++writes;samples+=g.copy_samples();}
        if(g.should_mute())++mutes;
        if(g.step())++finished;
    }
    assert(frames==45 && writes==25 && samples==7883 && mutes==1 && finished==1);
    assert(g.begin(320));g.cancel();assert(!g.active());
    nomi::RemoteControl c;
    c.apply(1,0,"probe",0,true,false);
    assert(c.apply(1,1,"happy",1,true,true).effect==nomi::RemoteEffect::Face);
    assert(c.apply(1,1,"happy",2,true,true).effect==nomi::RemoteEffect::None); // Never say OK twice for a retry.
    assert(!std::strcmp(c.apply(1,1,"happy",3,true,false).status,"STALE"));
}
