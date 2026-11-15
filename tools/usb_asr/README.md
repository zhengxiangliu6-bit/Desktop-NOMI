# PC语音控制0.4.1更新（不用重新烧录）

已安装0.4.0的用户：将ZIP中的pc文件夹合并覆盖到`D:\NOMI-ASR-debug`，保留已有`.venv`与`models`。在pc目录运行`start_control.cmd COM3`，按Enter开始；先说“小米同学”或“你好小米同学”，设备确认Listening后再说“开心一点”等。20秒无有效指令或“休息一下”回待机。只用最终结果，不做模糊匹配、不接AI/TTS/云服务。

完整词表、更新、设备回执与待测边界见更新包内`VOICE_CONTROL_GUIDE.md`或仓库`docs/PC_VOICE_CONTROL.md`。`start.cmd COM3`继续为纯转录，不执行动作；不必重新setup/下载模型。PC模式仍需电脑运行。

# ESP32板载麦克风 → Windows本地中文转录

需要64位Python3.10–3.13（可使用已安装的ESP-IDF终端中的Python）、USB转录调试固件0.4.0、真实COM端口。此程序不打开电脑麦克风。识别在Windows CPU进行；默认不保存音频或转录，运行阶段不调用网络服务。

首次从ESP-IDF终端运行`setup.cmd`：创建此目录自己的`.venv`，不修改ESP-IDF Python环境；下载固定Python依赖及约21MB中文模型，校验归档和模型文件SHA256。之后运行`start.cmd COM3`，按Enter开始板载麦克风；Ctrl+C停止。关闭miniterm或其它占用COM3的软件。

输出`[临时]`为可修订的流式假设，`[最终]`为停顿后结果；`[音频]`为真实采样统计；`[异常]`为丢帧、校验、采音、USB或积压错误。缺文字不等于没声音；以电平及完整句子试读排查。第一次不必先说“小米同学”，也不执行语音表情指令。

默认板载MIC1。若电平持续很低，可在同一终端试`start.cmd COM3 --mic 2`；不要同时打开两个程序。可用`--threads 4`测试更多CPU线程，但不保证更快。程序仅保留至多0.5秒输入队列；跟不上会停止并报错，不悄悄丢帧继续识别。

版本：sherpa-onnx及其core 2.0.1、NumPy2.2.6、pyserial3.5；模型固定为`sherpa-onnx-streaming-zipformer-small-ctc-zh-int8-2025-04-01`。模型来源、字节数和SHA256见`model.lock.json`。sherpa-onnx为Apache-2.0，NumPy为BSD及其分发依赖许可，pyserial为BSD。Python轮子由pip安装，不重新打包轮子；模型由用户脚本从上游固定发布下载，交付ZIP不重新分发权重。上游模型归档未附独立LICENSE，本次不补造模型许可证。

详细Windows步骤、USB安全停止、当前未实测项见ZIP内`docs/USB_CHINESE_TRANSCRIPTION.md`或仓库同名文档。使用结束后若要恢复独立指令功能，刷回原0.3.0 commands完整ZIP，不用擦除整片Flash，不动原厂备份。
