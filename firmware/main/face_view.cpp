#include "face_view.h"
#include "face_catalog.h"
#include <algorithm>
#include <cmath>
#include <iterator>
namespace nomi {
namespace {
constexpr uint32_t INK=0x283445,CREAM=0xfff0d4,ACCENT=0xe8a26e,PINK=0xd76888;
lv_obj_t *rounded(lv_obj_t *parent,int w,int h,uint32_t color) {
    auto *o=lv_obj_create(parent);lv_obj_remove_style_all(o);
    lv_obj_remove_flag(o,static_cast<lv_obj_flag_t>(LV_OBJ_FLAG_SCROLLABLE|LV_OBJ_FLAG_CLICKABLE));
    lv_obj_set_size(o,w,h);lv_obj_set_style_radius(o,LV_RADIUS_CIRCLE,0);
    lv_obj_set_style_bg_color(o,lv_color_hex(color),0);lv_obj_set_style_bg_opa(o,LV_OPA_COVER,0);return o;
}
lv_obj_t *line(lv_obj_t *parent,uint32_t color,int width) {
    auto *o=lv_line_create(parent);lv_obj_remove_style_all(o);
    lv_obj_set_style_line_color(o,lv_color_hex(color),0);lv_obj_set_style_line_width(o,width,0);
    lv_obj_set_style_line_rounded(o,true,0);return o;
}
void opacity(lv_obj_t *o,int value) {lv_obj_set_style_opa(o,value,0);}
}
void FaceView::create() {
    auto *s=lv_screen_active();lv_obj_remove_style_all(s);lv_obj_remove_flag(s,LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_bg_color(s,lv_color_hex(CREAM),0);lv_obj_set_style_bg_opa(s,LV_OPA_COVER,0);
    ring_=rounded(s,288,288,CREAM);lv_obj_set_style_bg_opa(ring_,LV_OPA_TRANSP,0);
    lv_obj_set_style_border_color(ring_,lv_color_hex(ACCENT),0);lv_obj_set_style_border_width(ring_,4,0);lv_obj_center(ring_);
    const lv_point_precise_t heart[]={{24,43},{2,21},{2,9},{10,2},{19,2},{24,10},{29,2},{38,2},{46,9},{46,21},{24,43}};
    std::copy(std::begin(heart),std::end(heart),heart_points_);
    for (int i=0;i<2;++i) {
        eyes_[i]=rounded(s,38,64,INK);brows_[i]=line(s,INK,5);smiles_[i]=line(s,INK,6);
        hearts_[i]=line(s,PINK,7);lv_line_set_points(hearts_[i],heart_points_,11);
        tears_[i]=rounded(s,10,28,0x72b7d2);
        auto *cheek=rounded(s,28,12,ACCENT);lv_obj_set_pos(cheek,i?258:74,205);opacity(cheek,128);
    }
    mouth_=line(s,INK,5);lv_obj_set_pos(mouth_,151,229);open_mouth_=rounded(s,26,12,INK);
    for (int i=0;i<3;++i) {
        dots_[i]=rounded(s,8,8,INK);lv_obj_set_pos(dots_[i],156+i*20,280);
        symbols_[i]=lv_label_create(s);lv_obj_set_style_text_color(symbols_[i],lv_color_hex(INK),0);
        lv_label_set_text(symbols_[i],"Z");lv_obj_set_pos(symbols_[i],250+i*12,92-i*14);
    }
    for (int i=0;i<4;++i) {
        anger_[i]=line(s,0xd86052,4);
        const int x=i%2?12:0,y=i/2?12:0;
        anger_points_[i][0]={lv_value_precise_t(x),lv_value_precise_t(y+8)};
        anger_points_[i][1]={lv_value_precise_t(x),lv_value_precise_t(y)};
        anger_points_[i][2]={lv_value_precise_t(x+8),lv_value_precise_t(y)};
        lv_line_set_points(anger_[i],anger_points_[i],3);lv_obj_set_pos(anger_[i],266,99);
    }
}
void FaceView::render(const Frame &f,Phase phase) {
    const auto &p=f.pose;const auto &d=face_design(f.expression);
    for (int i=0;i<2;++i) {
        const int cx=(i?240:120)+int(p.gaze_x),cy=160+int(p.gaze_y);
        const int w=int(i?p.right_width:p.left_width),h=std::max(4,int(std::lround((i?p.right_height:p.left_height)*(1-f.blink))));
        lv_obj_set_size(eyes_[i],w,h);lv_obj_set_pos(eyes_[i],cx-w/2,cy-h/2);
        opacity(eyes_[i],d.eyes==EyeKind::Normal?255:0);
        lv_obj_set_pos(brows_[i],cx-24,86+int(p.gaze_y+p.brow_raise));
        const float angle=i?p.brow_right:p.brow_left;
        brow_points_[i][0]={0,lv_value_precise_t(20-angle/2)};
        brow_points_[i][1]={48,lv_value_precise_t(20+angle/2)};
        lv_line_set_points(brows_[i],brow_points_[i],2);opacity(brows_[i],int(255*p.brow_opa));
        for (int j=0;j<9;++j) {float t=float(j)/8;smile_points_[i][j]={lv_value_precise_t(t*w),lv_value_precise_t(14*(2*t-1)*(2*t-1))};}
        lv_line_set_points(smiles_[i],smile_points_[i],9);lv_obj_set_pos(smiles_[i],cx-w/2,cy-7);
        opacity(smiles_[i],d.eyes==EyeKind::Smile?int(255*(1-f.blink)):0);
        lv_obj_set_pos(hearts_[i],cx-24,cy-23);opacity(hearts_[i],d.eyes==EyeKind::Heart?int(255*(1-f.blink)):0);
        lv_obj_set_pos(tears_[i],i?257:93,185+int(f.activity*5));opacity(tears_[i],d.decor==Decoration::Tears?255:0);
    }
    for (int i=0;i<9;++i) {float x=float(i)/8;mouth_points_[i]={lv_value_precise_t(std::lround(x*58)),lv_value_precise_t(d.zigzag?14+(i%2?5:-5):std::lround(14+p.mouth_curve*(1-(2*x-1)*(2*x-1))))};}
    lv_line_set_points(mouth_,mouth_points_,9);bool open=p.mouth_open>1;opacity(mouth_,open?0:255);
    int mh=std::max(2,int(p.mouth_open)),mw=f.expression==View::Surprised?42:26;
    lv_obj_set_size(open_mouth_,mw,mh);lv_obj_set_pos(open_mouth_,180-mw/2,245-mh/2);opacity(open_mouth_,open?255:0);
    opacity(ring_,phase==Phase::Listening?int(70+120*f.activity):0);
    const int symbol_kind=d.decor==Decoration::Sleep?1:d.decor==Decoration::Question?2:d.decor==Decoration::Exclaim?3:0;
    if(symbol_kind_!=symbol_kind) {
        symbol_kind_=symbol_kind;
        for(auto *o:symbols_)lv_label_set_text(o,symbol_kind==1?"Z":symbol_kind==2?"?":"!");
    }
    for(int i=0;i<3;++i) {
        opacity(dots_[i],d.decor==Decoration::Dots?int(60+190*std::clamp(f.activity+(i-1)*0.2f,0.f,1.f)):0);
        bool sleep=d.decor==Decoration::Sleep,single=i==0&&(d.decor==Decoration::Question||d.decor==Decoration::Exclaim);
        opacity(symbols_[i],sleep||single?255:0);
    }
    for(auto *o:anger_)opacity(o,d.decor==Decoration::Anger?255:0);
}
}
