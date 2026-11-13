#pragma once
#include "face_model.h"
#include "lvgl.h"

namespace nomi {
class FaceView {
public:
    void create();
    void render(const Frame &frame, Phase phase);
private:
    lv_obj_t *eyes_[2]{}, *mouth_ = nullptr, *open_mouth_ = nullptr;
    lv_obj_t *dots_[3]{}, *ring_ = nullptr;
    lv_point_precise_t mouth_points_[9]{};
};
}
