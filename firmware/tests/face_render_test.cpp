#include "face_model.h"
#include "face_view.h"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
std::array<uint8_t, 360 * 360 * 3> pixels;
std::array<uint8_t, 360 * 16 * 3> buffer;
void flush(lv_display_t *d, const lv_area_t *a, uint8_t *p)
{
    const size_t stride = (a->x2 - a->x1 + 1) * 3;
    for (int y = a->y1; y <= a->y2; ++y) {
        std::memcpy(pixels.data() + (y * 360 + a->x1) * 3, p, stride); p += stride;
    }
    lv_display_flush_ready(d);
}
void check(bool ok, const char *why)
{
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", why); std::exit(1); }
}
}
int main()
{
    lv_init();
    auto *d = lv_display_create(360, 360);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB888);
    lv_display_set_buffers(d, buffer.data(), nullptr, buffer.size(), LV_DISPLAY_RENDER_MODE_PARTIAL);
    lv_display_set_flush_cb(d, flush);
    nomi::FaceView view; view.create();
    nomi::FaceModel model;
    std::array<uint8_t, 360 * 360 * 3> previous{};
    for (auto name : {"idle", "blink", "happy", "sad", "curious", "thinking", "listening", "speaking"}) {
        model.reset(0); model.command(name, 0); model.update(0);
        auto frame = model.update(!std::strcmp(name, "blink") ? 70 : 200);
        view.render(frame, model.phase());
        lv_obj_invalidate(lv_screen_active()); lv_refr_now(d);
        unsigned ink = 0;
        for (int y = 0; y < 360; ++y) for (int x = 0; x < 360; ++x) {
            const uint8_t *p = pixels.data() + (y * 360 + x) * 3;
            bool background = p[0] == 0xd4 && p[1] == 0xf0 && p[2] == 0xff;
            if (!background) {
                ++ink;
                check((x-180)*(x-180)+(y-180)*(y-180) <= 160*160, "face exceeds 160px safe radius");
            }
        }
        check(ink > 500, "empty face");
        check(pixels != previous, "consecutive expressions are visually identical");
        previous = pixels;
        char path[64]; std::snprintf(path, sizeof(path), "%s.ppm", name);
        auto *out = std::fopen(path, "wb"); check(out, "cannot save render");
        std::fprintf(out, "P6\n360 360\n255\n");
        for (size_t i = 0; i < pixels.size(); i += 3) {
            std::fputc(pixels[i+2], out); std::fputc(pixels[i+1], out); std::fputc(pixels[i], out);
        }
        std::fclose(out);
        std::printf("PASS render: %s, %u foreground pixels within safe radius\n", name, ink);
    }
    lv_deinit();
}
