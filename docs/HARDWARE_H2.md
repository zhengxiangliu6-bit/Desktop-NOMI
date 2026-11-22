> **0.6.3输入诊断**：修正AFE VAD缓存补回，新增板上官方PCM自检、原始/AFE双路串口音频和推理/堆统计。电脑只接收、不参与识别；默认不录音。新版本尚待实机验证，见[调试步骤](LOCAL_VOICE_TRACE.md)。

> **当前0.6.0：ESP32本地有限指令→14表情→固定回复**，无需PC识别/网络。新增WAV导入工具和重建步骤，沿用占位音频待用户提供替代；实体识别/播放仍待验收。见[离线闭环与音频替换指南](OFFLINE_COMMAND_REPLY.md)。以下版本保留历史记录。

> **0.5.1固定回应音色更新**：免费MeloTTS仅在开发时离线生成短PCM，设备不运行神经TTS；兼容PC0.5.0，不改指令/别名/20秒会话。新版实体听测待验。脱离电脑及AI决策见[方案对比](VOICE_NEXT_PLAN.md)。

> **当前0.5.0：14种明显不同的圆屏表情、网页图库、可静音测试的固定回应。** 见[完整指令、成对升级与Pages合并步骤](EXPRESSION_GALLERY.md)。固件/PC均需0.5.0；先运行`start_control.cmd COM3 --silent-replies`测试表情，再去掉静音参数听“好的”。新增实体效果待验收；下方版本段落保留历史记录。

# H2：本地音频与唤醒词接入

> 当前新增0.4.0 [USB中文转录调试版](USB_CHINESE_TRANSCRIPTION.md)：用户已同意Windows本地ASR；板载麦克风经USB传音频，电脑显示实际中文，暂不执行语音表情动作。旧0.3.0有限指令版本保留，不能视为任意中文转录或已通过激活验收。

> 后续需求已扩展为独立ESP32语音指令，见 [HARDWARE_VOICE](HARDWARE_VOICE.md)。本文的“无ASR/模型未获得”描述针对原audio/benchmark阶段；commands使用通用MultiNet7词表匹配“小米同学”，不是专用WakeNet。0.3.0模型分区扩大为4MB。

**「小米同学」专用模型不可用，当前不能宣称已实现这个唤醒词。**
本阶段交付音频/AFE 接入及一个明确标记的「小爱同学」基准选项，不接 ASR、LLM、TTS、触摸、记忆、舵机或网络。
音频与新唤醒功能尚未连接实体板验证；H1 表情的用户实机反馈见 [H1 文档](HARDWARE_H1.md)。

## 两种构建，不能混淆

| Profile / ZIP | 本地运行内容 | 真正的唤醒词 |
| --- | --- | --- |
| `audio` / `desktop-nomi-h2-audio.zip`（默认） | 开机采集双麦，MIC1 进入 AFE + WebRTC NS/VAD，输出电平和计数 | **无模型**；不会产生唤醒成功事件 |
| `benchmark` / `desktop-nomi-h2-benchmark.zip` | 相同音频链 + 官方 `wn9_xiaoaitongxue` / WakeNet9 | **小爱同学，仅技术基准，不是小米同学** |

默认包不装入另一个词冒充目标；benchmark 需用户明确选择，启动和每次检测均打印模型身份与 benchmark_only 标记。
音频只在 RAM/PSRAM 与 AFE 有界环形缓冲流转，不保存录音、不输出 PCM、不初始化 Wi-Fi/BLE/HTTP。
设备开机即在本地采集，`wake off` 可停止采集；这不是物理断麦开关，也没有声称关闭全部模拟电源。

## 调查证据与准确硬件

官方资料入口：[Waveshare 文档](https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.85B)。云端访问该域名被网络代理拒绝，本次未声称已加载网页；可核验内容来自官方 GitHub 源码及 Rev1.1 原理图：
[固定官方提交](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-1.85B/tree/5a98b8da1948340c07032a408ac0d93c47ca558f)。

- 读过 `examples/esp-idf/06_mic_test/main/MicTest.cpp`、同示例 BSP 显示/音频实现、`bsp_extra/src/bsp_board_extra.cpp` 和原理图。
- 两个模拟贴片麦克风进入 **ES7210** ADC，原理图 U7/U11 仅标注“贴片麦克风 1.6V~3.6V”，没有公布可确认的采购型号，不能推定为某款 I²S 数字麦。
- **ES8311** 是 DAC/输出侧 Codec；本版保留官方共享音频时钟/初始化链，DAC 静音，GPIO9 功放始终关闭，TX 不提交语音或播放数据。
- ES7210 I²C 7-bit 地址 **0x40**（驱动 8-bit 0x80），ES8311 **0x18**（驱动 0x30）；I²C1 SDA=GPIO11、SCL=GPIO10，显式配置 400 kHz。
- **I²S1 主机 Philips stereo PCM16**：MCLK=GPIO2、BCLK=48、LRCLK=38、MCU DOUT=47、DIN=39；PA=9。全部来自 **1.85B** 官方 BSP，没有使用其他开发板引脚。
- 官方 Mic Test 为 **16 kHz、16-bit、两路 MIC1/MIC2**，slot0/slot1；本版同样采集这两路，提取 MIC1 给 AFE 的 `M` 格式，MIC2 只统计电平。不把 MIC2 当回声参考，也不接官方四槽 MIC3 回放参考路径。
- H1 只有显示驱动，无音频组件。H2 通过独立 `nomi_audio` 和 `WakeWordController` 加入；FaceModel 源码未改，八种表情保留。

## 框架、模型与资源选择

版本/完整提交/基准模型三个文件的 SHA256 见 [dependencies.lock.json](../firmware/dependencies.lock.json)，许可与改写见 [NOTICE](../firmware/components/nomi_audio/NOTICE.md)。

| 组件 | 锁定选择 |
| --- | --- |
| ESP-IDF | **5.5.4**，与已完成的 Windows H1 相同 |
| LVGL | **9.5.0**，保持 H1 提交 |
| ESP-SR | manifest **2.0.1** / upstream tag **v2.0.0**，提交 `1c0503e7e2dc5e1ecb2fd3da0a5d7e51e3574842` |
| ESP-DSP | **1.4.14**，满足此 SR 的 <=1.5.0 约束 |
| esp_codec_dev | **1.6.2** / ESP-ADF 固定提交，仅取此组件，未引入 ESP-ADF 框架；官方微雪示例是 1.5.5，此差异明确记录 |
| AFE | SR LOW_COST / MORE_PSRAM，16 kHz signed PCM16 单麦 `M`，AEC/SE/AGC 关闭、WebRTC NS/VAD 开启 |
| WakeNet | benchmark 仅 **WakeNet9 `wn9_xiaoaitongxue`**，`_MODEL_INFO_` 标识“WakeNet9_v1h24_小爱同学_3_0.620_0.6276:AFE” |
| Flash | 16 MB；bootloader 0x0、表 0x8000、app 0x10000/4 MB、model 0x410000/2 MB；准确参数由构建生成 |
| PSRAM | 板载 8 MB 八线 80 MHz，AFE 优先 PSRAM；PCM 缓冲最多 6144 字节，显示双 DMA 缓冲保持 23,040 字节 |
| 任务 | 主显示 CPU1；capture CPU0 优先级4/8192字节栈；fetch CPU1 优先级3/8192字节栈；AFE内部任务偏好CPU0/优先级3 |

调研 master 是 ESP-SR **2.6.2**（`bb552f1a559396a17681299cb3e199a0f1a4520a`），但集成采用上述更小的 WakeNet9 依赖组合；不是声称使用最新 WakeNet10。
所选 SR manifest 声明 IDF >=5.0，H2 实际目标构建验证 IDF 5.5.4；二进制库运行、音频格式与时序仍须实机验证。

官方 [benchmark 源文件](https://github.com/espressif/esp-sr/blob/1c0503e7e2dc5e1ecb2fd3da0a5d7e51e3574842/docs/en/benchmark/README.rst) 给出 S3 单个 WakeNet9 的参考量级约 16 KB 内部 RAM / 324 KB PSRAM / 3 ms 每32 ms帧；带 AEC/NS 等完整 AFE 的 MR LOW_COST 示例约72.3 KB内部 / 732.7 KB PSRAM。**这些是官方其他模型/板/配置的基准，不能代替本板实测。**
H1 用户日志可用内部 RAM 324,575 字节、PSRAM 8,386,308 字节；它只说明加入音频前的余量。H2 静态大小见 HANDOFF，动态量用 `status` 与30分钟测试确认。

## 「小米同学」模型调查结论

核查了最新公开 README、Kconfig、[完整模型清单](https://github.com/espressif/esp-sr/blob/bb552f1a559396a17681299cb3e199a0f1a4520a/wakeword_list.md) 和模型目录：有「小爱同学」「小明同学」，**未找到「小米同学」**。本次没有获得或训练准确模型；偶然对相近词误触发也不能算支持。

- WakeNet 是本地唤醒判定；AFE 做前处理，VAD 只判断语音/非语音。VAD 电平变化或 speech 状态不是识别出了目标词，也不是 ASR。
- 官方 [定制流程](https://github.com/espressif/esp-sr/blob/bb552f1a559396a17681299cb3e199a0f1a4520a/docs/en/wake_word_engine/ESP_Wake_Words_Customization.rst)：支持纯 TTS、官方众包人声+TTS、客户语料三条路径；客户语料方案要求至少20,000条合格语料，格式16kHz/16bit/单声道 WAV；语料就绪后人声方案通常还需2–3周训练优化。
- 费用：官方写明**一次性定制费**，不按设备数或使用年限另收许可费，但不公开固定金额，具体须询价。不能把旧报价或估计值当当前价格。本次没有询价发邮件、提交语料、购买或接受协议。
- 免费/低成本路径：[官方 issue #88](https://github.com/espressif/esp-sr/issues/88) 提供社区 TTS 词征集；自2024-08起要求提供实际项目链接/说明或超过5个赞，是否接受、公开发布时间和效果没有承诺；提交视为同意其单独协议，故本次没有替用户发帖。项目提到 TTS Pipeline V3 多语言训练，这是厂商训练服务/发布路径，**不等于仓库提供可直接自己训练 WakeNet 的完整脚本、权重和语料**。
- 输出/部署：需取得与选择的 ESP-SR/WakeNet 运行库兼容的正式模型文件，校验词与版本后由打包脚本生成模型分区镜像。不能改 `_MODEL_INFO_` 的词就让模型学会新词，不能直接把任意 `.tflite` 塞进 WakeNet；若厂商交付 WakeNet10 模型，需要另评估并升级运行依赖。
- 可研究的自训替代：[microWakeWord](https://github.com/kahrendt/microWakeWord) 有合成样本+特征提取+训练 notebook，输出适用于 TFLite Micro 的流式量化模型，适合 MCU 研究。但其 README 明确训练高质量模型困难、基础 notebook 结果多半不可直接使用；中文“小米同学”需要合规中文 TTS/人声、负样本和本板调参，没有现成效果保证。软件开源不代表语料/TTS/GPU 零费用，也不是 WakeNet 模型格式，接入会是独立 Adapter/运行时工作。
- [openWakeWord](https://github.com/dscripka/openWakeWord) 官方 README 仍写主要只支持英语，且不推荐直接在 ESP32-S3 上运行（推荐 microWakeWord）；预训练模型还有非商业等许可限制。因此它不是本阶段可直接替换的中文 S3 方案。

本阶段不在设备上接入 TTS；以上 TTS 仅是训练语料方案调查，没有调用任何语音合成服务。

## 任务、状态与异常

`WakeWordController` 的 capture worker 拥有音频初始化/采集/AFE feed/销毁，fetch worker 持续取 AFE 结果；主任务独占 FaceModel/LVGL。
请求队列长度1（最后一次启停请求优先），唤醒事件队列长度4；每次 on/off/reinit 更新 epoch，旧事件不能覆盖新状态。
初始化不在显示任务运行。关闭/重初始化先停采集，再等待 fetch 退出本轮才销毁 AFE/模型；停机超时保留仍在用的资源并报告需重启，防止释放后继续使用。

- I²S DMA 6×240 stereo帧；warmup约200ms。逐段收齐整块，检查4字节帧对齐，MIC1 转 mono 后按 AFE 查询的 chunk 喂入。
- AFE ringbuffer设为50个库内部单位（固定ESP-SR 2.0.1单麦每单位1024字节）；VAD speech/delay各128ms，历史预留8192字节。旧版5单位不足，用户实机出现feed满/fetch空；0.2.1扩大有界缓存并将feed返回0视为故障，实机修复待复测。数据/队列满、格式错误、I²S连续超时、fetch停滞均记录故障并停止本轮，**不把断续/过期音频当正常语料，也不伪造唤醒**。启动warmup可能发生的溢出单独计数，稳定运行新增溢出视为异常。
- 每个运行会话仅发送一次实际唤醒事件。benchmark 日志为 `WAKE_WORD_DETECTED model=wn9_xiaoaitongxue phrase=小爱同学 benchmark_only=1 target_xiaomi_available=0`。
- 正常唤醒后主任务保持 Listening，等待后续语音系统；`idle`/其他表情命令退出保持，`wake on` 或 `wake reinit` 建立新会话并重新布防。
- **demo优先**：不被唤醒打断，demo中的检测事件不切屏且记录忽略；本轮检测若已锁存，demo后用 `wake on` 再布防。`status` 不打断 demo/Listening。音频故障不会导致原有表情不可用。

## Windows：最简单的构建产物烧录方式

1. 保留已校验的原厂双备份，不移动/覆盖 `D:\NOMI-backup`。如果还想保留已验证 H1 的完整状态，可按 H1 同样方法另存新的文件名做完整备份。不要把 H1 的备份覆盖到原厂备份上。
2. 打开 [固件 Actions](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/workflows/firmware.yml)，选择 **feat/h2-local-wakeword** 分支的成功运行；下载 `desktop-nomi-h2-audio` 或明确选择的 `desktop-nomi-h2-benchmark` artifact。GitHub 下载产物可能需要登录。
3. 解压 artifact；若里面还有同名ZIP，再解压一次。进入同时包含 `flash_args`、`manifest.json`、`READ-ME-FIRST.txt` 的目录。核对 manifest 的板型、profile、target_model_available=false、活动模型，以及每个文件 SHA256。benchmark 只能用“小爱同学”测试。
4. 关闭占用串口的程序，确认实际COM号（下面沿用之前的COM3）。在已安装的 **ESP-IDF 5.5.4 终端**运行：

   ```bat
   cd /d D:\NOMI-H2-audio
   python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
   python -m serial.tools.miniterm COM3 115200 --eol CRLF
   ```

   `D:\NOMI-H2-audio` 替换为你实际解压目录。按生成的 response file 写 app/bootloader/表/**模型分区**；**不能只刷 app，否则可能读取旧模型。不要执行 erase_flash。** 此操作会改变固件分区布局，不能保证 H1/原厂旧分区内容继续可用；保留备份用于恢复。
5. 检查 `I2S_FORMAT_VERIFIED`、`AFE_READY`、profile、16kHz PCM信息；audio版没有唤醒成功是预期行为。benchmark版说“小爱同学”，观察事件与Listening；不要说它已经识别“小米同学”。串口Ctrl+]退出。

可用串口命令：

| 命令 | 行为 |
| --- | --- |
| `status` | 原有表情/内存 + 音频状态、计数、栈与任务runtime、最大帧间隔 |
| `wake status` | 音频/模型与任务统计，不打断表情 |
| `wake off` | 异步关闭采集/AFE，立即作废旧事件，离开保持聆听 |
| `wake on` / `wake reinit` | 异步重新初始化并布防；两种profile不互相切换 |
| `idle` / 其他H1表情 / `demo` | 原有功能保持；清除Listening保持，**不等于关麦** |

默认开机麦克风采集；日志确认 `MIC_DISABLED` 后才表示关闭已完成。`wake on` 不会把audio版变成benchmark版，更不会创建“小米同学”模型。

## 源码构建和测试

在ESP-IDF终端（已有目录先保存本地修改再切换分支）：

```bat
cd /d D:\Desktop-NOMI
git fetch origin feat/h2-local-wakeword
git switch feat/h2-local-wakeword
cd firmware
python scripts\build.py --profile audio --package
```

技术基准版需主动选择：

```bat
python scripts\build.py --profile benchmark --package
```

脚本下载固定提交并核验模型SHA256、分别使用 build-audio/build-benchmark 与独立 sdkconfig，不覆盖已有H1 sdkconfig；执行build/size/模型身份与ELF检查后输出dist ZIP。脚本**没有自动烧录或擦除步骤**。首次下载依赖需要网络与Git，本地 IDF 保持5.5.4。

原生测试（命令行进入firmware）：

```sh
python scripts/prepare.py
cmake -S tests -B build-native -DNOMI_RENDER_TESTS=ON
cmake --build build-native
ctest --test-dir build-native --output-on-failure
python -m unittest discover -s tests -p 'test_*.py' -v
```

原生覆盖H1状态/八种表情实际LVGL渲染、PCM极值/声道/静音/错误格式、唤醒事件的epoch/重复/非基准模型/demo隔离/保持，以及打包前模型/偏移/网络运行入口审计。**这些不能验证真实声音或预编译AFE/WakeNet库的运行效果。**

## 实机验收与四层结果

| 验收层 | 当前证据 | 通过所需实机步骤 |
| --- | --- | --- |
| 音频驱动 | 源码/目标构建验证；实际麦克风待测 | AFE_READY后说话/拍手，MIC1/MIC2 peak_hold/rms变化，静音时rms明显下降；持续blocks/fetched增长，无稳定期overflow/timeouts/削波异常 |
| ESP-SR框架 | AFE调用已集成并编译；运行待测 | 查看真实AFE pipeline，16kHz/mono PCM16 chunk检查通过，连续运行、off/on/reinit后恢复 |
| 其他预训练唤醒词 | 只集成“小爱同学”benchmark；实际识别待测 | 近场正常音量多次说“小爱同学”，逐次wake on重新布防，核对模型身份、事件及Listening保持；同时测背景音/相似词误唤醒 |
| 小米同学专用模型 | **未获得，不可用** | 必须先取得准确兼容模型、独立正/负样本及本板测试；前三项通过也不能勾选这一项 |

基础实机流程：

1. 确认屏幕8表情和demo仍正常，连做两轮；在说话/采集期间发demo，屏幕不被打断。
2. `status`记录初始RAM/PSRAM、MIC电平、blocks/fetched/VAD、overflow/timeouts/drop，Listening前后无反复重启。boot中的失败日志不能当成初始化成功。
3. benchmark说“小爱同学”，检查唯一实际检测事件和Listening保持至少10秒；`idle`可回待机，`wake on`重新布防。分别用“小米同学”“小明同学”和普通背景话音作负样本；相近词偶发触发是误唤醒，需要记录，不是新增支持。
4. `wake off`等待MIC_DISABLED，blocks/fetched应停止；`wake on`重新开始增长。连做10轮off/on/reinit，比较稳定后的可用内存与栈，检查没有持续下降或旧事件回切。
5. 运行30分钟，定期status，并可在另一个未占串口的时段使用：`python scripts/soak.py --port COM3 --minutes 30`（先退出miniterm）。脚本只观察日志和发送status，不录音、不写Flash、不自动宣布验收成功。监控栈剩余至少约1KB（不足需调参）、RAM余量、模型运行、温升、无WDT/花屏/卡死/异常重启。
6. runtime_us为任务累计运行时间，**不是CPU百分比**。soak按两次采样差计算每个任务占单核的比例，包含AFE内部与IDLE任务；双核总体忙碌约为 `100% - (IDLE0% + IDLE1%)/2`。runtime采用32bit计数，脚本处理一次回绕；检测方法、30分钟实测结果仍由操作者记录。
7. 无网络验证：运行ELF入口审计、检查源码未初始化网络；设备不会连接AP，也没有音频上传代码。音频只经本地I²S/PSRAM处理。若未来加入网络，必须重新验证此边界。
8. 不为H2执行原厂恢复或整片擦除；恢复需求另按已验证备份与 [H1 恢复流程](HARDWARE_H1.md)。本次没有执行真实恢复测试。

下一阶段建议：先完成上述音频/基准实测并确定准确唤醒词模型来源，再设计本地有界聆听窗口/结束检测、独立ASR Adapter、取消与错误回退；ASR是后续授权事项，本阶段不提前接入。继续保持唤醒前无音频上传，不直接接LLM/TTS。
