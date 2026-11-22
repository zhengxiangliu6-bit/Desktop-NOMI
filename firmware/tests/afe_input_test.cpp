#include "afe_input.h"
#include <cassert>
#include <vector>
int main(){
    int16_t cache[]={1,2,3},data[]={4,5};std::vector<int16_t> output;
    auto consume=[&](const int16_t *p,size_t n,bool){output.insert(output.end(),p,p+n);return true;};
    assert(nomi::consume_afe(data,4,cache,6,consume));assert((output==std::vector<int16_t>{1,2,3,4,5}));
    output.clear();assert(nomi::consume_afe(data,4,nullptr,0,consume));assert((output==std::vector<int16_t>{4,5}));
    assert(!nomi::consume_afe(data,4,nullptr,6,consume));assert(!nomi::consume_afe(data,3,cache,6,consume));
    assert(!nomi::consume_afe(data,4,cache,-2,consume));assert(!nomi::consume_afe(data,4,cache,32770,consume));
    int calls=0;assert(!nomi::consume_afe(data,4,cache,6,[&](const int16_t *,size_t,bool){++calls;return false;}));assert(calls==1);
}
