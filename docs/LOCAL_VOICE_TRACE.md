# 0.6.3：板上模型自检、音频追踪与资源诊断

本版用于定位0.6.2仍未激活的问题，不是已证明修复了“小米同学”。用户0.60实体日志显示模型DETECTED=0、TIMEOUT持续增长，采音/AFE/推理帧继续、无溢出；所以不是会话拒绝，也没有证据表明卡死。旧日志只有任务栈余量，没有堆余量/模型耗时，不能排除处理路径问题或把模型文件大小当作实际RAM消耗。

## 有证据的修正与新增诊断

1. 固定ESP-SR头文件/AFE文档明确要求将非空vad_cache接在data前，补回截断语音。旧代码忽略它。新代码校验长度/对齐/指针，按cache→data顺序送MultiNet，记录restored_cache_samples。该遗漏可以造成短指令开头缺失，仍需实体数据证明是否是本次唯一原因；未改变采样率/引脚/用户词表，不盲降门槛。
2. 开机在板上运行官方公开PCM“打开空调”与静音对照，直接送同一MultiNet。临时测试词表只用于这段自检，不执行表情/设备动作、不播放声音；随后恢复原小米同学及14表情词表，并打印实际模型词表。自检失败则红色Fault，不伪装绿色可用。`MN_SELFTEST PASS`只验证模型+库+测试输入，不代表麦克风/AFE/激活词通过。
3. `MN_RUNTIME`报告selftest、推理调用墙钟last/mean/max微秒、frame_budget_us和over_budget。均值每32调用更新，墙钟包括被调度等待，不等于纯CPU百分比。`HEAP`报告内部与PSRAM free/largest、最小总堆；任务stack_free仍保留。`AFE_PCM`给出实际送模型音频的电平/零块和恢复缓存样本，不能只凭原MIC电平推断模型输入正常。
4. 新可选串口追踪：CH1原始MIC1，CH2正常识别时按cache→data补全的AFE流。二者PCM16LE/16kHz/mono，独立连续20ms帧。VAD/AFE会引入延迟与静音处理，两流不是逐样本同步文件。播放保护期间CH1仍是真实采音，CH2仅为被屏蔽期间AFE输出、带guard标志，模型不使用这些保护帧。

## Windows：电脑仅接收，绝不运行识别模型

退出miniterm和旧ASR程序。先解压本次完整commands包到`D:\NOMI-OFFLINE-063`，用ESP-IDF终端按flash_args烧录，保留原备份，不整片擦除。开机自检需数秒，屏幕继续渲染；不要在橙色初始化期间反复喊。

```bat
cd /d D:\NOMI-OFFLINE-063
python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
python debug\monitor.py --port COM3 --seconds 20 --threshold 60
```

现有Python已经能运行esptool/miniterm，所需pyserial已具备；工具只用pyserial和标准库，不装sherpa/ASR、不上传音频。按Enter才开始串口音频传输（设备本地识别本身开机就运行），20秒自动关闭追踪，Ctrl+C可提前停。默认不保存音频或转录。

调试程序显示原始音频/AFE各自有效帧、peak/RMS以及ESP32日志；`@NRES1 ... label=...`是模型返回的有限配置标签，不是任意讲话的中文转录。模型没返回指令时只报告detected=0/超时，不编造文字。电脑没有“重新识别”的隐藏步骤。

若双路传输发生TRACE_STOPPED背压，可加`--source raw`或`--source afe`分别采集，不需要再烧录，也不改变设备本地识别。需要自己试听两路音频时，**显式**指定仓库外目录：

```bat
python debug\monitor.py --port COM3 --seconds 20 --threshold 60 --record-dir D:\NOMI-capture-063
```

会创建`raw-mic1.wav`、`afe-output.wav`，拒绝覆盖已有同名文件；退出后双击WAV试听。录音只存在用户指定的电脑目录，设备不存，不自动上传；不指定参数则不会生成文件。传输损坏/丢帧会报错，已有WAV可能是未完成片段，不补静音假装完整。录音期间能收到身边其它声音，按Enter前自行选择合适环境。

## 数据如何走

`麦克风 → CH1串口PCM → AFE/VAD缓存恢复 → CH2串口PCM + MultiNet → ESP32候选/动作日志`。

音频不直接打印成中文：终端无法把PCM当可听声音，接收工具解包后显示电平，可选写WAV试听。完整音频在串口中是`@NTRC1 token seq channel flags checksum base64`，和旧PC识别的`@NOMI2`区分。候选标签用`@NRES1 id/label/score/gate/source`一次驱动写入，避免音频帧插入中文日志中间；这是诊断输出，不作为控制回执。音频帧FNV校验覆盖token/序号/通道/flags/PCM，通道独立序号；512等AFE块累计成320样本，不在块边界插零凑块或丢样（停止时不足20ms的尾部不发送）。工具校验后才显示/写文件。

追踪默认关闭，显式trace on才开启（可选channels掩码1=raw、2=AFE、3=双路）；每次开启使用新token；工具自动生成。需要0.5秒心跳，断线2秒停止追踪；每次USB写等待≤2个RTOS tick（驱动先等互斥再等环形缓冲，调度还可增加墙钟时间），背压则停止追踪，本地识别继续，不让慢电脑无限卡住推理。停止追踪不关设备麦克风（本地识别仍运行）；需要停止本地采音用wake off。

## 需要回传的最少证据

- `MN_SELFTEST PASS/FAIL`或`MN_RUNTIME selftest=...`。若FAIL，先停止喊词，分别看reference/silence：reference=0表示官方直送样本未命中，silence=0表示静音误报；不能直接等同内存不足。先查模型/词表/库，而不是继续调用户发音。
- 原始MIC1与AFE音频都有电平吗？`AFE_PCM`是否大量zero_chunks，restored_cache_samples是否增长？两路试听能否听清同一句？
- `MN_RUNTIME`推理平均/最大耗时与frame_budget_us比较；`HEAP` free/largest；`MN_DIAGNOSTIC`检测/超时。
- 正常说1次“小米同学”和1次“开心一点”，记录实际候选和会话接受/忽略。未唤醒的普通指令只作候选诊断，不执行。完成后工具自动停止，保留最后状态。

只有这些信息才能区分模型本身、采音、AFE丢头、分数/词表与性能问题。自检PASS仍不代表准确的小米同学专用WakeNet已经获得；现在仍是MultiNet有限匹配，不是任意中文ASR。旧0.6.2/0.6.1包可回退，原厂备份保留。

## 0.6.4：默认词表对照与音频诊断解耦

0.6.3用户实测：`silence=1 reference=0`，自检在开麦前失败，按旧设计停掉了整个采音链；所以blocks/raw_frames全0并不说明麦克风坏。最低总空闲堆约5.28MB，失败后PSRAM回到约8MB；后者是清理后的值，不能当推理运行期余量。没有内存分配失败/重启证据，不把结果归因“模型太大”。

已通过固定libmultinet.a反汇编调用关系核对：MN7 model_create会调用esp_mn_commands_alloc，model_destroy会调用esp_mn_commands_free。旧应用额外alloc/free重复操作了库的词表；现已去掉。日志最后“not initialized”是清理阶段问题，不能单凭它证明检测失败根因已经找到。

新自检顺序：

1. `factory_untouched`：create后的原厂默认词表，不先alloc/clear/update/改门槛，直接送官方PCM；固定commands_cn.txt的“打开空调”是ID25。
2. `custom_reference`：使用库已经创建的词表，更新为上游示例的打开/关闭空调两条测试词、预期ID1、门槛0.60，再送相同PCM。
3. 静音对照，然后恢复实际17个指令。每一步输出pass/expected/got/score/state/frames，参考输入补齐到完整块并附2秒静音；模型窗口恢复官方示例的6000ms。默认与定制两条都通过且静音无误报才允许本地动作。

这两条测试仍需在设备上执行；编译和原生逻辑测试不等于模型实测通过。若factory成功而custom失败，重点看动态词表；若二者均失败，才继续查默认模型/库/推理路径，不先责怪用户讲话或麦克风。

即使模型失败，本版仍启动独立的麦克风/AFE音频诊断，状态点保持红色、`DETECTOR ready=0`，没有候选也不执行动作；raw/AFE音频可按之前monitor命令接收或显式录WAV。音频诊断不是绕过模型自检执行指令。若音频初始化本身失败，则仍停止采音并报告实际硬件错误。

## 0.6.5 从 Windows 源码目录迭代

本轮实体对照中默认词表识别 ID25 成功，运行时改词表后同一音频没有结果。commands 构建现在将 NOMI 词表写入模型分区，启动时核对每个 ID 和拼音，并直接测试打包词表。ID25 只用于验证，业务会话不接受它。实体通过标记为 `MN_REFERENCE stage=bundled_table pass=1`。

在 ESP-IDF 5.5.4 命令窗口执行以下命令。第一次克隆后，同目录可用 `git pull --ff-only` 更新，并保留增量构建缓存。

```bat
if not exist D:\codex mkdir D:\codex
cd /d D:\codex
git clone --branch fix/h3-bundled-command-table https://github.com/zhengxiangliu6-bit/Desktop-NOMI.git Desktop-NOMI
cd Desktop-NOMI
python firmware\scripts\build.py --profile commands
cd firmware\build-commands
python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
```

有私人回复素材时，在构建命令加 `--reply-assets` 指向之前导入的目录。源码的默认音频是项目占位音。用仓库的 build.py 生成模型分区后再按 flash_args 写入程序和模型。
