# H2 本地音频与唤醒交接

更新：2026-11-15（Asia/Shanghai）。**目标“小米同学”准确模型未获得，不能宣称目标词唤醒完成。** 本阶段交付本地采集/AFE与单独“小爱同学”技术基准代码、双profile固件ZIP；H2新音频与真实唤醒运行均待用户实机验证。

## 开始调查与基线

- 开始分支 `feat/h1-esp32-face` / `c858ce9`，工作区干净；读取AGENTS、README、ARCHITECTURE、API_CONTRACT、ROADMAP、firmware/H1实现、本交接，检查无子目录AGENTS。`git fetch origin main` 后 main仍为 `e06e8a9`，H1尚未在main。因此从已验证H1提交创建独立 `feat/h2-local-wakeword`，不丢弃H1实现、不修改main。
- 本阶段按用户明确要求：**不创建PR、不合并main**，该要求优先于AGENTS默认PR流程；不自动擦除/刷写、不覆盖用户备份、不购买训练服务、不调用ASR/LLM/TTS。
- 使用现有官方IDF源码 v5.5.4（提交735507283d5b2f9fb363a1901172dbd9e847945d）、Xtensa GCC esp-14.2.0_20260121、Python3.12.14、CMake3.30.5、Ninja1.13.2；保留既有可写工具环境和正常TLS。`idf.py --version` 确认为5.5.4。
- 写代码前已调查官方1.85B固定提交 `5a98b8da1948340c07032a408ac0d93c47ca558f` 的06_mic_test、BSP音频与bsp_extra、原理图；现有H1无音频组件。用户给的docs.waveshare.com域名被云代理拒绝，未声称成功阅读该网页，使用同板官方GitHub源码/原理图核对。

## H1 实机证据补录（来自本会话用户，不是助手连接硬件）

- 用户Windows实际安装ESP-IDF5.5.4，设备识别S3 revision0.2、16MB Flash、8MB PSRAM、USB Serial/JTAG；Secure Boot和Flash Encryption均Disabled。
- 两份完整16MB原厂备份SHA256相同，verify_flash明确`verify OK (digest matched)`；原厂备份保存在用户本机，未上传/写入本仓库。未实际执行原厂恢复。
- 用户Windows编译成功，app538,016字节；刷写bootloader/app/分区表全部Hash verified，复位显示脸/眨眼，demo八种表情连续两轮正常。用户反馈部分表情变化较小，暂不影响验收，不在H2改外观。
- 用户H1 status：内部可用324,575字节、PSRAM可用8,386,308字节；这些是加音频前的余量。30分钟稳定性、重复断电启动、实际恢复仍未获得结果。

## 模型结论与实现决策

- 核查ESP-SR master2.6.2（bb552f1a559396a17681299cb3e199a0f1a4520a）的README、Kconfig、wakeword_list和模型目录：未找到“小米同学”，有“小爱同学”“小明同学”，不能混同。
- 集成锁定ESP-SR manifest2.0.1（上游tag名v2.0.0）、ESP-DSP1.4.14、esp_codec_dev1.6.2、LVGL9.5.0；完整SHA/基准模型文件SHA256见firmware/dependencies.lock.json，许可/版本差异见nomi_audio/NOTICE。采用成熟WakeNet9组合，未增加最新WakeNet10的esp-dl/dl_fft依赖。
- 默认audio profile：本地双麦采集、MIC1->AFE/NS/WebRTC VAD，不加载唤醒模型；benchmark profile：唯一wn9_xiaoaitongxue，“小爱同学”，每次启动/检测和ZIP元数据均明确benchmark与target_model_available=false。
- 本次没有准确目标模型、没有训练或购买。官方支持TTS样本定制：一次性费用需询价、无公开固定金额；issue#88社区征集存在项目/点赞门槛、单独提交协议及无交付时限，未代用户提交。自训microWakeWord/中文TTS语料可后续研究，但格式/运行时/语料与算力成本另评估，不能直接替换WakeNet。详细证据/费用/格式/替代限制见HARDWARE_H2。

## 硬件、并发与内存

- 同板ES7210双模拟麦、ES8311输出Codec，麦克风原理图只给工作电压描述，未公开可确认的采购型号。I²C1 SDA11/SCL10、ES7210 0x40、ES8311 0x18；I²S1 MCLK2/BCLK48/LRCLK38/DOUT47/DIN39，PA9强制关闭。显式400kHz I²C，16kHz signed PCM16 stereo slot0/1。
- 独立nomi_audio改写官方初始化，保留静音DAC时钟路径，两个麦都采集但仅MIC1送AFE单麦M格式，MIC2仅电平诊断。不伪造回放参考，不启用AEC/SE/AGC，不录音/回放、不写PCM/上传。
- WakeWordController：capture CPU0/prio4/8192字节栈、fetch CPU1/prio3/8192字节栈；主显示CPU1。AFE MORE_PSRAM、LOW_COST、5帧ringbuffer、内部任务偏好CPU0/prio3，raw stereo+mono最大6144字节；H1显示DMA仍23,040字节。
- 请求队列1、事件队列4、epoch作废迟到事件；off/on/reinit异步，不在渲染任务做Codec/模型初始化。检查PCM对齐/采样契约、溢出、读超时、fetch停滞、内存分配；停机等待fetch本轮退出再destroy，超时保留仍在用资源报告需重启。第三方预编译库若自身卡死仍可能需硬件重启，不能声称云端验证了这些故障路径。
- 正常检测后保持Listening；串口idle/其他表情可退出，wake on/reinit重新布防。demo不被检测事件打断，demo期间若检测已锁存需之后重新布防。FaceModel/FaceView/显示驱动源码未改。
- 状态有MIC peak_hold/rms/削波、blocks/fetched/VAD、超时/溢出/drop、栈余量、任务累计runtime（包含AFE/idle任务）和UI最大帧间隔。soak.py按差值估计单核占用；没有伪造CPU或30分钟数据。

## 已执行验证与真实结果

- `python firmware/scripts/prepare.py`：四个官方依赖提交与模型SHA256核验通过；不依赖组件注册表，第三方checkout保持干净。
- `python firmware/scripts/build.py --profile audio --package`：IDF build/size、模型数0、偏移/ELF运行入口审计通过，app **1,044,320字节**，模型镜像 **4字节**。静态DIRAM约104,735字节。
- `python firmware/scripts/build.py --profile benchmark --package`：同样通过，app **1,047,552字节**，模型 **291,150字节**（唯一小爱同学）；静态DIRAM约104,947字节。app4MB/model2MB分区，均在16MB内；运行堆/CPU/栈还须实机测。
- 音频接口在打开Codec后查询实际I²S驱动配置并核对16kHz/16bit/stereo，打印I2S_FORMAT_VERIFIED与时钟；关闭前查询is_enabled，避免Codec已关闭时重复disable产生误导日志。修改后两profile重新build/size/打包审计通过。
- ELF未发现esp_wifi_init、esp_http_client_init、esp_tls_conn_new、esp_mn_handle_from_name、esp_tts_create运行入口；源码没有网络初始化/上传、ASR/LLM/TTS调用。上游SR CMake声明TTS/MultiNet静态库不代表本固件启用了它们。
- `cmake -S firmware/tests -B /tmp/nomi-h2-tests -G Ninja -DNOMI_RENDER_TESTS=ON`、build、ctest：**3/3通过**（H1核心状态、八表情真实LVGL离屏渲染、wake/PCM策略）。覆盖旧epoch、重复/未验证模型、demo隔离、Listening保持、极值/静音/声道/对齐。
- `python -m unittest discover -s firmware/tests -p 'test_*.py' -v`：**4/4通过**，覆盖错误模型/数量/profile/芯片/偏移/网络和ASR/TTS入口拒绝。它只测试打包审计，不是假音频冒充模型成功。
- wake_logic_test C++17 `-Wall -Wextra -Werror -fsanitize=address,undefined`：通过。Python工具py_compile、actionlint1.7.7、Markdown链接/围栏、git diff --check：通过。ZIP逐文件SHA256与manifest/profile核对通过。
- 调试中先修正SR在禁用组件管理器时需显式REQUIRES espressif__esp-dsp、Codec GPIO释放函数名；正式构建已通过。一次命令工作目录错误只影响云端临时路径，已改脚本使用绝对隔离build目录并移除误生成目录。审阅固定SR源码发现get_wake_words返回malloc字符串，成功/失败路径都加了free，避免每次reinit泄漏；随后重新构建两profile通过。
- 前后端/API Key/Pages工作流无变更；不受影响的Web/后端测试未重复执行。没有连接用户COM3、执行flash/erase/付费请求或实机30分钟测试。

## 产物、烧录与剩余验收

- 本地ZIP：firmware/dist/desktop-nomi-h2-audio.zip、desktop-nomi-h2-benchmark.zip，未提交二进制；包含准确flash_args、app/bootloader/表/model、ELF/map、sdkconfig、源提交/模型身份/哈希manifest及第三方许可。
- 独立firmware.yml在本H2分支push触发，不需要PR；两profile矩阵构建、打包并upload-artifact。远端运行及下载入口在推送后补录，不将本地编译说成远端已成功。
- Windows优先下载对应成功artifact解压，在flash_args所在目录用现有ESP-IDF终端 `python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"`；先核对当前COM与板型/profile/哈希，**不能遗漏model、不能先erase_flash、不能覆盖原厂备份**。详细步骤见HARDWARE_H2。
- 分层结论：音频驱动=集成/编译通过、实际待测；ESP-SR框架=API集成/编译通过、运行待测；小爱基准=编译/身份核验通过、真实识别待测；小米同学=模型不可用、未完成。前三项不能替代第四项。
- 用户需实测麦克风电平/格式/Codec时序、AFE初始化与持续运行、基准正负样本、Listening保持、demo、10轮off/on/reinit、30分钟RAM/PSRAM/CPU/栈/复位情况。恢复与硬件长稳仍未验证。
- 后续先完成音频/基准验收与准确唤醒模型来源决策，再单独授权ASR Adapter、有界聆听窗口/VAD结束、取消/错误恢复；本阶段不预先接ASR/LLM/TTS。

## 实际修改文件（相对H1 c858ce9）

```text
.github/workflows/firmware.yml
README.md
docs/ARCHITECTURE.md
docs/HANDOFF.md
docs/HARDWARE_H1.md
docs/HARDWARE_H2.md
docs/ROADMAP.md
firmware/.gitignore
firmware/CMakeLists.txt
firmware/README.md
firmware/components/nomi_audio/CMakeLists.txt
firmware/components/nomi_audio/NOTICE.md
firmware/components/nomi_audio/audio_input.cpp
firmware/components/nomi_audio/include/audio_input.h
firmware/dependencies.lock.json
firmware/main/CMakeLists.txt
firmware/main/Kconfig.projbuild
firmware/main/main.cpp
firmware/main/wake/wake_logic.h
firmware/main/wake/wake_word_controller.cpp
firmware/main/wake/wake_word_controller.h
firmware/partitions.csv
firmware/scripts/build.py
firmware/scripts/prepare.py
firmware/scripts/soak.py
firmware/sdkconfig.benchmark
firmware/sdkconfig.defaults
firmware/tests/CMakeLists.txt
firmware/tests/test_build_tools.py
firmware/tests/wake_logic_test.cpp
```

## 提交与推送

- 实现提交 `3975363`，已成功推送 `feat/h2-local-wakeword`。
- 首轮云端运行43619456065：原生检查成功，两个固件都完成目标编译/size/模型与ELF审计，但打包读取Git元数据遇到Actions容器UID归属检查（dubious ownership），未上传产物。修复为每次Git查询只信任当前仓库的准确绝对路径，不改全局配置、不使用通配信任。I²S格式/关闭修正提交d335bf7也已推送，最终产物以修复后的最新成功运行和manifest的source_commit为准。
- 使用全新临时目录实际运行prepare的SR/Codec sparse fetch/checkout与模型哈希检查：通过；不是仅复用已安装依赖。
- 按用户要求未创建PR、未合并main，原厂备份不在本工作区。后续远端最终结果另行补录。

---

# H1 硬件固件交接

更新：2026-11-13（Asia/Shanghai）。当前新增交付：**独立 ESP32-S3 圆屏表情固件 H1**。实体硬件、Windows 驱动/烧录/恢复未验证；现有阶段 2B 和 Pages Mock 保留，下方历史交接继续有效。

## 基线与调查

- 工作区起始干净，阅读 AGENTS、README、ARCHITECTURE、API_CONTRACT、ROADMAP、HANDOFF 及 Expression Adapter。`git fetch origin main` 后从最新 `e06e8a9` 创建 `feat/h1-esp32-face`，未修改 main。
- 官方仓库固定提交 `5a98b8da1948340c07032a408ac0d93c47ca558f`，阅读 Rev1.1 原理图、README、ESP-IDF LVGL 示例、BSP 头文件/显示实现、Arduino 示例驱动及官方恢复指南。
- 确认 ESP32-S3R8 / 16 MB Flash / 8 MB 八线 PSRAM；ST77916 360×360 QSPI；所有引脚来自该板，未借用其他板配置。官方框架 IDF 5.5.4 / LVGL 9.5.0。细节见 [HARDWARE_H1](HARDWARE_H1.md)。
- 下载并核对官方合并镜像 20261109，10,514,658 字节，SHA256 `10dbcd2655fe44249840ff2b8879ff11152a7d73e1d6a3ebd8311c1f8e2b3b05`；esptool 4.11.0 image_info 识别 ESP32-S3，bootloader checksum/hash 有效。镜像未加入本仓库。
- 官方恢复方式为合并镜像写 0x0（完整重置时先擦除）；自己整片备份则读取/验证 0x0 起 16 MB 后原址写回。两种恢复目的不同，文档已区分，未对设备执行。原理图 Key1 为电源、Key2 为 BOOT，不假设独立 RESET 按钮。

## 设计与范围

- 新增独立 `firmware/` ESP-IDF 5.5.4 工程。依赖仅 LVGL 9.5.0 固定提交 `85aa60d18b3d5e5588d7b247abf90198f07c8a63`，prepare.py 获取/核验，下载目录忽略。不依赖组件注册表、不打包 Web 运行时。
- 显示层提取该板官方初始化表，保留两版面板 ID 选择、GPIO、80 MHz QSPI、RGB565 和首帧后背光；使用官方仓库随附的 Espressif ST77916 C 驱动，不将其冒充注册表 2.0.1。驱动逐字节核对，初始化表清理行尾空白后与上游核对一致。许可/修改见 [NOTICE](../firmware/components/nomi_panel/NOTICE.md)。
- LVGL 固定图元绘制奶油色脸、眼睛、嘴、腮红/活动提示。idle/blink/happy/sad/curious/thinking/listening/speaking 均实现，安全半径 160；没有图片帧、Aora SVG/源码/素材。两个内部 DMA 条带缓冲总计 23,040 字节。
- FaceModel 为独立 C++17 状态机：情绪/阶段正交、5 秒 TTL（内部可设 1..30000 ms）、工作态优先但不延长情绪、180 ms 插值、2.5–6 秒自然眨眼。眨眼覆盖后恢复原状态；非法输入回退 idle；单调 64 bit 时钟。
- 主任务单独拥有状态机与 LVGL，20 ms 更新几何，FreeRTOS 5 ms yield；DMA 用信号量等待且超时 fail-fast，面板初始化保留必要协议延时。USB Serial/JTAG 有界非阻塞读取本地命令，支持 demo/status/idle；不实现远程设备协议。
- 未初始化触摸、音频、传感器、SD、Wi-Fi，也未实现真实 AI、语音、记忆、舵机或 Device Adapter。listening/speaking 为无声动画。
- Windows 先检查准确板型与安全状态、两份 16 MB 备份/哈希/verify_flash、下载校验官方镜像，再用 idf.py flash；不是将 app bin 写到 0x0。完整步骤与验收表见 HARDWARE_H1。

## 验证记录

- `python firmware/scripts/prepare.py`：LVGL 提交核验通过。
- `g++ -std=c++17 -Wall -Wextra -Werror firmware/tests/face_model_test.cpp firmware/main/face_model.cpp -I firmware/main -o /tmp/nomi-face-model-test` 及执行：通过。
- `cmake -S firmware/tests -B /tmp/nomi-render-tests -G Ninja -DNOMI_RENDER_TESTS=ON`、`cmake --build /tmp/nomi-render-tests -j 6`、`ctest --test-dir /tmp/nomi-render-tests --output-on-failure`：**2/2 通过**。一项覆盖核心状态/TTL/插值/非法值/长运行/跨 32 bit 毫秒；一项链接真实 LVGL 渲染八种表情，检查图像非空、连续表情不同、所有前景像素在半径 160 安全圆内，并输出八张 PPM。已查看合成预览；这是离屏渲染，不模拟显示硬件。
- 初次原生构建缺少 cmake，使用临时 Python 环境安装构建工具；首次 renderer 编译发现 C++ 枚举位或需显式转换，已修正后重建通过。最初插值测试误复用非初始状态，改用新模型后通过，没有更改动画状态语义规避测试。
- 官方表/驱动来源核对、Markdown 本地链接检查：通过。
- 官方 IDF v5.5.4 源码提交 `735507283d5b2f9fb363a1901172dbd9e847945d`（子模块完整且干净），官方 tools.json 校验安装 Xtensa GCC `esp-14.2.0_20260121`。Linux Python 3.12.14 / CMake 3.30.5 / Ninja 1.13.2 / esptool 4.11.0。通用 Docker 镜像下载量大，取消下载，改用上述原生工具链构建；没有宣称在容器内运行成功。
- 云端 Python 按 IDF requirements.core.txt 安装，`idf_tools.py check-python-dependencies` 通过；设置 IDF_PYTHON_CHECK_CONSTRAINTS=no，未使用另行下载的供应商 constraints 文件。没有关闭 TLS 或绕过网络策略。用户 Windows 仍按官方 v5.5.4 安装器配置。
- ESP32-S3 `idf.py build`：**成功**，生成 app/bootloader/partition table/ELF/map/flash_args；最终 app bin **538,016 字节**，分区大小 0x177000（约 65% 余量）。`idf.py size` 成功，静态 DIRAM 约 80,423 字节；动态缓冲/实际 PSRAM 与总运行内存须实机日志确认。esptool image_info 检查 app 为 ESP32-S3、checksum/hash 有效。没有运行 flash/erase/monitor 或连接实体设备。
- 首次 IDF 编译发现 Xtensa uint32_t 与主机 unsigned int 类型不同，std::clamp 推导失败；改为显式 std::clamp<uint32_t> 后目标构建成功。最终变更后重新执行目标 build/size、原生 2/2 测试及 AddressSanitizer/UndefinedBehaviorSanitizer 检查，全部通过。初次命令误将 -j 传给 idf.py，未开始编译，随后改用实际支持的 idf.py build。
- IDF 首次配置存在上游 Kconfig 无 0x 前缀的弃用 NOTE，以及提示检测到 LVGL manifest 但组件管理器已禁用；这是固定 GitHub 依赖的预期行为。最终增量编译无 warning/error，未屏蔽编译诊断。
- actionlint 1.7.7 检查新增 firmware.yml：通过。CI 容器固定官方 v5.5.4 amd64 manifest digest；远端工作流尚未在交付记录时确认执行。
- 官方表/驱动来源核对、本次 Markdown 本地链接及 git diff --check：通过。
- 新增独立 firmware.yml：原生状态/渲染测试 + IDF 5.5.4 目标构建，上传编译产物及第三方许可；无烧录/发布/部署步骤。远端 Actions 运行结果另行记录，未执行不算通过。
- 前后端运行代码、.env.example、Pages 工作流差异为空；本阶段未重跑不受影响的 Web/后端测试，没有更改 Key 或生产 Mock 机制。

## 已知限制与下一步

- **没有接入实体板。** 实际 PSRAM、LCD ID/批次、QSPI 时序、颜色/方向、闪烁/撕裂、USB 重枚举、串口响应、Windows 工具链/驱动、备份/烧录/恢复、30 分钟稳定性均未验证。
- 未知面板 ID 使用官方驱动默认表并报警日志；不能将此回退声称为支持新硬件版本。先收集该板 ID/丝印/日志，不套用别的板引脚。
- 软件目标与硬件实测必须分别记录；照 HARDWARE_H1 表逐项验收。任何恢复实际执行都以自己同板未加密备份与已核对官方镜像为依据。
- 触摸未接入，串口可测试全部表情；如需触摸交互、AI/音频/舵机或主机通信，另定后续阶段。

## 修改文件与恢复入口

新增 firmware/（工程/锁定依赖获取脚本/显示驱动与许可/状态机/渲染/主循环/原生测试）、.github/workflows/firmware.yml、docs/HARDWARE_H1.md；更新 README、ARCHITECTURE、ROADMAP、本交接。硬件备份不入库。工程恢复用分支提交，实体恢复用 HARDWARE_H1 两种方案；不要将两者混淆。

## 提交与 PR

- 实现提交 `a475b76`：`feat: add H1 ESP32-S3 round-screen expression firmware`。
- `git push -u origin feat/h1-esp32-face`：成功。
- 已创建 [PR #6](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/pull/6)，base=main、head=feat/h1-esp32-face；未合并、未部署。
- 本交付记录作为后续文档提交推送同一分支；最新提交以分支日志为准。

---

# 任务交接

更新：2026-11-11（Asia/Shanghai）。当前交付：**阶段 2B，前后端文字对话集成**。默认/生产/Pages 保持纯前端 Mock，显式开发 API 模式通过同源 Vite Proxy 连接 loopback FastAPI。没有语音、长期记忆、硬件或公网后端部署。

## 基线与恢复入口

- 本次实际 `git fetch origin main` 得到 `d589708`（PR #4 合并阶段 2A）。`git merge-base --is-ancestor c940a4d origin/main` 返回 0，确认 2A 已合并；从该 main 创建独立分支 `feat/stage2b-chat-integration`。开始时工作区干净，未修改 main。
- 先读 AGENTS、README、ARCHITECTURE、当前 API_CONTRACT、本交接和 backend/README。完整启动、模式切换、测试与 2C 建议见 [INTEGRATION](INTEGRATION.md)。
- 严格消费实际 `/api/v0/chat`，没有改动 HTTP 请求/回复结构，未采用 docs/design 归档草案中的 sessions/turn_id。

## 实现决策与兼容性

- 统一 ChatService：`(text, AbortSignal, sessionId?) -> {text, emotion, motion, provider, sessionId?}`。HTTP 将后端 reply 转 text；原 Mock 规则保留，标识 frontend-mock。API provider=mock 明确显示后端 Mock，不伪装真实模型。
- frontend/.env.local 仅非敏感配置：VITE_CHAT_MODE=mock/api、同源 VITE_API_BASE_URL=/api/v0、VITE_CHAT_TIMEOUT_MS；NOMI_DEV_BACKEND_URL 仅 Vite 服务端使用，限制为 loopback HTTP。根 .env 仍只供后端模型配置。没有前端 LLM Key。
- Vite 构建期常量以 command=build 强制前端 Mock，所有生产构建如此，不允许 URL/存储/UI 切换到 API。Pages base 仍为 /Desktop-NOMI/，工作流文件未改。
- 后端 app/ 运行代码和 Host/Origin/CORS/绑定限制均未改。Vite proxy 只调整目标 Host，保留浏览器 Origin，默认前端 5173 与后端原有精确允许来源匹配。
- 会话由每个控制器独立持有，服务对象无会话状态。首轮只发 text，当前请求成功并校验后才记录 UUID，续聊携带 ID。新会话 abort、清空本页记录/草稿和 ID；过期响应不能覆盖新会话。
- pendingMessage 独立于成功历史；成功成对追加 user/assistant，最多 60 条；失败/取消移除临时项，保留全部已有成功记录。输入按 Unicode 码点限制，与后端一致。
- 原 ref 锁、取消/卸载清理、工作阶段/情绪分离和 Expression Adapter 保留。真实 HTTP emotion 经唯一映射层；motion 只存为描述字段，在调试中查看，不执行动作。
- 网络错误、客户端超时、非 JSON/格式错误均使用固定安全文案，不显示服务端 message 或异常原文；错误码/状态先校验。SESSION_NOT_FOUND 需要主动新会话；恢复待机不会偷偷复用失效 ID。
- 停止/网络未知结果明确提醒后端未必停止，重试真实模型可能重复计费，不自动重试。调试预览和模拟错误只在本地发生，不调用模型。
- contracts/chat-v0.json 由当前 Pydantic 生成；后端 pytest 校验快照，前端 unit 校验枚举/必需字段/长度一致。不是新增业务协议。

## 执行命令与真实结果

运行环境 Node 24.22.1 / npm 11.9.0、Python 3.12.14 / uv 0.13.5、Linux 系统 Chromium。所有后端模型均为 Mock/MockTransport，无收费模型或真实凭据调用。

- `git fetch origin main`、祖先检查、`git switch -c feat/stage2b-chat-integration origin/main`：成功。
- 阅读现有文档、控制器、Mock 服务和后端当前 schema/边界：完成。前置兼容性为 reply/text、模式与 Provider 不同、会话失效及生产 Mock 保护，未变更后端契约。
- 在 frontend 中 `npm --cache /tmp/nomi-npm-cache ci`：成功安装 104 个包；未新增运行或测试依赖，锁文件不变。
- 在 backend 中 `uv sync --frozen --group dev`：成功，依赖不变。云端 uv 使用可写 UV_CACHE_DIR=/tmp/nomi-uv-cache 和 UV_SYSTEM_CERTS=true，未关闭 TLS。
- `npm run typecheck`：通过。
- `npm test`：**9 个文件，68 项全部通过**。含 Mock 回归、HTTP 成功/非法输出/非 JSON/服务不可用/取消/超时、全部已实现错误映射、连续 session_id、过期恢复、重复发送、新会话/不同控制器隔离、Unicode 输入、安全文本及诚实 Provider 标签。
- `VITE_CHAT_MODE=api npm run build`：成功，验证即使环境选择 api，生产仍强制 Mock。主 JS 约 618.14 kB（gzip 215.91 kB），保留已有 500 kB 提示，未屏蔽。
- `CI=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:e2e`：**2 项通过**，原桌面/手机 Mock、Aora SVG/动画、调试和错误恢复回归。
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:pages`：**1 项通过**，生产 Mock 标识、无 API 请求、JS/CSS/动态资源、子路径/刷新/首页导航；不能据此宣称公网 Pages 重新上线。
- `UV_CACHE_DIR=/tmp/nomi-uv-cache UV_SYSTEM_CERTS=true PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npm run test:integration`：**3 项通过**。自动启动实际 FastAPI 测试进程 + Mock Provider 和 API Vite；验证 POST、thinking→情绪回复→idle、连续 ID、服务端超时/恢复、真实 TTL 过期、主动新会话、取消隔离和本地调试。无浏览器路由拦截伪造后端响应。
- 初次集成测试与前端格式化操作重叠，Vite 热重载影响首项；固定文件后完整重跑 3 项通过，最后又按顺序运行全部前端检查通过。未弱化业务断言。
- 后端 `uv run --frozen pytest -q`：**68 项全部通过，1 warning**（原 67 + Pydantic 契约快照）。warning 为原有 Starlette TestClient/httpx 弃用提示，未屏蔽。
- 后端 `uv run --frozen ruff check .`、`uv run --frozen ruff format --check .`：通过，30 个 Python 文件格式检查通过。
- actionlint 校验新增 integration.yml 与更新 backend.yml：通过。GitHub Actions 实际运行未验证。
- 文档相对链接、JSON 示例、代码围栏与 `git diff --check`：通过。
- `git diff --name-only origin/main -- backend/app .github/workflows/pages.yml`：为空，后端运行安全边界和 Pages 工作流无改动。
- 所有 Playwright 自行启动的测试进程已由 runner 清理；后续任务不要假定服务仍运行。

## 启动与模式测试

两个终端：backend 中 `uv sync --frozen --group dev`、`uv run --frozen python -m app.cli`；frontend 中 `npm ci`、`npm run dev`。初次使用后端 Mock 默认无需 Key；若根 .env 已选择真实 Provider，应先确认测试模式，勿意外调用收费模型。

Mock：不配置 VITE_CHAT_MODE（或设 mock），前端关键词与调试不发 API 请求，无需启动后端。API：frontend/.env.local 按模板设 api，同源 /api/v0 经默认 loopback 8000；重启 Vite。访问运行这些进程的电脑上的 5173/Desktop-NOMI/。云端本机地址不是远程用户可访问的公网预览。

SESSION_NOT_FOUND 时可保留旧成功记录，但必须点击新会话再发送。停止等待或网络异常后结果可能未知，不自动重试；新会话不表示后端已删除/取消旧任务。speaking 始终只是无声展示。

## 已知限制与未执行

- **真实账号、真实模型输出、真实计费、供应商兼容性、真实网络/TLS：未执行。** HTTP 集成使用实际服务与 Mock Provider，不代表已连通真实模型。
- 未部署公网后端，未验证公网页面新版本、远端 Actions、Windows 实机、实体手机、Safari/Firefox、麦克风、扬声器或硬件。
- API 模式仅开发同源代理；所有生产构建都强制 Mock。当前没有可直接通过 Pages 使用真实模型的公网服务。
- 后端仍为内存、单 worker、无认证/幂等、重启清空。字符预算不是精确 token 数；真实请求重试可能重复计费。
- 前端只提供一个活动会话，新建会清空本页旧聊天和草稿；不实现会话列表、长期存储或同步旧记录。后端上下文窗口可能比本页展示历史更短。
- 保留主 bundle 体积提示与上游 TestClient 弃用提示，未为本阶段扩展性能/依赖升级工作。

## 阶段 2C 建议

见 INTEGRATION 的最小真实验证计划：明确授权/预算后，仅在后端安全配置真实供应商，确认 Chat Completions / max_tokens / JSON mode 支持，再用无隐私输入做一至两轮实测，记录安全结果，不记录 Key/用户数据。health 只代表配置齐全，不代表账号验证通过。不要自动开始公网部署、语音、记忆或硬件。

## 修改文件清单

下方由本次 Git 差异生成，含新增文件；不含被忽略的环境、缓存与测试产物。

```text
.env.example
.github/workflows/backend.yml
.github/workflows/integration.yml
README.md
backend/README.md
backend/scripts/export_contract.py
backend/tests/integration_server.py
backend/tests/test_contract_snapshot.py
contracts/chat-v0.json
docs/API_CONTRACT.md
docs/ARCHITECTURE.md
docs/HANDOFF.md
docs/INTEGRATION.md
docs/ROADMAP.md
frontend/.env.example
frontend/package.json
frontend/playwright.config.ts
frontend/playwright.integration.config.ts
frontend/src/api/contract.test.ts
frontend/src/api/contract.ts
frontend/src/app/App.tsx
frontend/src/app/chatConfig.test.ts
frontend/src/app/chatConfig.ts
frontend/src/app/styles.css
frontend/src/env.d.ts
frontend/src/features/conversation/ChatPanel.test.tsx
frontend/src/features/conversation/ChatPanel.tsx
frontend/src/features/robot/DebugPanel.tsx
frontend/src/features/robot/model.test.ts
frontend/src/features/robot/model.ts
frontend/src/features/robot/useRobotController.api.test.tsx
frontend/src/features/robot/useRobotController.test.tsx
frontend/src/features/robot/useRobotController.ts
frontend/src/services/chatErrors.ts
frontend/src/services/chatService.ts
frontend/src/services/httpChat.test.ts
frontend/src/services/httpChat.ts
frontend/src/services/mockChat.ts
frontend/tests/integration/chat.spec.ts
frontend/tsconfig.json
frontend/vite.config.ts
```

## 最终交付记录

- 实现提交 `58e7d40`：`feat: integrate frontend chat with local FastAPI service`。
- `git push -u origin feat/stage2b-chat-integration`：成功，main 未修改。
- `gh pr create --repo zhengxiangliu6-bit/Desktop-NOMI --base main --head feat/stage2b-chat-integration --title "feat: 阶段 2B 前后端文字对话与情绪集成" --body-file /tmp/nomi-stage2b-pr.md`：失败，`Post https://api.github.com/graphql: Forbidden`；本助手未能创建 PR，不声称远端 CI 已执行。
- 准确 compare 入口：https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...feat/stage2b-chat-integration?expand=1 。API 可访问且授权有效后可重试；临时说明文件丢失时依据本交接重建描述。
- 本记录另作后续文档提交并推送同一分支，最新提交见 `git log -1`。未合并、未发布、未调用真实收费模型。
