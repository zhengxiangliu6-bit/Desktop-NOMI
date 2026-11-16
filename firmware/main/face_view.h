#pragma once
#include "face_model.h"
#include "lvgl.h"
namespace nomi {
class FaceView {
public:
    void create();
    void render(const Frame &frame, Phase phase);
private:
    lv_obj_t *eyes_[2]{}, *mouth_=nullptr,*open_mouth_=nullptr,*ring_=nullptr;
    lv_obj_t *dots_[3]{},*brows_[2]{},*smiles_[2]{},*hearts_[2]{},*tears_[2]{},*symbols_[3]{},*anger_[4]{};
    int symbol_kind_=-1;
    lv_point_precise_t mouth_points_[9]{},brow_points_[2][2]{},smile_points_[2][9]{},heart_points_[11]{},anger_points_[4][3]{};
};
}
