> **0.6.2校准诊断版**：0.6.1用户日志显示采音/AFE/MultiNet帧持续增加，但未报告激活。现有证据不能确定根因；旧代码模型与UI两层0.90门槛是待检验因素，不是已证明原因。新版默认仍0.90，新增`voice threshold 60`临时设置模型和会话门槛到0.60（不是60%准确率），在推理任务应用并清旧decoder；重启恢复0.90，wake reinit沿用本轮设置。范围30–95，不自动保存。改变门槛会结束当前会话，等待`VOICE_THRESHOLD_APPLIED`再说话。

> 调试输出：`VOICE_CANDIDATE`只打印模型实际DETECTED时最高候选的配置ID/标签/分数（限每秒一条），不是任意中文转录；没有结果时不编造候选。`wake status`新增`MN_DIAGNOSTIC`的detected/timeouts/below_gate/last_id/last_score/active_threshold/requested。last_id/last_score是历史最后候选，不能当成本句识别。

> 本次测试：烧录专门的0.6.2私有声音诊断包→打开miniterm→`voice threshold 60`→确认APPLIED→说一次“小米同学”→`wake status`。回报这段候选/接受或拒绝/诊断计数。不要自行反复降到很低门槛；若能激活还需安静、旁人讲话和近似词负样本测试，再决定正式门槛。本版用于校准定位，不宣称已修好实体唤醒。用户声音仍只在私有构建，公开CI用默认素材。

> **0.6.1支持私有音频构建**：不再需要把个人音频写入Git源码。先用`python firmware/scripts/import_reply.py 路径/okay.wav --output-dir D:/NOMI-private-reply`，再用`python firmware/scripts/build.py --profile commands --reply-assets D:/NOMI-private-reply --package`。目录可放仓库外，原文件不上传；所有素材校验及WAV试听仍执行。GitHub CI默认使用仓库占位音频，**不含用户上传声音**；用户定制包单独交付。下方原地替换方式仍可用于自己管理的源码。

# 0.6.0：ESP32本地指令 → 表情 → 固定回复

仅适用于Waveshare ESP32-S3-Touch-LCD-1.85B / ESP-IDF5.5.4 /16MB Flash /8MB PSRAM。独立`commands`包开机采音，在ESP32本地MultiNet7识别有限中文指令，切换14表情并由ES8311播放固定回复。不需要运行Windows程序、电脑ASR、Wi-Fi、API Key、ASR/LLM/TTS服务；串口只是可选日志。固件软件构建通过不代表实机识别/声音通过。

本版保留0.5.1现有“好的”作为功能测试占位音频，用户已表示不喜欢这个音色；没有将它再标成音质改善交付。用户自行生成的替代音频尚未收到。可以先发WAV/MP3，由开发方转换打包；或按下方自行替换。所有接受的动作目前共用一段`okay.pcm`，没有实现每条指令独立音色/音频。

## 识别能力与指令

这是有限词表识别（返回指令ID），不是任意中文转文字。激活名称是“小米同学”的MultiNet连续指令匹配，**不是已获得该词专用WakeNet模型**。实际准确度/误激活必须测，不能把编译成功写成唤醒词实机验收。PC的“回到待基”别名未加入，本次也不修改PC词表。

1. 开机初始化：状态点橙色；检测可用后绿色。
2. 说“小米同学”：Listening/蓝色，播一次固定回复。
3. 播放及保护时状态点橙色，请暂不说话。恢复蓝色后再说一条表中短语。
4. 明确指令被接受：展示表情并回复一次；5秒表情后会话未满20秒则恢复Listening，20秒无接受指令后idle/绿色。
5. 已激活再次叫名称只续期，不重置脸/重复回应；未激活普通表情不执行。“休息一下”/“回到待机”结束会话并回应，自动超时不回应。

| 说出的短语（本地词表） | 动作 |
| --- | --- |
| 开心一点 | happy |
| 难过一点 | sad |
| 眨一下眼 | blink |
| 好奇一点 | curious |
| 思考一下 | thinking |
| 认真听讲 | listening |
| 说话表情 | speaking |
| 生气一下 | angry |
| 惊讶一下 | surprised |
| 困倦一下 | sleepy |
| 单眼眨眼 | wink |
| 喜欢表情 | love |
| 疑惑一下 | confused |
| 回到待机 / 休息一下 | idle并结束会话 |
| 表情演示 | demo，14项每项3秒后idle |

先按表格原句分开说，不把自由中文或PC全部语音别名当成本地词表；识别成功ID及原句在VOICE_COMMAND日志，不能说这些日志是逐字转录。

## Windows烧录（不编译即可使用完整包）

退出PC语音程序、关闭miniterm；不要同时占用COM3。下载0.6.0 **commands**包（不是usb_asr/audio/benchmark），解压到例如`D:\NOMI-OFFLINE-060`，确认flash_args、srmodels/srmodels.bin存在。首次必须按包内全部偏移烧录模型和程序，不能只替换app；保留已验证原厂备份，不整片擦除。

```bat
cd /d D:\NOMI-OFFLINE-060
python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
```

重启后直接工作，**不运行start_control.cmd或start.cmd**。用合适USB电源供电也可运行；首次还需连接电脑观察日志做验收，不等于电脑参与识别。

可选日志：`python -m serial.tools.miniterm COM3 115200 --eol CRLF`，Ctrl+]退出。看`VOICE_READY`、`WAKE_WORD_DETECTED`、`VOICE_COMMAND_ACCEPTED`、`LOCAL_REPLY_START`、`LOCAL_REPLY_DONE; VOICE_LISTEN_READY`。DONE只说明数字输出/保护结束，实际声音以耳听为准。`wake off`停止采音、关闭播放，`wake reinit`重新初始化；`status`查看内存/任务，`demo`和14个ASCII表情命令保留。

## 你生成音频需要什么格式

**推荐文件名okay.wav，WAV容器、未压缩PCM signed16bit little-endian、16,000Hz、单声道**。“好的”建议0.3～2秒，硬上限3秒/96,000字节PCM；无背景音乐，首尾安静尽量短，不削波。建议导出峰值约-6～-3dBFS，最终音量仍在板上听测。不要仅把MP3后缀改成WAV；24bit/float WAV也需转换。

可把生成的WAV发给开发方；只有MP3或44.1kHz立体声也可发，由开发方转换。文件应包含你要的固定“好的”内容；导入器验证格式/时长/削波，不声称能自动判定文字/音质或推断素材许可。

如自己有FFmpeg，可转换：

```bat
ffmpeg -i D:\NOMI-audio\okay.mp3 -ar 16000 -ac 1 -c:a pcm_s16le D:\NOMI-audio\okay.wav
```

## 自己替换语音并构建

在有**当前feat/h3-offline-command-reply分支完整源码**的ESP-IDF5.5.4终端中（旧0.5.x源码没有导入器；这不是已解压二进制包目录）。可从[当前源码分支](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/tree/feat/h3-offline-command-reply)下载Code ZIP或切换本地分支，然后按实际源码路径运行：

```bat
cd /d D:\Desktop-NOMI
python firmware\scripts\import_reply.py D:\NOMI-audio\okay.wav --source "自行生成的固定回复"
python firmware\scripts\build.py --profile commands --package
```

`import_reply.py`只用Python标准库，不安装TTS模型、不联网，不烧录、不自动提交Git。拒绝格式错误、静音、数字削波、过长或截断文件。它会同时更新：

- `firmware/components/nomi_audio/assets/okay.pcm`：真正嵌入固件的原始采样；不是直接把WAV头写进去。
- 同目录`okay.json`：样本数/时长来源/格式/SHA256。
- 同目录`NOTICE.md`：新来源说明；不把原Melo许可冒充新素材许可。

**不要仅手动覆盖PCM而保留旧JSON**，构建审计会拒绝hash/长度不匹配。导入器不保存原WAV路径或复制源文件；保留你自己的原音频。`--license-note`可填写生成工具允许的项目使用/分发说明；默认只描述本地播放，不自动授权公开分发。目录里旧MeloTTS-LICENSE.txt仅说明旧占位资产，不能当新音频的许可证。

构建输出`firmware\dist\desktop-nomi-h2-commands.zip`，内含`okay-preview.wav`（与实际嵌入采样完全相同），先试听。解压到新的烧录目录，按上方flash_args烧录。即使只是改声音，目前也需要重新编译、重新烧录；本版没有SD卡替换、网页上传或运行时音频更新功能。

恢复出厂或回到USB版：分别按HARDWARE_H1恢复已验证备份，或重新烧录保留的0.5.x usb_asr完整包并运行原PC0.5.0，不混刷模型/分区。

## 调度与保护

`FixedReplyPlayer`为独立、无动态分配的固定播放内核，由采音任务独占AudioInput调用；USB调试与commands共用它。按实际RX采样累积每320样本写一次立体声，适配AFE任意≤1024样本块，I2S写超时20ms，不在渲染任务播放。播完100ms排空再关功放，300ms声学尾部保护；本地模式额外送2秒静音并持续fetch，覆盖50×1024字节AFE环形缓冲及VAD历史，再复位MultiNet继续识别。当前534ms占位音频合计约3秒保护；换3秒音频会更长，实际以状态点恢复蓝色/绿色为准。

保护从UI接受播放请求起生效，队列有界，丢弃保护中识别事件；AFE继续接收零采样，不把回应送进识别器；fetch所有权内只在保护边界清decoder，未跨任务重置模型。这是半双工基础保护，**不支持播放期间说指令或打断，也不是AEC**。读写/AFE/推理失败停止本轮并关闭PA，不静默跳过不连续PCM。

## 实体验收（全部待用户验证）

- 断开电脑数据连接、用合适电源冷启动；看初始化/待机指示，唤醒和14项逐项执行；记录漏检、误识别、距离/噪音条件，不只看ID日志。
- 同句重复/已激活重复唤醒只续期，不反复播；未激活指令、近似词、否定句/旁人讲话做负样本。MultiNet只辨词表，否定句不是完整语义理解，需测误触发。
- 听占位或替换音频；保护期没有新动作，恢复指示后能接下一句；“休息一下”回复后回绿色；20秒超时不回复。
- 连续30分钟测试任务栈、内部RAM/PSRAM、帧间隔、溢出/重启；日志status供观察，无CPU百分比字段不伪称CPU占用验收。当前不上传/保存录音或转录、不初始化网络。
- `wake off`/reinit及demo、串口手动14表情回归；替换WAV后试听内容与板声相符。未逐项验证不能声明硬件闭环测试通过。
