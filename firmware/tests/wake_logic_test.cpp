#include "wake_logic.h"
#include <cstdio>
#include <cstdlib>
#include <limits>
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);std::exit(1); } } while(0)
int main()
{
    nomi::WakeLatch ui;
    CHECK(!ui.accept({1,1,true},2,false)); // event queued before disable/reinit
    CHECK(!ui.accept({2,1,false},2,false)); // no unverified model event
    CHECK(!ui.accept({2,2,true},2,false));
    CHECK(!ui.accept({2,1,true},2,true)); // demo must keep all H1 expressions
    CHECK(!ui.held());
    CHECK(ui.accept({2,1,true},2,false)); CHECK(ui.held());
    CHECK(!ui.accept({2,1,true},2,false));
    ui.clear(); CHECK(!ui.held());
    CHECK(!ui.accept({2,1,true},3,false));
    CHECK(ui.accept({3,1,true},3,false));
    ui.clear();
    const int16_t stereo[] = {-32768,32767, 0,-17, 1234,0, -99,32760};
    int16_t mono[4]{}; nomi::PcmLevel level;
    CHECK(nomi::unpack_pcm(stereo,8,mono,4,level));
    CHECK(mono[0]==-32768 && mono[1]==0 && mono[2]==1234 && mono[3]==-99);
    CHECK(level.peak[0]==32768 && level.peak[1]==32767);
    CHECK(level.clipped[0]==1 && level.clipped[1]==2);
    CHECK(level.energy[0]==uint64_t(32768)*32768+uint64_t(1234)*1234+99*99);
    CHECK(!nomi::unpack_pcm(stereo,7,mono,4,level));
    CHECK(!nomi::unpack_pcm(stereo,8,mono,3,level));
    CHECK(!nomi::unpack_pcm(nullptr,8,mono,4,level));
    CHECK(!nomi::unpack_pcm(stereo,0,mono,4,level));
    const int16_t silence[8]{};
    CHECK(nomi::unpack_pcm(silence,8,mono,4,level));
    CHECK(!level.peak[0] && !level.energy[1] && !level.clipped[0]);
    // Long event bursts cannot silently unlatch the UI or accept a stale session.
    for (uint32_t epoch=4; epoch<10000; ++epoch) {
        ui.clear(); CHECK(!ui.accept({epoch-1,1,true},epoch,false));
        CHECK(ui.accept({epoch,1,true},epoch,false));
        for (int i=0;i<4;++i) CHECK(!ui.accept({epoch,1,true},epoch,false));
    }
    std::puts("PASS: stale/duplicate/model/demo gating, Listening latch, stereo contract, clipping, silence");
}
