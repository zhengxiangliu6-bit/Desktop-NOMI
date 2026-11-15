# USB板载麦克风与Windows本地中文转录（0.4.0）

> 0.4.2修复见[当前语音控制说明](PC_VOICE_CONTROL.md)：固件与PC成对升级，使用编号/校验回执和设备端20秒聆听会话，取消电脑每2秒刷新；原模型/依赖不变，实体修复待复测。以下0.4.0/0.4.1描述保留历史范围。

## 阶段目的

用户已明确同意临时由Windows本地运行ASR。先暂停语音表情指令，验证**设备自己麦克风的真实声音能否转为任意中文句子**。电脑显示实际ASR文本，不把预设指令标签当转录，不用电脑麦克风替代。

这不是ESP32独立ASR版本。串口传来的是板载PCM，由Windows程序解码并显示中文；不把结果冒称为ESP32识别输出。现有8种表情及手动串口demo仍保留，语音不会触发动作、LLM或TTS。

## Windows：三步开始

1. 下载并解压`desktop-nomi-h2-usb_asr.zip`到例如`D:\NOMI-ASR-debug`。确认`flash_args`直接位于该目录，内有`pc`与`docs`。原厂备份继续保留，勿放在备份目录内解压。关闭miniterm：Ctrl+]。
2. 在ESP-IDF5.5.4终端执行：

```bat
cd /d D:\NOMI-ASR-debug
python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
pc\setup.cmd
```

完整写入同包bootloader/表/app/空模型占位；不要只刷app，不运行erase_flash。首次setup需联网下载固定Python依赖和约21MB公开模型，只下载模型，不上传音频。它创建`pc\.venv`，不向ESP-IDF现有环境安装依赖。要求64位Python3.10–3.13；不支持时先报告错误，不自动替换用户Python。

3. setup成功后：

```bat
pc\start.cmd COM3
```

看到“按Enter开始”后按Enter，用正常音量说完整句子，例如“今天我想测试一下中文语音识别”，停顿约1–2秒观察最终结果。**不必先说唤醒词。** Ctrl+C停止，程序发送stream off并关闭串口。不同时开miniterm/其它COM3软件。

第二次使用不需要setup，直接start。模型和依赖安装完成后可断网运行。Windows终端UTF-8由cmd脚本配置。出现临时结果修订、无标点、专有名称错字等可能是小模型能力限制，不能承诺100%准确或逐字零延迟。

## 看什么结果

- `[临时] 中文…`：讲话中的暂定文本，后续可能修改。
- `[最终] 中文…`：停顿或停止后得到的实际结果。
- `[音频] 连续帧=… MIC1 peak=… rms=… 削波=… 队列=…`：每约2秒统计板载音频；不是转录。
- `[状态] 本段无识别文字`：本轮解码无文字，不伪造用户讲话、不断言没有声音。
- `[异常] …`：采集、校验、序号、USB、超时或电脑积压异常，停止采音，不继续识别不连续音频。

屏幕状态点：灰=采音关闭，橙=音频初始化，蓝=正在传送，红=采音/USB异常。**蓝点不表示认对了文字**，中文结果以电脑终端实际输出为准。识别不驱动脸，避免把这次测试与语音指令混在一起。

如无中文但电平有变化，正常音量读较完整句子，查看临时/最终；电平接近静音则尝试`pc\start.cmd COM3 --mic 2`单独对比第二路板载麦克风。增大音量导致持续削波也会影响识别。`--threads 4`可测更多CPU线程，效果由电脑决定。

## 隐私与停止行为

- 默认不开机采音。只有用户启动电脑程序并按Enter，程序发带随机会话token的`stream on`后才打开ES7210。
- Windows线程每0.4秒发送同token心跳；ESP32超过约2秒未收到会话心跳则停止，或在USB发送超时/I2S错误/溢出时停止。I2S读最多100ms、USB写最多20ms；实际关闭时间还含Codec清理，需实机确认，不承诺精确2秒。
- Ctrl+C/接收线程错误发送`stream off`。杀进程、断线或串口异常时由租约/有限写超时兜底；重开程序才开始新会话。未获请求不录音，关闭后不继续后台识别。
- 不创建音频/转录文件、不写数据库；只在当前进程内存与终端显示。模型下载/依赖安装会写公开模型和软件缓存，不含用户录音。系统或操作者自行进行的终端录制/重定向不由本程序创建。
- 运行时无云服务、无API Key、无HTTP上传；设备也不初始化Wi-Fi/BLE。模型初始化先于串口采音，避免加载模型期间积压真实音频。

## 传输和模块

硬件保持Waveshare1.85B同板官方引脚及ES7210/ES8311路径，见[HARDWARE_H2](HARDWARE_H2.md)。16kHz/PCM16双麦采集，选择MIC1（可MIC2）转单声道；每320采样/20ms生成一帧。此次使用原始PCM，不通过旧AFE/MultiNet，以便先隔离采音与通用ASR链路。PA始终关闭，不播放声音。

`UsbAudioStream`独立任务CPU0/8192栈，主UI仍单独拥有FaceModel/LVGL。两个任务通过原子开关/会话/心跳状态交互。固件只做采音和USB，不装载语音模型、不启动旧WakeWordController采音或识别。

帧为ASCII行：`@NOMI1 token_hex seq_hex channel hash_hex base64_PCM`。token和序号各uint32，channel=1/2，payload固定640字节有符号PCM16LE；FNV-1a32覆盖token/seq的小端字节、channel单字节和PCM。每帧前后换行，接收端忽略无关日志/旧会话，只接受新会话seq0起连续帧、正确长度和校验。FNV是传输检错而非密码认证。

这条链路使用原生USB Serial/JTAG虚拟串口。虽然软件打开COM3时参数115200，实际USB传输速率不由UART波特率上限决定；Base64后约45KB/s，真实Windows USB吞吐/积压待实测。不能拿真正115200 UART传输该PCM。任何短写/帧间断/积压均停止，不悄悄降采样或丢帧。

电脑读取/心跳线程与ASR分离，输入队列上限25帧（0.5秒），额外检查帧等待时间<=0.5秒。线程退出或异常停止；解码器自己的上下文和端点判断仍可能增加文字显示延迟。端点识别和主线程在CPU运行，不访问电脑麦克风。

## 固定版本与模型

- 固件0.4.0 / ESP-IDF5.5.4；原硬件、驱动、LVGL/Codec依赖版本不变，板载8MB PSRAM/16MB Flash。保留0.3.0的app4MB、model4MB布局；此profile模型分区写4字节空占位。
- Windows：sherpa-onnx2.0.1及其core2.0.1、NumPy2.2.6、pyserial3.5，CPU执行；创建单独venv。
- 中文流式Zipformer2-CTC小模型：`sherpa-onnx-streaming-zipformer-small-ctc-zh-int8-2025-04-01`。归档21,264,113字节，SHA256 `b3b309f7ce4a737195fcc6963ea19b0653a7d3401580af5ae0d3e284cbb71f0b`；模型/词表的独立SHA256在`tools/usb_asr/model.lock.json`。
- [模型官方发布](https://github.com/k2-fsa/sherpa-onnx/releases/tag/asr-models)、[引擎文档](https://k2-fsa.github.io/sherpa/onnx/)。交付包含下载/校验脚本，不打包权重或Python轮子；上游权重归档未包含独立LICENSE，记录此限制，不补造模型许可。

## 测试与尚未验证

云端Linux已用真实sherpa-onnx2.0.1加载上述模型，并流式解码同包公开`test_wavs/0.wav`（16kHz/单声道/16bit，约5.61秒），获得正常中文最终文本。此为**公开音频样本软件测试**，不是本板用户语音或Windows实测，不据此承诺“小米同学”准确率。

自动化覆盖C++帧编码/极值/边界及与Python一致的校验向量；Python覆盖UTF-8日志隔离、旧会话、帧损坏/错长度/丢帧/重复/声道、启动/心跳/异常关闭和积压停止；现有FaceModel/LVGL/VoiceSession回归保留。

真实硬件验收：

1. 新固件上电灰点、不运行PC程序不采音；程序按Enter后蓝点且连续帧增长。
2. 读至少5句不同中文（不局限指令词表），观察临时及最终文本，记录错字/漏字/延迟，不以预设标签替代转录。
3. 安静/正常讲话/短促声音对比电平，避免持续削波；对比MIC1/MIC2，确认声音来自板载麦克风。
4. Ctrl+C后灰点/STREAM_STOPPED；关闭进程、拔USB、占用COM端口、电脑过载等场景明确停机/报错，重开后新token从seq0开始。模拟丢帧测试通过不等于实体断线测试通过。
5. 断网测试仅运行已安装程序，仍可中文转录；无录音/转录落盘。持续30分钟检查RAM、温度、连续帧、显示和延迟。
6. 手动表情/demo仍能正常显示，任意说话不切换表情。本次不是最终独立语音方案，离开Windows只剩脸和安全关闭的麦克风。

**Windows安装/字符显示、实际USB吞吐/时序、板载声音的识别效果、停止与断线行为、30分钟稳定性均待用户实测。** 原厂备份不动，恢复见[HARDWARE_H1](HARDWARE_H1.md)；可刷回原0.3.0完整commands ZIP恢复旧独立指令试验，不需要整片擦除。
