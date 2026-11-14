# H2 音频与 ESP-SR 来源

音频引脚和初始化参考 Waveshare ESP32-S3-Touch-LCD-1.85B 官方提交
`5a98b8da1948340c07032a408ac0d93c47ca558f`：
`examples/esp-idf/06_mic_test/components/esp32_s3_touch_lcd_1_85B/esp32_s3_touch_lcd_1_85B.cpp`、
`components/bsp_extra/src/bsp_board_extra.cpp`、`main/MicTest.cpp`。
上游 Apache-2.0；完整许可随显示组件 `components/nomi_panel/LICENSE` 及构建 ZIP 附送。
本模块是显示 BSP 之外的采集专用改写：固定双麦 PCM16/16kHz，MIC1 输入 AFE，MIC2 仅电平诊断；
不复制原厂录音/回放/UI/联网代码。不启用功放，ES8311 静音。ES7210/ES8311 API 使用独立锁定的 esp_codec_dev。

版本及完整 Git SHA / 基准模型文件 SHA256 以 `firmware/dependencies.lock.json` 为唯一清单：

- ESP-SR manifest **2.0.1**，Git tag 名为 **v2.0.0**，以完整提交核验，不能按 tag 名误报运行组件版本。使用成熟 WakeNet9/AFE V2 API；没有追随 master 2.6.2/WakeNet10 的 esp-dl、dl_fft 等额外依赖。已针对 IDF 5.5.4 构建检查；运行兼容性仍待硬件验证。
- ESP-DSP **1.4.14**，满足该 ESP-SR manifest 的 `<=1.5.0` 约束；组件名 `espressif__esp-dsp` 对应上游 CMake。上游 Apache-2.0。
- esp_codec_dev **1.6.2**，来自 ESP-ADF 固定提交，仅使用该组件，**未引入 ESP-ADF 框架**。官方微雪示例锁定 1.5.5，本工程明确使用 1.6.2 的 IDF 5.3+ 新 I²C/I²S API 与资源释放接口，不能把它说成未经变更的官方完整 BSP。上游 Apache-2.0。
- LVGL **9.5.0** 保持 H1 固定提交，MIT。

ESP-SR 与所用模型许可为 **ESPRESSIF MIT License**，限 Espressif 产品使用，并非无条件通用 MIT。
WakeNet 模型为上游预编译推理库配套二进制（`wn9_index` / `wn9_data` / `_MODEL_INFO_`），
不是 ONNX/TFLite 文件；由上游 movemodel.py/pack_model.py 打包至 model 数据分区。
上游 CMake 声明了 TTS/MultiNet 静态库，但本固件不调用这些运行入口、不加载其模型；打包前检查 ELF。
ZIP 附送全部相关许可，未复制训练数据或个人音频。

**唯一测试唤醒模型：`wn9_xiaoaitongxue` =「小爱同学」，不是「小米同学」。**
默认 audio profile 不带唤醒模型；benchmark profile 才带此测试模型。
目标词「小米同学」专用模型尚不可用；也不把「小明同学」当作目标词。
