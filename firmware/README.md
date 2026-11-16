> **当前0.6.0：ESP32本地有限指令→14表情→固定回复**，无需PC识别/网络。新增WAV导入工具和重建步骤，沿用占位音频待用户提供替代；实体识别/播放仍待验收。见[离线闭环与音频替换指南](../docs/OFFLINE_COMMAND_REPLY.md)。以下版本保留历史记录。

> **0.5.1固定回应音色更新**：免费MeloTTS仅在开发时离线生成短PCM，设备不运行神经TTS；兼容PC0.5.0，不改指令/别名/20秒会话。新版实体听测待验。脱离电脑及AI决策见[方案对比](../docs/VOICE_NEXT_PLAN.md)。

> **当前0.5.0：14种明显不同的圆屏表情、网页图库、可静音测试的固定回应。** 见[完整指令、成对升级与Pages合并步骤](../docs/EXPRESSION_GALLERY.md)。固件/PC均需0.5.0；先运行`start_control.cmd COM3 --silent-replies`测试表情，再去掉静音参数听“好的”。新增实体效果待验收；下方版本段落保留历史记录。

# Desktop-NOMI 本地语音指令固件

> 新增0.4.3 [板载固定“好的”回应](../docs/SPOKEN_OKAY.md)：ES8311/GPIO9、短PCM、播放保护，不接动态TTS/云端。固件与PC成对更新，原ASR模型不变，实体扬声器和回灌抑制待验证。

> 0.4.2修复见[当前语音控制说明](../docs/PC_VOICE_CONTROL.md)：固件与PC成对升级，使用编号/校验回执和设备端20秒聆听会话，取消电脑每2秒刷新；原模型/依赖不变，实体修复待复测。以下0.4.0/0.4.1描述保留历史范围。

> 当前新增0.4.0 [USB中文转录调试版](../docs/USB_CHINESE_TRANSCRIPTION.md)：用户已同意Windows本地ASR；板载麦克风经USB传音频，电脑显示实际中文，暂不执行语音表情动作。旧0.3.0有限指令版本保留，不能视为任意中文转录或已通过激活验收。

当前新增 **0.3.0 commands**：在ESP32-S3上识别“小米同学”激活和有限中文表情指令，不依赖电脑、网络或云服务。实现是MultiNet7连续词表匹配，不是专用WakeNet模型，真实效果待实机验收。

完整操作/自定义名称/Windows烧录/正负样本验收见 [HARDWARE_VOICE](../docs/HARDWARE_VOICE.md)。

```sh
python scripts/build.py --profile commands --package
```

说“小米同学”看到Listening后，再说“开心一点”“难过一点”“眨一下眼”等；“休息一下”或20秒超时回待机。不做自由对话/LLM/TTS，不保存录音、不上传音频。原H2两种诊断profile保留如下。

## H2 诊断版本（历史方案）

目标仅为 **Waveshare ESP32-S3-Touch-LCD-1.85B，360×360**。保留H1八种表情与串口demo，加入本地麦克风/AFE模块。
**准确“小米同学”模型尚不可用**；不要把“小爱同学”技术基准当作目标词已经完成。

| 构建 | 行为 |
| --- | --- |
| `audio`（默认） | 开机本地采集、AFE/NS/VAD；没有唤醒模型，不会输出唤醒成功 |
| `benchmark` | 仅“小爱同学” WakeNet9 基准；检测后保持Listening并输出带模型身份的事件 |

不接ASR/LLM/TTS、网络上传、触摸、记忆或舵机。主显示任务不做音频初始化/推理；FaceModel未改。首次开机即本地采集，可发 `wake off` 停止，不保存录音。

完整的**准确硬件、模型调查/费用/限制、Windows预编译ZIP烧录与验收**见 [HARDWARE_H2](../docs/HARDWARE_H2.md)。原厂备份/恢复仍见 [HARDWARE_H1](../docs/HARDWARE_H1.md)，不要覆盖用户已有备份、不要整片擦除。

## 源码构建

使用 **ESP-IDF v5.5.4** 终端、Python 3、Git。在firmware目录执行：

```sh
python scripts/build.py --profile audio --package
```

主动选择“小爱同学”技术基准：

```sh
python scripts/build.py --profile benchmark --package
```

脚本自动prepare固定依赖、build/size、校验模型数量/词身份/准确写入偏移/ELF无网络与ASR/TTS运行入口，最后生成 `dist/desktop-nomi-h2-audio.zip` 或 `dist/desktop-nomi-h2-benchmark.zip`。**没有烧录步骤。**
独立的build-audio/build-benchmark和sdkconfig.*.local避免继承H1配置；不要直接使用原H1 build目录烧H2。GitHub Actions对两种profile分别构建，并上传可下载ZIP。

依赖版本、提交与基准模型SHA256锁在 [dependencies.lock.json](dependencies.lock.json)；prepare只从官方GitHub仓库获取并校验，拒绝错误提交或有本地修改的依赖。组件管理器保持关闭，不依赖注册表。ESP-SR manifest为2.0.1（tag为v2.0.0），ESP-DSP1.4.14、esp_codec_dev1.6.2、LVGL9.5.0；没有引入整个ESP-ADF运行框架。

ZIP含app/bootloader/分区表/**model镜像**/准确flash_args、ELF/map、sdkconfig、manifest及许可证。`desktop_nomi_h2.bin`仅app，不能单独刷0x0；按H2说明刷完整生成文件集，不能遗漏model。

## 串口

115200，ASCII命令一行回车：

| 命令 | 行为 |
| --- | --- |
| `idle` / `blink` / `happy` / `sad` / `curious` / `thinking` / `listening` / `speaking` | 原H1预览、TTL/回退/自然眨眼保留；显式表情指令清除唤醒后的Listening保持 |
| `demo` | 原八表情各3秒，两轮可重复；期间不被唤醒切屏 |
| `status` | 表情与内存 + 音频/AFE/模型、栈、CPU累计runtime、最大帧间隔 |
| `wake status` | 只看本地音频诊断，不中断表情 |
| `wake off` | 异步停止采集，等待MIC_DISABLED；使旧唤醒事件失效 |
| `wake on` / `wake reinit` | 异步重新初始化、恢复采集并重新布防；不会切换profile |

未知/过长命令回退idle，部分输入不阻塞画面。phase/emotion数值含义与H1相同。唤醒事件每个会话只发一次，Listening保持到显式退出；要再次检测请wake on。demo中的事件被忽略，demo后如已触发需wake on再布防。无“串口伪造唤醒成功”命令。

## 自动化测试与实机边界

```sh
python scripts/prepare.py
cmake -S tests -B build-native -DNOMI_RENDER_TESTS=ON
cmake --build build-native
ctest --test-dir build-native --output-on-failure
python -m unittest discover -s tests -p 'test_*.py' -v
```

实机30分钟观察辅助工具（先关闭其他串口终端）：

```sh
python scripts/soak.py --port COM3 --minutes 30
```

原生状态/实际LVGL渲染/PCM和唤醒隔离测试、构建与打包审计可以在云端执行；它们不等于真实麦克风、AFE库运行、唤醒准确率或稳定性通过。分层实机验收、CPU/栈/内存读法与当前结果见HARDWARE_H2和 [HANDOFF](../docs/HANDOFF.md)。

H1用户实测已通过Windows备份/编译/烧录、眨眼及八表情两轮demo；H2新音频功能尚待用户实测。本阶段不声称“小米同学”已经能唤醒。
