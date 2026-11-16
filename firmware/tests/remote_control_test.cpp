#include "remote_control.h"
#include <cassert>
#include <cstring>
int main() {
    nomi::RemoteControl c;
    using E=nomi::RemoteEffect;
    assert(!std::strcmp(c.apply(1,0,"probe",0,true).status,"OK"));
    assert(c.apply(1,1,"listening",100,true).effect==E::Face);
    assert(c.hold(101));
    assert(c.apply(1,2,"happy",1000,true).effect==E::Face);
    assert(!c.hold(5999));assert(c.hold(6000));
    assert(c.apply(1,3,"extend",2000,true).effect==E::None);
    assert(!c.hold(5999)); // re-wake never interrupts the expression or resets its preview
    assert(c.apply(1,3,"extend",10000,true).effect==E::None); // duplicate must not renew deadline
    assert(c.expire(22000,true));assert(!c.hold(22000));
    assert(!std::strcmp(c.apply(1,4,"extend",23000,true).status,"ASLEEP"));
    assert(!std::strcmp(c.apply(1,2,"sad",23001,true).status,"STALE"));
    assert(!std::strcmp(c.apply(1,5,"demo",23002,true).status,"INVALID"));
    assert(!std::strcmp(c.apply(2,0,"probe",24000,false).status,"STALE"));
    assert(c.apply(2,0,"listening",24000,true).effect==E::Face);
    assert(c.expire(24001,false)); // lease loss returns to idle
    assert(c.apply(2,1,"listening",25000,true).effect==E::Face);
    assert(c.apply(2,2,"idle",26000,true).effect==E::Face);assert(!c.hold(26001));
    c.apply(2,3,"listening",27000,true);
    assert(c.apply(3,0,"probe",27001,true).effect==E::Reset);
    assert(!c.hold(27002));
    nomi::RemoteControl gallery;
    assert(gallery.apply(10,0,"probeall",0,true).effect==E::Reset);
    uint32_t sequence=1;
    for (const auto &design:nomi::face_designs) {
        assert(nomi::remote_face(design.command));
        assert(gallery.apply(10,sequence++,design.command,100,true).effect==E::Face);
    }
    assert(sequence==15);
    assert(!nomi::remote_face("unsupported"));
    char ack[120];
    auto n=nomi::encode_control_ack(ack,sizeof(ack),1,0,"probe","OK");
    assert(n && !std::strncmp(ack,"\n@NOMI_ACK1 00000001 00000000 probe OK ",37));
    assert(!std::strcmp(ack,"\n@NOMI_ACK1 00000001 00000000 probe OK e568b8dc\n"));
    assert(!nomi::encode_control_ack(ack,4,1,0,"probe","OK"));
}
