# 独立 ESP32 本地语音指令（0.3.0）

> 当前新增0.4.0 [USB中文转录调试版](USB_CHINESE_TRANSCRIPTION.md)：用户已同意Windows本地ASR；板载麦克风经USB传音频，电脑显示实际中文，暂不执行语音表情动作。旧0.3.0有限指令版本保留，不能视为任意中文转录或已通过激活验收。

## 本阶段目标与方案调整

用户最新要求：**必须脱离电脑，仅在 ESP32-S3 上实现语音激活和表情指令**。本版本在已有 H2 音频接入之上增加有限中文指令识别，取代“只有音频电平、无法验证词语”的验收方式。电脑仅用于烧录/可选日志，运行时只需合适 USB 电源。

默认说“小米同学”，观察 Listening 表情，然后说下表指令。**实现是 MultiNet7 连续指令识别 + 应用层激活门控，不是专用“小米同学”WakeNet 模型。** 所用通用中文模型支持词表配置，不需为每条指令单独购买/训练模型。它也不是自由对话或任意语句转文字。

旧 H2 文档“本阶段不接 ASR”的范围被本次用户语音指令需求扩展为本地有限指令识别；LLM、TTS、云端、触摸、舵机、记忆仍不接入。独立 `commands` profile，保留 `audio` 和 `benchmark` 诊断版本。

官方推荐先 WakeNet 再 MultiNet。为支持用户指定的名称，本实验版在待机也连续运行 MultiNet（每4秒解码超时会重置后继续），只把词表中激活ID作为唤醒入口。**不是低功耗唤醒，误激活率/漏识别率未知**，不能引用官方带 WakeNet 的效果数据代替实测。噪声、电视、相似发音可能误匹配，必须执行下方负样本测试。

屏幕底部增加8像素状态点：橙色=初始化或demo期间、绿色=待机识别就绪、蓝色=已激活可接收指令、灰色=采音关闭、红色=音频/识别故障。Listening及指令表情是动作反馈；指示点表示能否继续说指令，不用一直打开串口。

## 直接可验证的操作

| 说的话 | 前提 | 屏幕/事件 |
| --- | --- | --- |
| 小米同学 | 待机或已激活 | Listening；`WAKE_WORD_DETECTED source=multinet_command` |
| 开心一点 | 激活后20秒内 | Happy；`VOICE_COMMAND_ACCEPTED id=2 action=happy` |
| 难过一点 | 同上 | Sad，id=3 |
| 眨一下眼 | 同上 | Blink，id=4 |
| 好奇一点 | 同上 | Curious，id=5 |
| 思考一下 | 同上 | Thinking，id=6 |
| 认真听讲 | 同上 | Listening，id=7 |
| 说话表情 | 同上 | Speaking动画（不播放语音），id=8 |
| 回到待机 | 同上 | Idle并结束本轮，`VOICE_SLEEP id=9` |
| 休息一下 | 同上 | Idle并结束本轮，`VOICE_SLEEP id=10` |
| 表情演示 | 同上 | 原有八表情demo一轮，id=11；期间忽略语音，完成后待机 |

先说完整激活词，看到 Listening 后再单独说指令，第一版不承诺一句“小米同学开心一点”执行两步。严格按上表完整短语测试，不承诺“高兴点”等未配置同义词。指令效果约5秒，随后仍在窗口内会回到 Listening；接受普通指令会续期20秒，无后续指令则自动待机并记录 `VOICE_SESSION_TIMEOUT`。待机时表情指令不执行。

阈值0.90同时用于模型和UI门控；重复同ID在1.2秒内忽略。20秒是可接收命令窗口，不代表连续保存20秒录音。原始PCM仅在有界RAM/PSRAM处理，不写文件，不输出转录，不初始化Wi-Fi/BLE/HTTP，不上传音频。固件无声音应答，用现有表情确认。

## 硬件、资源和固定版本

使用与已运行H2相同的1.85B ES7210双麦、ES8311静音时钟路径及全部引脚，详见 [HARDWARE_H2](HARDWARE_H2.md)。保持16kHz/PCM16/stereo采集，MIC1转单声道送AFE，MIC2仅测电平；不新增板型或更改GPIO。

- ESP-IDF 5.5.4，ESP-SR 2.0.1（upstream v2.0.0 / `1c0503e7e2dc5e1ecb2fd3da0a5d7e51e3574842`），其它组件保持 `firmware/dependencies.lock.json` 固定版本。
- 模型 `mn7_cn`，信息 `MN7_v1_chinese_8_0.9_0.90`，配套 `fst`；所有文件SHA256记录在依赖锁，由prepare逐一校验。动态清空默认指令，安装项目词表并检查update错误，失败不进入可识别状态。
- [官方同版本中文指令文档](https://github.com/espressif/esp-sr/blob/1c0503e7e2dc5e1ecb2fd3da0a5d7e51e3574842/docs/zh_CN/speech_command_recognition/README.rst)；[官方资源基准](https://github.com/espressif/esp-sr/blob/1c0503e7e2dc5e1ecb2fd3da0a5d7e51e3574842/docs/en/benchmark/README.rst) 给出S3 MultiNet7约18KB RAM、2920KB PSRAM、11ms/32ms帧。这是官方参考，**不是本板本次测量值**。
- AFE单麦LOW_COST/MORE_PSRAM；无AEC/SE/AGC/WakeNet，WebRTC VAD开启，commands版关闭NS以避免前处理失真。保持0.2.1修复的50单位ringbuffer（51200字节）；VAD speech/delay各128ms。
- 保留capture CPU0/8192栈、fetch CPU1/8192栈与主显示CPU1。MultiNet在fetch worker执行，不在主显示任务推理；调用其查询得到的chunk，有限重组缓冲上限1024采样，不假定AFE/MN块长相同。
- 16MB Flash，app仍0x10000/4MB；模型仍0x410000，**分区扩大为4MB**（原H2为2MB），无NVS偏移变化，无整片擦除。现有H2 app/表/模型需一并刷新，禁止仅替换app。实际ZIP偏移以`flash_args`为准。
- status保留RAM、PSRAM、任务运行累计时间、栈余量、显示最大帧间隔，增加`MULTINET frames`与`VOICE_SESSION active`。初始化成功记录`VOICE_READY`仅代表模型/词表装载成功，不证明听对了话。

## 自定义名称

从源码首次构建前，在 `firmware/sdkconfig.commands` 同时设置：

```text
CONFIG_NOMI_VOICE_WAKE_LABEL="小米同学"
CONFIG_NOMI_VOICE_WAKE_PINYIN="xiao mi tong xue"
```

若已经构建，defaults不会覆盖已有配置。应在firmware目录运行 `idf.py -B build-commands -D SDKCONFIG=sdkconfig.commands.local menuconfig`，修改本项目的Activation phrase label/pinyin后保存，再运行构建脚本。

label只用于显示/日志；实际识别由无声调、空格分隔的小写拼音决定。改名需修改拼音并重新构建烧录，不能只改label；第一版无触摸/网页改名功能。模型词汇/发音覆盖有限，词条不合法时初始化失败，不伪装“自定义成功”。词表在`firmware/main/voice/voice_session.h`，id=1固定为激活，2–11为操作。新增/更名后重新做正负样本验收，不能保证任意名字效果。

## 构建与 Windows 烧录

ESP-IDF5.5.4终端，从仓库根目录：

```bat
python firmware\scripts\build.py --profile commands --package
```

输出`firmware/dist/desktop-nomi-h2-commands.zip`；GitHub Actions额外构建commands，不删除原两个profile。ZIP提供完整四文件、flash_args、版本/提交/哈希、许可和文档。

已完成并校验的原厂备份继续保留，恢复按 [HARDWARE_H1](HARDWARE_H1.md)。请勿覆盖 `D:\NOMI-backup`。将新ZIP解压至独立目录，确认目录中有flash_args、desktop_nomi_h2.bin、srmodels。Ctrl+]关闭miniterm后，在ESP-IDF终端执行（假设解压目录如下，COM3为本会话设备）：

```bat
cd /d D:\NOMI-voice-commands
python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
python -m serial.tools.miniterm COM3 115200 --eol CRLF
```

必须烧录同一个ZIP中的bootloader、分区表、app、模型；不运行erase_flash。串口115200，Ctrl+]退出；`status`查看信息，`wake off`停止采集与推理，`wake on`/`wake reinit`重建，`demo`及八种英文指令保持可用。普通串口表情/demo/off/on/reinit会结束当前语音会话，防止语音覆盖手动操作；status不改变会话。

## 实机验收：判断“听对了没有”

1. 开机有脸且自然眨眼；日志有`VOICE_READY model=mn7_cn`（字段顺序以实际日志为准），无重启/分配失败。尚未激活直接说“开心一点”不应改变表情。
2. 安静、约30–50cm正常音量，说“小米同学”，应出现Listening与激活事件；随后逐条说上表短语，核对屏幕**及对应ID/action**。只出现电平/VAD变化不算成功。不能把主动串口输入模拟的事件算语音成功。
3. 激活20次、每个表情至少5次；记录目标次数、正确次数、漏识别、错ID、到屏幕响应的大致时间。未执行的保留“待测”，不自动填通过。首次用于收集效果，不宣称产品级准确率。
4. 负样本：安静、正常无关聊天、背景音乐、“小爱同学”“小明同学”等相近短语；分别待机/激活测试。待机无关输入应不激活，激活后无关输入应不执行表情。记录误触发次数/测试分钟数。词表匹配可能误识别，不能保证负样本零误报。
5. “休息一下”后不激活直接说表情应无效；无输入20秒自动待机；重复唤醒、连续不同表情、语音demo/串口demo期间忽略语音，结束后重新唤醒。off时不应产生新识别事件；on/reinit后应恢复且旧队列事件不触发表情。
6. 连续运行30分钟，每5分钟status，blocks/fetched/MULTINET frames增长，timeouts/overflows/dropped无稳定期新增，剩余内存无持续下降，栈余量与帧间隔可接受；正常音量时削波不持续增长。记录实际CPU差分和重启次数。
7. 用普通USB电源启动，完全不运行电脑程序，重复激活和表情指令，才算独立运行通过。Windows烧录、模型运行、真实激活准确率、30分钟稳定性、脱机供电均需实机结果。

## 验证状态

H1八表情、H2 0.2.1采音/AFE短时持续运行已有用户证据：blocks/fetched持续增长、无超时溢出、两次内存一致。未获得H2长时稳定性结果。

**本次0.3.0新增的MultiNet模型加载、准确“小米同学”指令激活、表情语音识别、效果/资源及独立供电均未在实体硬件上验证。** 编译/自动化测试不能代替上述验收。专用“小米同学”WakeNet模型仍未获得；本版通过通用模型的词表匹配实现该名称，不能把二者写成同一技术结论。
