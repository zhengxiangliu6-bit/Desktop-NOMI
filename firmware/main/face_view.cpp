#include "face_view.h"
#include <algorithm>
#include <cmath>

namespace nomi {
namespace {
constexpr uint32_t INK = 0x283445, CREAM = 0xfff0d4, ACCENT = 0xe8a26e;
lv_obj_t *rounded(lv_obj_t *parent, int w, int h, uint32_t color)
{
    auto *obj = lv_obj_create(parent);
    lv_obj_remove_style_all(obj);
    lv_obj_remove_flag(obj, static_cast<lv_obj_flag_t>(LV_OBJ_FLAG_SCROLLABLE | LV_OBJ_FLAG_CLICKABLE));
    lv_obj_set_size(obj, w, h);
    lv_obj_set_style_radius(obj, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(obj, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
    return obj;
}
}
void FaceView::create()
{
    auto *screen = lv_screen_active();
    lv_obj_remove_style_all(screen);
    lv_obj_remove_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_bg_color(screen, lv_color_hex(CREAM), 0);
    lv_obj_set_style_bg_opa(screen, LV_OPA_COVER, 0);
    ring_ = rounded(screen, 288, 288, CREAM);
    lv_obj_set_style_bg_opa(ring_, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_color(ring_, lv_color_hex(ACCENT), 0);
    lv_obj_set_style_border_width(ring_, 3, 0);
    lv_obj_center(ring_);
    for (int i = 0; i < 2; ++i) {
        eyes_[i] = rounded(screen, 38, 64, INK);
        auto *cheek = rounded(screen, 28, 12, ACCENT);
        lv_obj_set_pos(cheek, i ? 258 : 74, 205);
        lv_obj_set_style_bg_opa(cheek, LV_OPA_50, 0);
    }
    mouth_ = lv_line_create(screen);
    lv_obj_remove_style_all(mouth_);
    lv_obj_set_pos(mouth_, 151, 229);
    lv_obj_set_style_line_color(mouth_, lv_color_hex(INK), 0);
    lv_obj_set_style_line_width(mouth_, 5, 0);
    lv_obj_set_style_line_rounded(mouth_, true, 0);
    open_mouth_ = rounded(screen, 26, 12, INK);
    for (int i = 0; i < 3; ++i) {
        dots_[i] = rounded(screen, 8, 8, INK);
        lv_obj_set_pos(dots_[i], 156 + i * 20, 280);
    }
}
void FaceView::render(const Frame &f, Phase phase)
{
    const auto &p = f.pose;
    for (int i = 0; i < 2; ++i) {
        const float height = i ? p.right_height : p.left_height;
        const int h = std::max(4, int(std::lround(height * (1 - f.blink))));
        lv_obj_set_size(eyes_[i], 38, h);
        lv_obj_set_pos(eyes_[i], (i ? 221 : 101) + int(p.gaze_x), 160 + int(p.gaze_y) - h / 2);
    }
    for (int i = 0; i < 9; ++i) {
        float x = float(i) / 8;
        mouth_points_[i] = {static_cast<lv_value_precise_t>(std::lround(x * 58)),
                            static_cast<lv_value_precise_t>(std::lround(14 + p.mouth_curve * (1 - (2*x-1)*(2*x-1))))};
    }
    lv_line_set_points(mouth_, mouth_points_, 9);
    const bool open = p.mouth_open > 1;
    lv_obj_set_style_opa(mouth_, open ? LV_OPA_TRANSP : LV_OPA_COVER, 0);
    const int mh = std::max(2, int(p.mouth_open));
    lv_obj_set_size(open_mouth_, 26, mh);
    lv_obj_set_pos(open_mouth_, 167, 245 - mh / 2);
    lv_obj_set_style_opa(open_mouth_, open ? LV_OPA_COVER : LV_OPA_TRANSP, 0);
    lv_obj_set_style_opa(ring_, phase == Phase::Listening ? int(70 + 120 * f.activity) : LV_OPA_TRANSP, 0);
    for (int i = 0; i < 3; ++i) {
        lv_obj_set_style_opa(dots_[i], phase == Phase::Thinking ? int(60 + 190 * std::clamp(f.activity + (i-1)*0.2f, 0.f, 1.f)) : LV_OPA_TRANSP, 0);
    }
}
}
