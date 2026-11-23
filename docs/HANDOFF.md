# 0.6.5 打包词表

0.6.4 实机的默认词表对照通过，运行时词表对照失败。0.6.5 在构建时更新模型分区里的中文词表，启动逐条验证并用公开参考音频自检。见 [Windows 源码工作流](LOCAL_VOICE_TRACE.md)。实体结果待验证。

Windows GBK 环境构建时，参考音频脚本须显式按 UTF-8 读取依赖锁。已修正，使用模拟 CP936 默认编码运行该脚本及固件工具测试。
Windows 源码实测还发现上游 ESP-SR movemodel.py 使用默认编码读取 sdkconfig。构建入口给 ESP-IDF 及其子进程启用 PYTHONUTF8，保留固定上游源码。
# 当前0.6.4：MN7词表所有权与默认路径对照

用户0.6.3实测官方PCM在**定制测试词表**下reference=0、silence=1；模型初始化失败先于开麦，blocks/raw/AFE全部0是旧fail-closed设计关闭整条采音，不是硬件没声音的证据。模型曾分配到资源，最低总空闲约5.28MB，失败清理后PSRAM约8MB；后者不是运行期值，不断言内存不足或模型本体坏。原日志不入Git。

- 从干净c52cb94独立fix/h3-multinet-command-lifecycle，保留不创建PR/不合并main。逐字对比model分区中6个文件与固定源码一致；官方样本经独立本地ASR确认内容打开空调，约1.42秒已给完整词、2.7秒结束（仅软件内容检查）。
- 用Xtensa nm/objdump确认固定multinet7_quantized.c.obj model_create调用esp_mn_commands_alloc、model_destroy调用esp_mn_commands_free。去掉应用额外alloc/free及所有权布尔；修正重复清理not initialized错误，但不谎称已证实这就是检测失败唯一根因。
- 之前selftest在测试前已clear/update默认词表，不能当官方默认路径对照。新顺序先factory_untouched（不改默认配置、预期ID25），再custom_reference（库已有词表上按上游示例配置打开/关闭空调两条、预期ID1、0.60）、静音。窗口用上游6000ms；输出状态/样本/实际ID/帧数。新增纯reference_probe验证输入不丢样、补零、正确/错误ID、超时、非法参数与低分，不将纯逻辑单测当NN执行。
- 模型未过时关闭识别/动作并保持Fault红色，但独立AudioInput/AFE/音频trace继续；所有结果门控维持关闭，供用户要求的原始音频诊断。硬件/I2S/AFE故障仍真正停止采音。模型和采音所有权分离，清理不重复销毁词表。
- 修改recognizer、wake_controller、reference_probe及其测试、版本0.6.4/CI/构建说明、LOCAL_VOICE_TRACE/API/架构/路线图。用户私有PCM不变，不上传公开Git或Actions；默认词表仅自检临时使用，不执行家电动作、不更换激活名。
- 原生CTest11/11初轮通过；commands初次目标编译另记。最终提交后重建私有包与软件检查；两条NN自检/实际麦克风/唤醒/播放/误触发/30分钟仍需实体执行，不宣称已修好识别。

## 0.6.4交付验证

- C++实现0802c05四profile本地构建/审计/打包通过；11项CTest、10项Python工具测试通过。0802c05的GitHub固件run45160353848全部success，前版66a27f0 run45159953937也success；CI不执行真实板上NN，不能称默认/定制自检已通过。
- ef9f89a仅调整接收工具文案/状态，区分detector unavailable与真正“没有匹配指令”。两轮PTY CLI模拟（默认不录音/显式双WAV）通过，随后commands私有包重新构建打包，source_commit=ef9f89a、source_dirty=false；逐文件SHA256和用户PCM确实在链接app中已复核。
- 本地定制包`firmware/dist/desktop-nomi-model-lifecycle-your-voice-v0.6.4.zip`，7,829,376字节，SHA256 `ba4734f080a53dbbccde479485f0147f91b6ad3b96098b32acef08213c1de128`。用户声音不入公开Git/Actions。代码已推送独立分支，不创建PR/合并main。
- 下一轮先不说话、不继续降低门槛：刷私有包，运行debug/monitor.py --port COM3 --seconds 30 --source raw，记录factory_untouched/custom_reference的pass/got/state/frames，以及DETECTOR ready和原始音频帧。自检失败仍应能采音诊断，但不会执行语音动作；识别问题是否解决尚待此实体证据。

---

# 当前0.6.3：VAD输入修正、模型自检与双路串口音频

用户反馈0.6.2调到0.60仍detected=0、模型timeouts增长，采音/AFE/MultiNet帧继续实时前进，无DMA溢出。随后明确要求判断资源是否跑不动，并把识别前音频与ESP结果发送串口。当前没有证据支持“卡死”，旧日志缺堆/实际推理耗时，不把任务累计时间冒称模型CPU百分比。完整中文转录仍不在MultiNet能力内。

## 证据与边界

- 从干净6887d88新建fix/h3-model-input-audio-trace，fetch最新main但不合并/创建PR。已查固定ESP-SR 1c0503e接口/文档/实际词表代码：中文拼音仍正确、数据16k/PCM16/mono，不能乱改名字或板型引脚。
- **已确认代码遗漏**：esp_afe_sr_iface.h说明vad_cache用于补回截断音频，固定版本AFE文档要求前置；旧fetch忽略它。新增consume_afe验证指针/字节数/对齐/上界，cache→data顺序送模型，统计restored_cache_samples。可能造成短指令开头丢失，仍未证明这是本次唯一根因。
- 不再盲降门槛。现有voice threshold保留以0.60作为前后对照；不将0.60称准确率。用户词表、20秒会话、14表情和私有回复原样保留。

## 模型/资源自检

- prepare_voice_fixture.py从同一固定ESP-SR提交提取公开官方打开空调PCM，验证原头SHA256和派生PCM SHA256，生成到Git忽略的.generated，99,610bytes/49,805samples/16kHz。随包保留原Apache2.0与诊断来源NOTICE；不是用户录音、不上传私人声音。
- commands开机在板上用临时单词表和静音/官方PCM自检：不会播放/发送动作/入事件队列。恢复17个原指令、打印实际模型词表，才能开麦。selftest失败直接Fault而非绿色假可用。silence=0表示静音误报，reference=0表示已知直送样本未命中，不能直接等同内存不足；PASS仍不证明小米同学或麦克风通过。
- MN_RUNTIME报告推理调用墙钟last/每32次mean/max/帧预算及超预算次数（包括调度等待，不是纯CPU百分比）；HEAP报告internal/PSRAM free与largest及最低总堆；AFE_PCM为实际送模型电平/零块/恢复缓存数。所有已知资源异常仍fail closed，FaceModel渲染保持独立。

## 串口音频与显示工具

- AudioTrace/TraceFramer：显式trace on/token开启，CH1原始MIC1、CH2正常识别时恢复VAD缓存后的AFE流；独立序号、320样本连续帧/FNV/flags/base64，@NTRC1与PC识别NOMI2分离。捕获/推理各自拥有缓冲，不插零凑AFE块；停止不足20ms尾部不发送。
- 每次USB写有界等待，commands stdout也切到同一驱动，避免默认轮询VFS旁路写FIFO破坏音频包；完整帧原子入环；慢主机/丢失心跳2s关追踪，保留本地识别。原始流在播放保护中仍可能含真实声音，带flags，AFE流保护期间不供模型识别。默认不开传输、不保存/上传。
- @NRES1原子输出每个DETECTED最高候选ID/配置中文标签/分数，非任意中文转录。无候选不编造词；底层传输背压可能丢诊断文本，但detected计数仍可靠。不因日志当作控制动作，原USB控制ACK不变。
- tools/local_voice_debug/monitor.py + start_debug.cmd随commands包，只用pyserial和标准库，不安装/调用电脑ASR或云端。显示双路电平与ESP32候选，默认20秒后关追踪，不关设备本地麦克风；显式--record-dir才写两个WAV，拒绝覆盖旧文件、校验失败不补静音，异常也关闭文件。原用户音频只从仓库外导入私有包。

## 文件与软件验证

- 修改main/voice/command_recognizer.*、wake_controller.*、main、CMake/构建脚本/CI/版本0.6.3；新增afe_input.h、audio_trace.*、trace_framer.h、prepare_voice_fixture.py、诊断NOTICE、debug工具、LOCAL_VOICE_TRACE和相关原生/Python测试；同步H1/H2/README/离线/API/架构/路线图。未接AI/云端ASR/动态TTS/触摸。
- 本地commands初步目标构建通过；后续增加候选原子输出初轮缺cstdio编译失败，已补显式包含，最终构建另记，不将失败写成通过。临时单词表ID使用官方示例同样的1，避免未承诺大ID范围。
- 已执行原生CTest10/10、Python10/10、PC22/22、共享目录--check、actionlint/diff；真实C++TraceFramer→Python解码2560样本逐值一致/CRC通过；PTY模拟CLI两轮通过（默认不录音、显式双WAV内容一致，均无ASR加载）。不将模拟串口或模型fixture校验冒称板上自检PASS。
- 实体自检、双路USB吞吐/电平/缓存恢复、推理/堆/栈、准确激活/误触发、用户回复/回灌、30分钟稳定仍待用户验证。下一轮第一步看自动MN_SELFTEST，不需反复喊；FAIL分别看silence/reference，再决定模型层或输入层排查。

## 0.6.3最终交付记录

- 源码42a39ba；四profile本地ESP-IDF5.5.4最终编译/审计/打包通过，各包source_dirty=false并逐文件SHA256复核。commands私有包核验原用户PCM和官方自检PCM都在链接app内，含debug/monitor.py、start_debug.cmd、完整诊断指南与原许可证；应用1,281,984字节，小于4MB应用分区。文件大小不是运行时RAM占用，不冒称现场内存验收。
- 下载别名`firmware/dist/desktop-nomi-audio-trace-your-voice-v0.6.3.zip`，7,825,298字节，SHA256 `6a203f3dd95e7d35b3c3cee8e481710eae804f4ab0ff6622044e4a814309e027`。用户音频仍仅本地私有素材，不进入公开Git/Actions。
- GitHub固件run45040652856（42a39ba）host_asr/native/四ESP32S3目标全部success；前两轮0e2de00/91a0513也success。**CI不执行板上MultiNet自检，也不包含用户声音**，不能把它当硬件PASS。
- 本轮软件证据：CTest10/10、Python工具/协议10/10、PC22/22；C++→Python音频协议2560样本逐值一致；PTY CLI两轮默认无录音/显式双WAV成功；源码推送完成，无PR/合并main。docs/LOCAL_VOICE_TRACE包含分路raw/afe/both与20秒/显式录音方法。
- 用户下一步：刷定制commands包，等初始化自检后用debug/monitor.py接收状态与音频（无电脑ASR）。第一步可选--source raw降低带宽，之后--source afe或both。先看MN_RUNTIME selftest，再看原始/AFE电平、cache_samples、推理预算和HEAP，最后说一次目标词；FAIL分别看silence/reference，不继续盲喊或盲降。全部真实硬件判断待这轮数据。

---

# 当前0.6.2：本地未激活的诊断与门槛校准

用户0.6.1实测绿色但叫名无反应。两次状态约13.23秒内frames/blocks/fetched增413、vad_speech增244，timeouts/overflows/dropped为0，无重启证据；这里旧timeouts为采音无数据，不是模型超时。仅能确认数据/推理循环持续运行，不证明有效激活。不能把问题归因用户发音或烧录失败，不保存用户原日志/音频。

- 从干净0e8544b创建fix/h3-local-command-diagnostics，不创建PR/合并main。检查固定ESP-SR源码确认中文拼音接口仍适用、输入16k/PCM16/mono契约未发现证据性错误。旧模型与UI均硬编码0.90且无识别统计；高门槛只是待检验因素，不能声称已找到根因。
- command_recognizer增加DETECTED候选ID/配置标签/分数（1秒限频）和检测/模型TIMEOUT/低分拒绝计数，status可查看；不读取模型未承诺状态下的get_results，不输出原始字符串冒充转录。没有返回候选时只报计数，last_score明确为历史值。
- 新voice threshold N，30–95临时校准；默认仍90，建议实体单次试60获得证据。请求原子传推理任务，set_det_threshold/clean都在owner内执行，VoiceSession接收门槛改为读取同一已应用值；变更结束UI会话，过时事件由cutoff隔离。重启90，reinit保留本轮设定；未改用户词表/音频/引脚/20秒会话/USB协议。分数不是百分比准确率，也没证明60是正式可用门槛。
- 文件：main/voice/command_recognizer.*、voice_session.h、wake_controller.*、main、原生门控测试；版本0.6.2、构建包说明/CI触发及OFFLINE/API/架构/路线图。本轮用户声音沿用仓库外私有素材，公开Git/Actions不含声音。
- 已执行CTest8/8（增加默认0.90拒绝/0.60接受与低分、非法门槛拒绝）、Python9/9、actionlint/diff检查；commands目标初编译审计通过。提交后最终私有包/源码和完整目标检查另记。未声称硬件唤醒或0.60校准成功；下一步要用户一次测试候选与模型超时统计，若无候选继续查模型链路，若有则分别看ID/分数/会话接受，不盲目继续降低。

## 0.6.2交付记录

- 源码8f8a205，四profile本地ESP-IDF5.5.4最终构建/审计/打包全部通过，manifest source_dirty=false。私有commands包核验每个文件SHA256且原选定PCM确实在链接app内，用户音频未入公开Git/Actions。
- 诊断包`firmware/dist/desktop-nomi-local-voice-diagnostic-v0.6.2.zip`，7,677,261字节，SHA256 `7690c9c4b1ef8b450b8cfd5abab6abeef0819510527a520062d5b6b3faab64df`。此包默认门槛90，使用时必须显式voice threshold 60并等APPLIED，再说一次目标词和wake status。不是已证明修复的生产门槛。
- 公开GitHub固件run43902835650交付时仍运行，不写成云端通过；它只用仓库默认音频。原生8/8、Python9/9、actionlint/diff本轮已执行通过；私有目标本地构建完成。未创建PR/合并main。
- 必须索取下一次实体候选/超时/接受或拒绝证据；当前不能声称小米同学唤醒成功或误触发率通过，也不能把score0.60称60%准确度。若60无候选，暂停盲降并进一步查模型/音频处理；若候选为其它ID或被拒绝，按对应层排查。

---

# 当前0.6.1：用户选定固定回复的私有烧录包

用户上传okay.mp3，明确延续“替换占位声音并打包”的工作。原MP3及转换音频只在本次本地定制构建使用，不提交公开Git/Actions；不以泛化的代码推送授权推定可以公开个人声音。独立分支feat/h3-private-reply-package来自干净204717b，不创建PR/合并main。

- 文件检查：MP3/24kHz/mono，容器时长0.744秒；FFmpeg解码并重采样PCM16/16kHz/mono后0.696秒/11,136采样/22,272字节，峰值11,876、无数字削波。只改格式，未重合成、加混响、归一化或调速。
- 代码仅增加私有素材构建支持：import_reply --output-dir（仓库外PCM/JSON/NOTICE）、build --reply-assets、nomi_audio CMake外部PCM路径、许可按实际素材存在选择、manifest custom_reply_asset标志。每次构建显式传入默认/自定义路径以避免CMake缓存错误。原本地有限指令/14表情/20秒会话/音频驱动/协议均未改。
- 固件版本0.6.1，用于区分私有声音包；公开源码/CI仍用旧占位音色，不包含用户MP3或转换采样。私有素材目录不写到manifest，只保留所选PCM的正常校验信息。README/文档提供外部目录方式，用户无需为构建而公开声音。
- Python工具测试9/9（新增外部导入不改默认资产/不复制源路径及外部hash破坏拒绝）；本地commands初步编译/审计已通过，提交后重建最终私有包；真实本地ASR仅检查固定“好的”内容，结果另记。代码改动不涉及运行时表情或播放，沿用已过的原生8项和PC22项基线，不冒称新执行。
- 私有包尚未上板，未验证本地唤醒率、实际音色/音量/爆音/防回灌和30分钟稳定；默认0.6.0本地指令闭环本身也尚待用户实体验收。可用前版0.6.0或0.5.x USB完整包回退，不整片擦除/覆盖原厂备份。

## 私有定制包交付结果

- commands目标最终ESP-IDF5.5.4编译/链接审计/打包通过；源码6a30c2e、source_dirty=false、custom_reply_asset=true。私有PCM实际存在于链接app，包内WAV逐采样与所选PCM一致，逐文件SHA256核验通过，mn7_cn/fst模型完整。
- 本地交付别名`firmware/dist/desktop-nomi-offline-your-voice-v0.6.1.zip`，7,595,360字节，SHA256 `083381e308464fdea1e49ae9661e890cb773747b6fd9548eff8132f1c184d756`；`okay-user-preview.wav`供用户试听。定制包/MP3/转换采样均未提交Git或上传公开Actions。
- 真实本地ASR将私有固定音频解码为预期“好的”，只记测试成功不记录用户音色数据；不能替代板上听测。工具9项通过。新增私有素材构建代码已推送，公开CI只测试默认素材，不宣称云端编译了用户声音。未创建PR/合并main。
- 用户应解压定制commands包至新目录、关闭旧COM3程序，按flash_args全部烧录；不运行start_control.cmd。先待机绿色→“小米同学”→橙色播放保护→蓝色再说“开心一点”。冷启动/识别率/声音/回灌/30分钟仍待实机验收。

---

# 当前0.6.0：ESP32本地指令到固定回复闭环

用户拒绝0.5.1音色，拟自行生成音频；授权先完成不依赖电脑的有限指令/表情/回复闭环，并说明音频类型和替换方法。独立feat/h3-offline-command-reply从干净aae18d2创建，不创建PR/合并main。新用户音频尚未收到，现有Melo“好的”只是占位，不能称音质已改善。

## 修改与设计

- 新`main/voice/fixed_reply_player.h`为无分配、RX时钟驱动的共用播放内核；适配160/320/512/1024采样块，20ms写入，立体声复制/尾帧补零/100msDMA排空/300ms尾音/异常取消关PA。USB重用相同内核，PC协议和词表不改。
- `wake_word_controller.*`新增单项播放请求队列/epoch校验/原子保护；采音唯一资源所有者开始播放，从UI接受请求起屏蔽结果，AFE继续零采样，fetch丢弃保护期结果并仅在边界清MultiNet；额外2秒排空50×1024字节AFE+VAD历史，结束恢复。清理/故障/停机取消音频并关PA，不在UI或fetch操作Codec。
- `voice_session.h`保留ID1–11，增加12–17对应六种新表情；Wake与Extend分开，已激活重复叫名只续期。main接受Wake/Expression/Sleep时请求一次固定回复，忽略/超时/重复不回复，保护时橙点，准备好绿色或会话内蓝色。原20秒会话/5秒表情/14项demo保留。
- 新`scripts/import_reply.py`（stdlib）接收PCM16/mono/16kHz WAV/0.1–3s，拒绝静音/数字削波/截断/错误格式，一起更新PCM/JSON/hash/NOTICE；不联网、不自动Git或烧录，不把源路径存进manifest，不推定用户素材公共许可。构建审计覆盖commands与usb_asr，长度上限96KB；commands包也含试听WAV/许可。默认资产未改，生成器仍可用于默认占位素材，用户替换后不要求安装神经模型。
- 固件0.6.0、固件Actions新分支触发；新增OFFLINE_COMMAND_REPLY完整Windows烧录/14词表/音频格式/转换/替换/重建/恢复/验收文档，同步H1/H2/架构/API/路线图/计划/README。未接Wi-Fi/AI/动态TTS/触摸，API Key机制不改。

## 已执行检查

- 本地commands初次目标编译/链接审计成功，USB初步目标构建另记；最终提交后重建/打包与云端结果补记。
- 原生CTest8/8（新增通用播放器四种采样块、双声道相等、尾帧补零、时序、重入/失败关PA/取消；新增六表情/重复激活Extend回归）；Python构建/导入7/7、PC22/22；actionlint/diff检查通过。不是硬件测试。
- 用户没有验证本版MultiNet准确度、全部本地短语、物理音频防回灌/栈/RAM/30分钟稳定，准确“小米同学”专用WakeNet仍不可用。当前是MultiNet有限匹配，无任意中文转录，不把ID日志冒充文字识别。不承诺否定语意理解。

## 最终0.6.0交付

- 实现提交fcc77c0；四profile本地ESP-IDF5.5.4最终构建/链接审计/打包全部成功，逐文件SHA256核验通过，source_dirty=false。commands包核验含mn7_cn+fst且模型>1MB，无pc目录，试听WAV与嵌入PCM逐采样一致。
- 本地别名`firmware/dist/desktop-nomi-offline-command-reply-v0.6.0.zip`，7,593,424字节，SHA256 `5ceff20dd25b28bb16e30e7500dfd71c1f15ee77f9aedda4406a12f45c9f1617`；默认仍为用户嫌弃的0.5.1占位声音，用户新音频未收到。USB包同时构建保留作兼容回归，本次刷commands而非usb_asr。
- GitHub [43894707716](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43894707716)：host_asr/native及四个ESP32S3目标全部success，四个固件Actions产物可下载。云端运行了原生8项/Python7项/PC22项和真实固定PCM软件解码；不把这些当实体MultiNet检测或扬声器听测。
- 新增/主要变更文件清单见上节；独立分支feat/h3-offline-command-reply已推送，未创建PR/合并main/改Pages。完整OFFLINE_COMMAND_REPLY指南包含WAV类型、转换、导入三文件、构建/烧录、原厂及USB回退和硬件验收表。当前文档补充说明源码必须为当前分支，二进制ZIP本身不能直接重建。

## 下一步

先按OFFLINE_COMMAND_REPLY刷commands完整模型包，冷启动用电源测试离线闭环；先看VOICE_READY再读词表。用户提供自己的固定音频后导入/试听、重新编译烧录；现有包仍是被嫌弃的占位音色。不要运行PC ASR程序配合本地固件。稳定后再设计Wi-Fi/ASR/AI，API Key留后端。恢复用保留的0.5.x USB完整包+PC0.5.0或已验证原厂备份，不整片擦除/覆盖备份。

---

# 当前0.5.1：更换固定“好的”音色；脱离电脑与AI仅做方案

用户已实测0.5.0整体效果可用、扬声器能播放但音色难听；认可20秒会话，不要求修改。用户明确要求不要修改“回到待基”别名，转向评估ESP32独立识别/回复、AI意图/表情与免费语音；先完成播报改进。

## 本次边界与文件

- 从干净`feat/h2-expression-gallery` / `1c45e2a`创建独立`feat/h2-natural-reply`。临时添加的同音别名/生成器/共享目录/PC测试变更已全部git restore，未提交未推送；原始ASR和严格词表、14表情、20秒会话均保留，PC仍为0.5.0。不创建PR、不合并main。
- `firmware/components/nomi_audio/assets/okay.pcm`替换eSpeak为公开MeloTTS中文女声离线生成的固定“好的”。新meta记录模型源包/ONNX/PCM SHA256、sherpa-onnx2.0.1CPU/speaker0/speed1、FFmpeg7.1.5；17,090bytes/8,545samples/534.0625ms。LICENSE/NOTICE完整记录MIT来源；无用户录音/定向克隆、不分发模型权重或推理运行时、不执行云端收费合成。
- `generate_okay.py`改为开发用神经生成器，要求传已下载模型目录并核对模型hash；只生成固定字句，输出≤1秒。神经生成不保证每次字节一致，release PCM/hash权威。一次开发下载前未等待完成就解压失败，下载完成后重新解压/推理成功，不将失败轮算通过；试验AISHELL模型没有采用/打包。
- 固件版本0.5.1，仍兼容PC0.5.0与现有协议，不需重新装模型/PC。build打包新增MIT许可、直接从嵌入PCM导出试听WAV（不另维护音频副本），音频长度保护仍按实际样本计算，测试改为27写帧+5DMA+15余音=47×20ms约0.94秒。播放/采音/FaceModel实现未改。
- 新增VOICE_NEXT_PLAN：免费模型与板载资源、离线有限指令vsWi-Fi自由对话对比、规则优先/复杂语意AI、后端Key隔离、分段上传与断网回退、实施/验收顺序。只是方案，本次未加入联网/ASR/LLM/动态TTS。更新README/硬件/架构/API/路线图/表情/播报文档和两套CI分支触发。

## 0.5.1交付与云端记录

- 实现提交53b5d9d；初轮USB试听WAV打包因局部writer变量遮蔽输出ZIP路径失败，已在0bbebfc修复。最终usb_asr本地编译/打包及逐文件SHA256/WAV实际采样数据一致性复核成功，manifest source_commit=0bbebfc、source_dirty=false；原生音频/benchmark/commands本地也构建通过。
- 下载别名`firmware/dist/desktop-nomi-natural-reply-v0.5.1.zip`（完整usb_asr，约4MB），SHA256 `fe43aef4f181dd6c2e3b349d75235a267207d5c9cea126917b583884233e57fd`。包内okay-preview.wav是嵌入PCM的16kHz16bit单声道WAV，不是另一套音色；licenses/MeloTTS.txt和assets/okay.json随包。可保留PC0.5.0原安装，只刷固件；回退可用0.5.0完整配套基线。
- GitHub [Windows/Linux43891229793](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43891229793)全部success，覆盖新PCM真实解码、旧控制/播放保护测试。新生成器不进入PC运行环境，不需重装依赖。
- GitHub [修复后固件43891465230](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43891465230)：native/host_asr/usb_asr/benchmark/commands均success，audio任务仍在运行时记录。实际交付的usb_asr云端编译/审计/产物已成功，不能把尚未结束的audio写成绿色。前次53b5d9d固件run失败保留历史，不冒充通过。
- GitHub分支feat/h2-natural-reply包含此前全部代码，已推送；main核对仍为e06e8a9。未创建PR/合并main/改正式Pages。若用户以后要合并，使用main...feat/h2-natural-reply包含新音色；不要只合并旧gallery分支而期待得到0.5.1。

## 已执行验证与待验

- 真实固定中文ASR2.0.1解码新PCM为“好的”，公开中文样本/PCM校验软件测试通过。原生CTest7/7、PC原22/22、构建Python6/6、共享目录--check、actionlint及diff检查通过。确认PC/词表/共享表情文件无diff，临时别名测试不计为交付测试。
- 源码提交后构建最终包/云端检查，结果将补记。无需跑未修改前端的全套浏览器回归，前版Pages绿色基线保留。
- 不声称自己听到了新版实际板声。用户需要先试听导出WAV，再刷0.5.1验音色/音量/爆音/回灌/30分钟稳定；数字DONE和ASR对字不代表声音好听。0.5.0旧硬件出声已由用户证实，本版仍待听测。
- 推荐下一阶段先把USB播放器解耦为独立服务并接ESP-SR有限指令，真正脱离电脑做14表情/固定回复闭环；专用小米同学WakeNet仍未取得，有限MultiNet激活需准确标记/实测。再接Wi-Fi后端ASR、规则，最后复杂AI/动态TTS；API Key留后端，不写Pages/固件。本次不提前实现这些模块。

---

# 当前0.5.0：14表情、对应静态图库、可静音测试的固定回应

用户在测试“好的”之前要求超过10种不重复且明显不同的表情、语音/串口切换、原GitHub静态页可看对应效果，并确认代码上传和合并方法。独立分支`feat/h2-expression-gallery`从已推送`70a7d81 feat/h2-spoken-okay`创建；main仍为e06e8a9，包含此前所有H1/H2提交的最终分支可一次合并。不自动创建PR、合并main或部署正式Pages。

## 0.5.0最终交付验证

- 实现源码提交`9f6f997`；`047537d`仅新增GitHub分支可直接查看的LVGL总览PNG及文档引用。四profile本地ESP-IDF5.5.4最终编译、链接审计、打包全部通过；manifest source_commit=9f6f997、source_dirty=false，逐文件SHA256复核通过。
- usb_asr binary实际671,728字节；链接器静态DIRAM87,443字节/341,760（动态堆与运行时栈仍需实机观察）。交付别名`firmware/dist/desktop-nomi-expression-14-v0.5.0.zip`为usb_asr完整包，SHA256 `1edfb14e0e9402c669a47e0f3de68349a7edd0f6a8764445eea3bc4e444eae4f`，约4MB。PC单独更新包`tools/usb_asr/dist/desktop-nomi-pc-voice-control-v0.5.0.zip`包含生成目录和两份升级指南，不含模型/venv/用户录音；完整固件包已包含pc文件，不需重复下载。
- GitHub [固件检查43870955739](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43870955739)：host_asr/native/audio/benchmark/commands/usb_asr全部success；四个profile可下载Actions产物。用户本次选usb_asr。
- GitHub [Windows/Linux本地ASR43870955756](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43870955756)：两平台固定依赖/中文样本和“好的”软件解码/测试及PC打包全部success。
- GitHub [Mock Pages43870955734](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43870955734)：build/tests成功，功能分支deploy按设计跳过，静态审阅artifact可下载。正式Pages仍需用户合并main后更新；未自动创建PR、合并main或发布。
- `git fetch origin main`后确认origin/main是HEAD祖先；当前最终分支已经包含此前所有硬件代码。此记录为软件构建及上传证据，不能代替本版实体14表情、扬声器和30分钟验收。

## 实现与文件

- `shared/expressions.json`14造型和严格语音别名；`firmware/scripts/generate_faces.py`生成`firmware/main/face_catalog.h`、`tools/usb_asr/face_catalog.py`、`frontend/src/features/hardware/expressions.generated.ts`，prepare/build及Pages检查生成文件同步。
- 固件`face_model.*`、`face_view.*`、main、remote_control：保留8种并新增angry/surprised/sleepy/wink/love/confused；眉毛/眼型/嘴型/泪水/爱心/符号明显区分，LVGL矢量、180ms插值、圆屏安全半径160。demo依次14项，串口命令保留，状态逻辑独立；remote指令目录共享。0.5.0 probeall握手拒绝旧8表情能力。
- PC`voice_control`、`command_channel`、`transcribe`、`package_pc`及测试：全部14种别名可达，新增--silent-replies强制spoken=0，保持ASR/模型/依赖与20秒会话、编号回执/幂等机制。默认声音包含此前0.4.3实现，新版需配套固件更新。
- Web`src/features/hardware/`SVG图库、选择/重播/轮播/中文短语；App/header/styles入口和Pages浏览器测试。原聊天/Aora/后端/API Key机制不改，预览不控制设备。新增网页和固件实际LVGL造型同目录，动画时序/抗锯齿不保证逐像素相同。
- 三个Actions工作流支持最终分支；Pages功能分支只编译测试和静态审阅artifact，main才部署。新增EXPRESSION_GALLERY，更新H1/H2、PC、SPOKEN_OKAY、README/架构/API/路线图；所有原厂备份未触碰，无整片擦除。

## 已执行验证与待办

- 原生CTest7/7（含14张真实LVGL渲染、半径160安全区、91对至少500不同像素、14命令可达、状态/音频/回执/播放保护回归）。PC单元22/22，含所有目录语音别名及静音标记；构建审计Python6/6；generate_faces --check、actionlint、git diff --check通过。
- 前端typecheck/build通过；Vitest70/70，常规桌面/手机浏览器2/2、Pages子路径与图库浏览器2/2。手动查看桌面和390px手机截图；原Mock入口/资源刷新/无网络调用回归通过。现有Aora大chunk告警仍存在，不妨碍构建。
- USB目标初步编译已通过；提交后将对四profile重新构建、打包并检查CI，结果另补交付记录。下载包必须显示source_dirty=false；不将源码检查当实体测试。
- 新14种实体屏幕/新别名Windows实测、固定“好的”实际出声/音质/爆音/防回灌、30分钟稳定性均待用户验收。0.4.2用户报告效果很好是旧基线证据；没有“小米同学”专用WakeNet模型，本版仍需Windows本地ASR。

## 用户下一步与恢复

[EXPRESSION_GALLERY](EXPRESSION_GALLERY.md)提供14项指令、0.5.0成对烧录/PC合并、先--silent-replies后听测、最终分支合并main发布Pages的具体步骤。旧venv/models保留，不需setup。可回到已验证0.4.2配套包；原厂恢复见HARDWARE_H1。GitHub代码推送/CI和包哈希在最终交付补记，不宣称正式Pages已更新。

---

# 0.4.3：板载固定语音回应“好的”

用户反馈最新0.4.2效果很好，保留为可用基线（未逐项补报全部异常/30分钟验收）；本次明确要求板载扬声器在执行指令时简单说“好的”。授权范围扩为固定短音频反馈，不接云端/运行时完整TTS/自由对话，不改变Windows本地ASR依赖，不保存用户录音。

## 方案与硬件核对

- 从干净`fix/h2-control-ack-session` / `0f4e79a`创建独立`feat/h2-spoken-okay`，不创建PR、不合并main，不改原厂备份或执行自动擦除。
- 官方Waveshare1.85B固定提交5a98b8da1948340c07032a408ac0d93c47ca558f已核对06_mic_test/BSP：ES8311 DAC、PA GPIO9默认非反转（高启用）、I2S1 MCLK2/BCLK48/WS38/DOUT47/DIN39。沿用现有16kHz/PCM16/stereo时钟，不照搬其它板、不重开24kHz影响采音。
- 固件内置固定合成“好的”，15,766字节/7883采样/492.6875ms；开发时eSpeak NG1.52.0 cmn/rate150、espeakng-loader0.2.4、FFmpeg7.1.5离线生成/归一化。此为用户新固定回应需求的构建资源，不是用户录音、不克隆真人。PCM与来源/格式/SHA256/NOTICE随源码，生成器不进入运行环境，不补造引擎许可。
- 采音任务独占DAC操作：音量60/100、DAC解静音、GPIO9高；分20ms立体声同样本块直接写已有TX，UI不阻塞。播完留约100ms DMA排空再低PA/静音，300ms余音保护；失败/停止/断线清理也关闭功放。实际响度/音质未听测。
- 保持RX和连续帧，保护区间NOMI2 flags=1、实际mic数据替换为零；PC在保护开始/结束重置ASR且不喂入保护帧。基础半双工，不做AEC/打断；约0.9秒内用户说话也忽略，听完并恢复识别后再说下一条。

## 行为和协议

- 明确接受的人声唤醒/表情/休息回应一次；extend重复叫名、自动超时idle、probe/拒绝/清理不回应。重复同编号不再次触发动作或音频。
- ctl新增spoken=0/1字段；RemoteControl缓存包含该标志。NOMI_ACK1确认动作，NOMI_SAY1 START/DONE/ERROR单独报告数字输出流程，不代表物理扬声器听测成功。NOMI2 flags纳入FNV校验，不伪装连续真实mic数据。
- 必须固件/PC0.4.3成对更新；旧固件不能通过新控制握手。原模型锁/requirements/venv不变，不重新setup/下载模型。

## 文件及已执行验证

- 固件：AudioInput增加speaker_begin/write/end；component CMake嵌入assets/okay.pcm及json/NOTICE，scripts/generate_okay.py仅开发复现；新playback_guard.h和测试，修改USB stream/remote/main/pcm frame、版本/构建审计/打包。原引脚、采样率、FaceModel、模型与Web API/Pages/密钥机制未变。
- PC：新增recognition_gate.py和test_spoken_reply.py，调整protocol/recognizer/command_channel/transcribe/voice_control（超时late-final静音）/smoke_test/package及相关测试；setup与依赖不变。文档新增SPOKEN_OKAY，更新PC说明、README/架构/API/路线图及本交接。
- 本地PC单元20/20、原生CTest7/7、Python构建审计6/6；固定PCM在真实本地ASR解码成“好的”，公开样本软件链路也通过；actionlint/语法检查通过。usb_asr目标链接已通过；初次嵌入符号路径按IDF实际导出_binary_okay_pcm_*修正后通过，不宣称初次失败为成功。
- 验证涵盖保护期不送ASR/重置/标志校验、仅人声指令播放、超时/重复不播、I2S块数/排空/尾音/取消、状态/表情/编号协议回归。**不能验证ES8311实际出声、音量/爆音/音质、真实声学回灌抑制、实际DMA/USB稳定性或30分钟硬件运行**。
- Windows软件和固件CI/最终ZIP结果记录在交付节。第一轮用户实测应只唤醒听一次“好的”，等恢复再说“开心一点”；没有声音时看SAY START/DONE/ERROR和设备错误，不把数字DONE当听测通过。

---

# 0.4.2：Listening后台回执超时修复

用户0.4.1上传日志有两次PC`listening`确认1.5秒超时。第二次发生于新唤醒词临时结果，尚未提交新唤醒；第一段已激活重复唤醒曾成功，后续后台刷新才超时。因此不能归因于“重复唤醒直接崩溃”，也未看到足够设备重启证据。普通日志缺失/无法重组的具体成因未实机确认，不伪称已定位某个硬件故障。不提交用户原始日志、完整对话或音频。

- 从干净`feat/h2-pc-voice-control` / `a548b94`新建`fix/h2-control-ack-session`，不创建PR、不合并main、不改备份。此前仅PC更新的承诺适用于0.4.1；本修复为摆脱旧日志确认，**必须成对更新固件和PC到0.4.2**，原模型/依赖不变，不重新setup/下载模型，不整片擦除。
- 新`firmware/main/stream/remote_control.h`：独立20秒远端会话/5秒展示、probe/extend/八表情、序号缓存幂等、重复/旧请求无副作用、租约失效回idle。UI负责渲染和到期检查，不把控制逻辑放入FaceModel。
- main接受`ctl token seq action`，验证当前音频会话租约后执行并入队完整ACK；采音任务有界队列发送`@NOMI_ACK1 token seq action status hash`单次driver write，脱离ESP_LOG逐字符日志。仅USB profile TX缓冲1024→4096，UI队列写不等待，不阻塞显示。保留NOMI1 PCM、原采样/引脚、ASCII手动命令和八表情。
- PC CommandChannel用token/seq/动作/FNV校验确认，probe #0握手；普通日志不能确认，旧会话/延迟回执不确认新指令，不自动重发动作。缺失/错/损坏回执仍明确停机，不把它静默当成功。
- VoiceControl取消全部2秒Listening续发；固件自动保持/恢复Listening到20秒。已激活再次叫名称只extend续期，不重置当前表情；新增“眨眼一下”“开心一下”“难过一下”明确别名，不做模糊匹配。临时/停止结果和无关/否定句仍不执行。
- 升级版本、打包/文档/CI：完整固件ZIP带pc和当前PC控制说明；单独pc更新包标明需0.4.2固件，旧0.4.0握手拒绝。Windows/Linux软件测试、四profile目标构建及原生状态/渲染/PCM回归列入Actions。

## 文件与验证

- 固件：新增remote_control.h/tests/remote_control_test.cpp，调整main.cpp、usb_audio_stream.h/.cpp、CMake版本/测试、build.py打包；无Codec/引脚、模型或前后端/API Key/Pages改动。
- PC：调整command_channel.py、voice_control.py、transcribe.py、package_pc.py及两套测试；模型锁、依赖及start/setup安装方式不变。文档更新PC_VOICE_CONTROL、tools README、根/firmware README、架构/API/路线图/USB说明和交接。
- 本地PC测试16/16、CTest6/6（含设备会话/重放/续期/租约/ACK格式与跨语言校验向量）、actionlint通过。usb_asr目标编译已通过；完整新产物与远端结果见交付记录。
- 已有用户短时实际成功唤醒/happy/sad/blink/休息反馈，伴随本次两次异常；不能算0.4.2修复通过、全路径或30分钟验收。**0.4.2实体重复唤醒、稳定ACK/会话到期/断线/实际屏幕仍待复测**。云端成功不能代替实体证据。
- 本次不承诺固定一次说话一定识别，不提高ASR/传输时延阈值掩盖回执异常。先看0.4.2握手、重复唤醒extend、无周期Listening发送，再复测普通表情、20秒静音待机和退出。


## 0.4.2 最终交付记录

- 实现提交`3e12f57`已推送`fix/h2-control-ack-session`，不创建PR、不合并main。后续本节仅作交付记录。
- 完整固件包`firmware/dist/desktop-nomi-control-fix-v0.4.2.zip`约4.1MB（usb_asr.zip同内容），内含0.4.2固件、pc程序、当前说明和哈希；app651,696字节、空模型4字节，布局/引脚/依赖未变。单独pc更新包也已生成，但不能搭配0.4.0固件使用。
- 四profile本地目标构建/审计/打包通过；完整包和PC包manifest source_commit=3e12f57、source_dirty=false，逐文件SHA256复核通过。无用户日志/录音、权重或venv写入ZIP。
- [固件CI 43736013355](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43736013355)：四ESP32构建、native、host_asr六job均success。[PC CI 43736013387](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43736013387)：Windows/Linux软件测试及公开中文解码、打包三job均success。目标编译/软件验证不代表0.4.2实体复测通过。
- 用户升级：关闭旧程序；新ZIP解压`D:\NOMI-042`，在该目录用现有esptool COM3和@flash_args完整写入；将新pc合并至原`D:\NOMI-ASR-debug`保留venv/models，在原pc目录运行start_control.cmd COM3，跳过setup。原厂备份不动，不整片擦除。
- 待用户重点复测probe编号握手、Listening再次叫名称只extend、表情展示中重复唤醒不中断、两种眨眼短语、20秒静音待机和断线。旧普通日志回执缺失的具体物理成因仍未实证，本修复移除其控制依赖及周期刷新流量，不伪称已实测根治硬件异常。

---

# PC 0.4.1：Windows本地ASR驱动唤醒和表情

用户已明确同意“利用现有中文转录链路，先唤醒/表情/20秒待机”，并要求开始修改。**本次只更新PC程序，沿用0.4.0 usb_asr固件、同一模型和依赖，无需重新烧录、setup或下载模型。** 仍需Windows运行，不是ESP32独立识别。

## 基线与实机证据

- 从干净`feat/h2-usb-chinese-transcription` / `6fc6723`创建独立`feat/h2-pc-voice-control`；不创建PR、不合并main、不修改备份或固件。
- 用户Windows Python3.11/x64实际安装成功，使用板载MIC1经USB得到多句中文临时/最终结果；短时连续帧从86增至1993、队列一般2–3、绝大多数时段无削波，最后一段有瞬时削波；Ctrl+C关闭串口正常。说明原始采音→USB→Windows本地ASR短时链路已通过用户实测，不能推断长期稳定或0.3.0独立唤醒已通过。不记录其原始对话/日志或录音到仓库。

## 修改与决策

- 新增`tools/usb_asr/voice_control.py`：只消费最终中文，NFKC/标点/空格归一化后精确匹配“小米同学”或“你好小米同学”；七种非idle表情短语、休息/待机，20秒窗口、重复去重、超时、否定/长句/相似名称拒绝。不做模糊修正。普通表情约5秒后恢复Listening；2秒续发Listening仅维持现有固件5秒TTL，不延长会话。
- 新增`command_channel.py`：接收线程独占所有串口写，最多一个待确认命令、1.5秒回执超时、1秒指令积压拒绝、有限队列；重组被完整PCM帧隔开的IDF字符日志，解析现有`nomi: Command accepted: <cmd> (5s TTL)`。只声称设备接受指令，屏幕实际效果仍需观察，不虚构渲染确认或命令ID。
- 修改`transcribe.py`：显式`--voice-control`启用；打印真实最终结果、接受/忽略原因、发送/设备确认。停止/异常后的结果不执行；退出若已控制设备则请求idle后stream off，退出阶段不等回执，并明确说明。物理断线无法发送idle时仍靠原固件TTL回退，待实机测。
- 新`start_control.cmd`启动新模式；旧`start.cmd`保持纯转录诊断。可用`--wake-name`配置PC激活名称，仍需ASR准确转录；不购买/训练模型，不调用云端/LLM/TTS，不保存录音/转录。
- 新`package_pc.py`仅打包显式允许的PC文件和说明，ZIP为pc目录更新，不包含固件、模型、venv、录音或其它用户文件。保留已有`.venv`/`models`并合并更新，不删除整个pc目录。
- 测试：扩展`tests/test_protocol.py`，新增`tests/test_voice_control.py`。新Actions `pc-voice-control.yml`在Linux/Windows Python3.11运行控制/串口测试和真实模型公开中文样本测试，再打包PC-only更新；不为纯PC变更重刷或重新构建固件。
- 文档：新增 [PC_VOICE_CONTROL](PC_VOICE_CONTROL.md)，更新tools README、根README、ARCHITECTURE、API_CONTRACT、ROADMAP及本交接。完整修改清单见本节所列文件；API Key、Web API/Pages和八表情固件未改。

## 验证及剩余事项

- 本地Python单元14/14，覆盖未唤醒/近似词/否定/长句、最终vs临时/停止结果隔离、唤醒/表情/休息/超时/去重/续发不续期、串口序列化、PCM间插日志回执、旧/错误/缺失回执、短写、积压和异常退出。actionlint与Python语法检查通过。
- 同一真实引擎/模型的公开中文样本软件解码已通过；不是新完整物理控制测试。**Windows/实体屏幕的新唤醒→表情→超时、实际回执交错、故障回退、30分钟稳定性均待用户验收**。
- 更新包为`desktop-nomi-pc-voice-control-v0.4.1.zip`，与固件0.4.0 usb_asr兼容；当前模型和依赖锁不变。操作：停止旧程序，将ZIP内pc合并至`D:\NOMI-ASR-debug`，在pc目录执行`start_control.cmd COM3`，先唤醒，再说“开心一点”，核对最终文字/接受/发送/设备确认/实际屏幕五层。


## PC 0.4.1 最终交付记录

- 实现提交`9bbc2a7`，Windows CI按实际cmd启动器设置UTF-8的修正`3aca65e`，均推送`feat/h2-pc-voice-control`，不创建PR、不合并main。未改任何firmware文件（与6fc6723比较为空），不生成或要求重刷固件。
- 首次CI中Linux与两端14项控制测试通过，但英文区域Windows直接运行setup_model时cp1252无法打印中文，公开样本job失败。修正CI全局`PYTHONUTF8=1`与既有setup/start启动器一致，不跳过测试、不更换模型。
- [Actions运行43734112490](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43734112490)：Windows/Linux Python3.11控制单元和真实模型公开样本解码均success，PC-only package job success。此为软件验证，不是新实体语音控制通过。
- 本地更新包`tools/usb_asr/dist/desktop-nomi-pc-voice-control-v0.4.1.zip`：仅15个PC/说明/manifest文件，约20KB；source_commit=3aca65e、source_dirty=false，逐文件SHA256已校验。无固件、模型、venv或录音，部署为合并pc目录并运行start_control.cmd COM3，保留原缓存与安装环境。
- 等用户实测：最终文字→接受/忽略→串口发送→设备接受回执→实际Listening/表情→20秒待机；实际回执交错/断线/退出与长期稳定性未验收。该记录另作后续文档提交，更新包与CI源码仍为3aca65e。

---

# 0.4.0 USB板载采音与Windows中文转录

用户明确回答“是的”，同意调试阶段由Windows本地ASR，暂时放宽“仅ESP32识别”；仍不上传云端、不保存录音/转录、不执行语音表情指令。本阶段验证真实板载声音转中文，不再以预设指令标签替代任意转录。

- 从干净`docs/h2-chinese-asr-assessment` / `5fb0877`创建`feat/h2-usb-chinese-transcription`，不创建PR、不合并main、不覆盖原厂备份。
- 新增`usb_asr`固件profile（0.4.0）：独立`UsbAudioStream` CPU0/8192栈，只复用准确1.85B AudioInput与现有脸；默认关闭采音，host随机token显式启动、0.4秒心跳/约2秒租约，USB20ms短写/I2S错误或溢出即关闭。MIC1/2可选，原始PCM16LE/16kHz单声道、每320采样一帧；不启动AFE/WakeNet/MultiNet，不播放声音/执行语音动作。手动八表情/demo保留。
- USBASCII帧包含版本、token、seq、channel、覆盖元数据+640字节PCM的FNV1a32、base64；主UI不做采音/推理。PC单独读取/心跳线程、至多25帧/0.5秒队列和帧时效检查，损坏/缺帧/积压均报错停止，不把断续音频当正常转录。
- PC程序固定sherpa-onnx及core2.0.1、NumPy2.2.6、pyserial3.5，64位Python3.10–3.13；`setup.cmd`创建独立venv而非修改IDF环境，首次下载公开约21MB中文流式Zipformer2-CTC模型，归档/文件SHA256锁定。`start.cmd COM3`按Enter采音，Ctrl+C停止。Windows终端UTF-8显示真实临时/最终中文及音频/错误，模型运行阶段不联网、不访问电脑麦克风。
- 权重与轮子不放入交付ZIP或Git；交付下载/校验脚本。模型上游归档未附独立LICENSE，准确记录不补造。公开样本软件测试用上游归档0.wav，不含用户录音，不将它当实体麦克风测试。

## 文件

- 新固件：`firmware/main/stream/pcm_frame.h`、`usb_audio_stream.h/.cpp`、`firmware/sdkconfig.usb_asr`、`firmware/tests/pcm_frame_test.cpp`。
- 新PC工具：`tools/usb_asr/{protocol.py,transcribe.py,recognizer.py,setup_model.py,smoke_test.py,model.lock.json,requirements.txt,setup.cmd,start.cmd,README.md,.gitignore,tests/test_protocol.py}`。
- 调整固件main/Kconfig/CMake、build.py/profile及打包/测试、GitHub Actions四profile和host_asr公开样本job。更新README、firmware说明、架构/API/路线图、H1/H2/VOICE和本交接；完整Windows和验收见 [USB_CHINESE_TRANSCRIPTION](USB_CHINESE_TRANSCRIPTION.md)。Web前后端、GitHub Pages、密钥机制不变。

## 已执行与待验收

- Linux真实引擎2.0.1加载固定模型，通过帧解析链路流式解码公开16kHz/mono/16bit样本0.wav，281帧，得到27个中文字符的最终文本。模型加载约0.75秒，5.61秒样本总解码约0.89秒为本云端一次参考，不是Windows/实体延迟承诺。归档SHA256 `b3b309f7ce4a737195fcc6963ea19b0653a7d3401580af5ae0d3e284cbb71f0b`，样本与权重hash在model.lock.json。
- CTest5/5（含原模型/LVGL/会话及新增PCM格式/校验/边界）；Python固件审计6/6；PC协议/线程测试4/4（字节序极值、日志/旧会话、损坏/序号/声道、开始/心跳/异常停止/积压）。actionlint通过。usb_asr目标构建及无板载模型/网络/TTS入口审计已通过。
- **Windows安装/字体与驱动、真实板载声音的USB吞吐和中文效果、硬件Ctrl+C/断线/租约关闭、30分钟稳定性仍待用户实机测试**。本次有目标编译和公开音频软件证据，不声称实体链路已通过。准确“小米同学”0.3.0激活也未通过；新版本不要求唤醒、不执行表情指令。
- 下载包`desktop-nomi-h2-usb_asr.zip`包含完整四文件flash_args、host工具pc目录、版本/源码/哈希/文档。刷入后默认灰点，PC按Enter后蓝点表示传送而非认对文字；红点故障。COM3只能由一个程序占用，不同时开miniterm。可刷回旧0.3.0完整commands包恢复原试验，不整片擦除。


## 0.4.0 最终交付记录

- 源码提交`50409c2`已推送`feat/h2-usb-chinese-transcription`。本次只提交独立分支，不创建PR、不合并main；后续仅更新本交接。
- 四个profile本地最终目标构建/打包/审计通过：usb_asr app650,288字节/空模型4字节；audio1,046,704/4；benchmark1,049,952/291,150；commands1,135,008/2,681,351。最终ZIP逐文件SHA256复核通过，source_commit=50409c2、source_dirty=false。
- [Actions运行43731645973](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43731645973)六个job全部success：四profile ESP32构建、native、host_asr真实引擎与公开中文样本软件测试。usb_asr artifact ID **14168781360**。Windows与实体设备验收仍未执行。
- 可下载文件`firmware/dist/desktop-nomi-h2-usb-asr-v0.4.0.zip`（与usb_asr.zip相同，约3.9MB），内含pc工具/下载锁/说明，无权重、Python环境或WAV文件。首次`pc\setup.cmd`会下载公开依赖和约21MB模型；已安装后`pc\start.cmd COM3`按Enter开始板载采音。
- 下一步只请用户读正常中文完整句子，观察电脑终端临时/最终文本和真实音频指标，不要求先说激活词，不执行语音表情动作。异常时收集程序错误文本，不索取录音或声称已修好实体识别效果。

---

# 中文任意讲话转录：重新评估（2026-11-15）

用户实机反馈0.3.0绿点，但说“小米同学”无Listening/颜色变化；目标激活尚未验收通过。最新需求是先暂停动作扩展，串口显示**任意讲话的真实中文转录**。用户已明确选择“先重新评估”，不接受用已知词表的中文标签代替转录。

- 从干净`feat/h2-offline-voice-commands` / `8eb0734`创建独立`docs/h2-chinese-asr-assessment`。不修改固件/原厂备份、不开PR、不合并main、不调用云端或收费服务。
- 已核查README、架构/API/路线图/交接、当前CommandRecognizer与VoiceSession、AFE推理/日志路径、固定与最新ESP-SR指令能力及官方ASR引擎资料。MultiNet仍为有限指令识别，串口UTF-8支持不等于具备任意转录能力。
- 评估及建议架构见 [CHINESE_ASR_ASSESSMENT](CHINESE_ASR_ASSESSMENT.md)：尚未找到当前8MB PSRAM板上可靠实时通用中文ASR的可交付路径；建议可选择临时Windows本地ASR调试，音频必须来自ESP32自己的麦克风，USB有界帧传输，终端中文临时/最终结果，不录音落盘、不触发表情。该路径与“仅ESP32识别”冲突，**未经用户选择不实施**。
- 用户此前要求必须脱离电脑，仅在ESP32上识别；本次未自行取消此要求。替代硬件/本地主机/云端只作为评估，不下载大模型、不购买硬件、不上传录音。
- 本次只新增评估文档、更新交接；执行文档相对链接及git diff空白检查，不重复目标构建/功能测试，未生成新固件、未宣称0.3.0问题已修复。

---

# 0.3.0 独立 ESP32 语音指令交接

本次用户将目标调整为“必须脱离电脑，仅在ESP32上进行语音激活和表情指令”。新增本地有限中文指令识别，按最新需求扩展此前H2的“不接ASR”限制；不接自由转录、LLM、TTS、网络、触摸、记忆或舵机。**代码/构建交付不等于真实语音验收通过。**

## 方案与当前状态

- 从干净 `feat/h2-local-wakeword` / `0e9a58f` 创建独立 `feat/h2-offline-voice-commands`；保留原分支和原厂备份，不创建PR、不合并/推送main。
- 用户提供的0.2.1日志确认约19秒内state=2，blocks 586→2506、fetched 183→783，无超时/溢出/丢弃，RAM/PSRAM余量一致；VAD计数增长，双麦各累计5个削波点。支持“短时采音/AFE处理正常”的结论，不证明30分钟稳定性或词语识别。
- 官方固定版本MultiNet7允许配置中文拼音指令。使用 `mn7_cn`（`MN7_v1_chinese_8_0.9_0.90`）和`fst`，SHA256加入依赖锁及prepare校验；所有原组件版本不变。
- 新 `commands` profile连续运行MultiNet，应用层仅接受ID1“小米同学”激活；进入Listening/20秒窗口后，2–8表情、9/10结束待机、11原demo。普通指令续期，表现5秒后回Listening；超时待机；手动串口优先、demo隔离、epoch/时效/阈值/去重门控。**不是专用WakeNet唤醒，也不是任意语句识别。** 待机仍持续推理，功耗与误激活需测。
- 名称通过Kconfig label+无声调拼音配置；仅改label不会改变识别。硬件引脚、Codec、16kHz双麦采样、FaceModel和8种表达未改；commands关闭NS，保持VAD和50单位AFE缓存。MultiNet只在fetch任务推理，查询并重组模型chunk；UI独占表情与会话。
- 底部状态点仅commands显示：橙初始化/demo、绿就绪待机、蓝已激活、灰关闭、红故障。可脱离日志观察激活及表情反馈。
- model分区原地址0x410000扩至4MB，app仍0x10000/4MB，NVS保持；必须用完整四文件ZIP，不能只刷app，不整片擦除。

## 修改文件

- 新增：`firmware/main/voice/voice_session.h`、`command_recognizer.h/.cpp`、`firmware/sdkconfig.commands`、`firmware/tests/voice_session_test.cpp`、`docs/HARDWARE_VOICE.md`。
- 调整：`firmware/main/main.cpp`、`main/wake/wake_word_controller.h/.cpp`、`main/CMakeLists.txt`、`main/Kconfig.projbuild`、`firmware/CMakeLists.txt`、`partitions.csv`、`dependencies.lock.json`。
- 工具/回归：`firmware/scripts/prepare.py`、`build.py`、`soak.py`、`tests/CMakeLists.txt`、`tests/test_build_tools.py`、`.github/workflows/firmware.yml`（三个profile分别编译打包）。
- 文档：根README、firmware/README、ARCHITECTURE、API_CONTRACT、ROADMAP、HARDWARE_H1/H2、本交接；旧H2记录以下保留作为历史，当前策略以本节及HARDWARE_VOICE为准。前后端/Pages/密钥机制未变。

## 已执行检查与限制

- IDF5.5.4目标构建：commands、audio、benchmark均编译/模型集合/链接入口审计通过。初次commands app1,134,944字节，模型2,681,351字节，均在4MB分区内；最终尺寸以构建产物/manifest为准，静态编译不测动态堆或真实CPU。
- 原生CTest 4/4：原FaceModel、实际LVGL八表情渲染、WakeLatch/PCM、本次VoiceSession（激活/待机门控、阈值、重复、demo、旧epoch、过期/未来事件、睡眠、续期和超时）。Python构建审计5/5：模型身份/集合、profile、偏移、非法运行入口、缺失MultiNet等拒绝路径。actionlint通过，diff空白检查通过。
- Windows刷写、模型真正初始化、准确“小米同学”激活、表情指令识别、误识别/漏识别、30分钟稳定性、断开电脑独立供电均**待用户实测**。当前没有实体板可用于助手验证；不将自动测试的合成事件算语音识别成功。
- 交付ZIP `desktop-nomi-h2-commands.zip`，步骤及正负样本验收见 [HARDWARE_VOICE](HARDWARE_VOICE.md)。首次先确认绿点，然后说“小米同学”观察蓝点/Listening，再说“开心一点”；每次看实际动作，而非仅看VAD电平。


## 最终交付记录

- 代码提交`fe1c05d`，UI在消费语音事件前刷新时钟的修复`041a5b7`；均已推送`feat/h2-offline-voice-commands`。不创建PR，不合并main。
- 最终本地三个profile重新构建并打包通过：commands app **1,135,008** 字节 / 模型 **2,681,351** 字节，audio app1,046,704 / 无模型4字节，benchmark app1,049,952 / 模型291,150字节。
- 三个ZIP逐文件SHA256复核通过，manifest来源`041a5b7056e9e4f23be8840782c095cf21f3595a`、`source_dirty=false`；可配置激活label/pinyin从实际sdkconfig写入manifest，不把自定义名称硬写成默认名。
- [GitHub Actions运行43624614822](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43624614822)：native、esp32s3 audio、benchmark、commands四个job均success。三个ZIP产物已生成，commands artifact ID **14124958822**。云端成功不代表Windows刷写或实体识别通过。
- 本地可下载`firmware/dist/desktop-nomi-h2-commands-v0.3.0.zip`（与commands.zip内容相同）。本次新增真实语音验收仍待用户：绿点就绪→“小米同学”蓝点/Listening→“开心一点”Happy；再执行负样本、睡眠/超时、20次唤醒/每指令5次及30分钟稳定性。
- 本地并行构建共享`.deps`时，先单次prepare，再用`--skip-prepare`并行独立profile，避免Git稀疏checkout索引锁竞争；本次曾遇该锁竞争，复用已校验依赖重跑后通过。CI各job独立checkout，无该共享目录问题。
- Markdown相对链接与actionlint、git diff空白检查通过；本记录为后续文档提交，固件源码与CI来源仍为041a5b7。

---

# H2 本地音频与唤醒交接

更新：2026-11-15（Asia/Shanghai）。**目标“小米同学”准确模型未获得，不能宣称目标词唤醒完成。** 本阶段交付本地采集/AFE与单独“小爱同学”技术基准代码、双profile固件ZIP；H2首次用户实机音频测试已发现AFE故障；0.2.1修复构建待实机复测，真实唤醒仍未验证。

## H2 0.2.1：首次实机 AFE 停滞修复

- 用户成功刷写默认audio包，初始化日志确认ES7210/ES8311打开、I2S 16kHz/16bit/stereo和AFE管线建立；随后`blocks=521 fetched=5 state=4`。重新初始化仍出现FEED ring full/FETCH empty及`AFE fetch stalled`。不能将初始化成功当作麦克风、AFE持续运行或唤醒验收通过。
- 对固定ESP-SR 2.0.1单麦预编译库的feed/create/VAD实现作反汇编核对：ring单位为1024字节，VAD保留speech+delay历史，feed满时返回0。原5单位5120字节低于128+128ms的8192字节历史需求，是明确的容量配置缺陷，与用户故障吻合；此前仅检查feed<0也漏报丢帧。
- 修改`firmware/main/wake/wake_word_controller.cpp`：ring=50（51200字节有界缓冲，MORE_PSRAM保持）、显式VAD speech/delay各128ms，新增`AFE_BUFFER`配置日志；feed<=0立即停止本轮。未改引脚、采样率、表情、串口demo或模型。
- `firmware/CMakeLists.txt`版本0.2.1；同步`docs/HARDWARE_H2.md`及本交接。不增加组件、不购买模型，不上传原始日志/音频。
- 本地原生CTest 3/3、Python构建审计4/4通过；audio目标编译/模型与链接入口审计通过。benchmark目标编译/模型及链接入口审计也通过。修复提交`db1090e`已推送独立H2分支；GitHub Actions运行43622526392已启动，记录时仍进行中，尚不宣称远端通过。本地两个ZIP的manifest均记录该提交且source_dirty=false。
- 复测：刷写0.2.1 audio包后确认`AFE_BUFFER ring_units=50`，观察开机、说话/安静与`status`，至少间隔10秒采样两次；state=2、blocks/fetched均持续增长、无full/stalled/新增overflow才可继续30分钟测试。重复off/on/reinit及demo回归。当前没有实体修复通过证据；准确“小米同学”模型依旧不可用。

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
- 修复提交 `192687d` 已推送；真实Git ownership拒绝在本地通过GIT_TEST_ASSUME_DIFFERENT_OWNER复现，精确仓库作用域查询成功。I²S修正为 `d335bf7`。
- 最新 [Actions运行43619895196](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/actions/runs/43619895196)，source=192687dd077c4d8a66086f426962b16dbdd5bfa3：**native、esp32s3(audio)、esp32s3(benchmark)三项全部success**，两个ZIP均已上传且未过期。
- 云端下载产物：desktop-nomi-h2-audio（artifact14123896819）、desktop-nomi-h2-benchmark（artifact14123593493）；进入上述成功运行的Artifacts下载。ZIP/manifest/source_commit与本次对应，不依赖创建PR。产物的二进制大小/哈希可能因编译环境/路径与本地不同，以所下载manifest为准。
- 本地两个ZIP已在干净source=192687d状态重新构建/打包，逐文件哈希与词身份验证通过；最终交付说明另作文档提交，不改变固件代码。
- 按用户要求未创建PR、未合并main，原厂备份不在本工作区。

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
