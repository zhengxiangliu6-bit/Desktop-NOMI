#include "fixed_reply_player.h"
#include <cassert>
#include <vector>
#include <cstdint>
struct Sink {
    unsigned begins=0,ends=0,writes=0;bool fail=false;
    std::vector<int16_t> output;
    int speaker_begin(){++begins;return 0;}
    int speaker_write(const int16_t *pcm,size_t bytes){++writes;if(fail)return 1;output.insert(output.end(),pcm,pcm+bytes/2);return 0;}
    void speaker_end(){++ends;}
};
int main(){
    for(size_t chunk:{160,320,512,1024}){
        nomi::FixedReplyPlayer p;Sink s;std::vector<int16_t> pcm(8545);
        for(size_t i=0;i<pcm.size();++i)pcm[i]=int16_t(i);
        assert(p.begin(s,pcm.data(),pcm.size()));assert(!p.begin(s,pcm.data(),pcm.size()));
        size_t captured=0;
        while(p.active()){captured+=chunk;assert(p.pump(s,chunk));assert(captured<20000);}
        assert(captured>=15040 && captured<15040+chunk);
        assert(s.begins==1 && s.ends==1 && s.writes==27);
        for(size_t i=0;i<pcm.size();++i)assert(s.output[i*2]==pcm[i] && s.output[i*2+1]==pcm[i]);
        for(size_t i=pcm.size()*2;i<s.output.size();++i)assert(s.output[i]==0);
        assert(p.begin(s,pcm.data(),pcm.size()));s.fail=true;assert(!p.pump(s,320));assert(!p.active());assert(s.ends==2);
        assert(p.begin(s,pcm.data(),pcm.size()));p.cancel(s);assert(!p.active());
        assert(!p.begin(s,pcm.data(),48001));
    }
}
