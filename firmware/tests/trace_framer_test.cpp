#include "trace_framer.h"
#include <cassert>
#include <string>
#include <vector>
int main(){
    nomi::TraceFramer f;std::vector<std::string> lines;int16_t pcm[512];
    for(int i=0;i<512;++i)pcm[i]=i;
    auto write=[&](const char *p,size_t n){lines.emplace_back(p,n);return true;};
    for(int i=0;i<5;++i)assert(f.feed(1,1,pcm,512,i==1,write));
    assert(lines.size()==8);assert(lines[0].find("\n@NTRC1 00000001 00000000 1 0 ")==0);
    assert(lines[1].find(" 1 1 ")!=std::string::npos);assert(lines[7].find("00000007 1 0")!=std::string::npos);
    assert(f.feed(2,1,pcm,320,false,write));assert(lines.back().find("00000002 00000000")!=std::string::npos);
    assert(!f.feed(2,1,pcm,320,false,[](const char *,size_t){return false;}));
}
