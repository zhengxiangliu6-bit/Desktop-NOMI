# 第三方来源与修改

上游：Waveshare `ESP32-S3-Touch-LCD-1.85B`，提交
`5a98b8da1948340c07032a408ac0d93c47ca558f`，Apache-2.0。
https://github.com/waveshareteam/ESP32-S3-Touch-LCD-1.85B/tree/5a98b8da1948340c07032a408ac0d93c47ca558f

- `esp_lcd_st77916.c` / `include/esp_lcd_st77916.h`：取自官方 `examples/Arduino-V3.2.0/examples/01_lvgl_demo/`，未修改；保留 Espressif 2023 版权和 SPDX。它们使用 ESP-IDF esp_lcd 接口，可在本工程直接编译，不引入 Arduino 运行时。不将其版本冒充注册表 2.0.1。
- `panel_tables.inc`：从官方 `examples/esp-idf/01_lvgl_demo/components/esp32_s3_touch_lcd_1_85B/esp32_s3_touch_lcd_1_85B.cpp` 提取数据常量和 version_1/version_2 初始化表；添加来源说明、清理行尾空白，表中指令/数据未变。
- `nomi_panel.cpp`：Desktop-NOMI 显示专用改写。保留同板 GPIO、复位、ID 读取/表选择、QSPI 和首帧后背光流程；去除音频/存储/传感器/网络/触摸及 esp_lvgl_adapter，改为单任务 LVGL、部分双缓冲及 DMA 信号量同步。背光初值改为 60%。
- `LICENSE`：随附上游 Apache License 2.0 完整文本。上游未附独立 NOTICE 文件。

LVGL 9.5.0 从 https://github.com/lvgl/lvgl 获取，MIT，完整提交
`85aa60d18b3d5e5588d7b247abf90198f07c8a63`；依赖 checkout 自带 `LICENCE.txt`、`COPYRIGHTS.md`。分发固件时应同时附上这些许可文件及本目录许可证/来源说明。

本固件没有复制 Aora 包的 SVG、React 实现、动画数据或素材；仅参考 Desktop-NOMI 的奶油色圆形角色和语义表情，重新使用 LVGL 基本图元绘制。项目整体未选定许可证，第三方许可不等于赋予项目整体再分发授权。
