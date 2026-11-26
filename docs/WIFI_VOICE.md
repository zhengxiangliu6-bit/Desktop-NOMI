# ESP32 Wi-Fi 语音试用

设备启动后连接 2.4 GHz Wi-Fi。运行中短按 Key2（BOOT，GPIO0），看到聆听表情后说话。设备录制四秒 16 kHz 单声道 PCM，结束后通过 HTTPS 发送给语音网关。请在开机完成后按键。上电时按住 BOOT 会进入下载模式。

网关返回中文转录。设备串口显示 `TRANSCRIPT`。例如说“你好，小米同学，开心一点”，网关剥离前置称呼并匹配完整指令，设备切换表情并播放本地“好的”。仅叫名字会返回转录，下一次按键可另录指令。支持词表见 [网关](../backend/app/voice_gateway.py)。

## 网关

在常开的服务器上进入 `backend`，安装锁定依赖，将以下变量配置到服务环境：

- `NOMI_DEVICE_TOKEN` 为随机生成的至少 24 字符设备令牌。它与板上配置一致。
- `NOMI_ASR_API_KEY` 为转录供应商密钥，仅配置在服务器。
- 可选 `NOMI_ASR_URL` 和 `NOMI_ASR_MODEL`。默认是 OpenAI 的 `/v1/audio/transcriptions` 与 `gpt-4o-mini-transcribe`，实际请求按服务商规则计费。

```sh
uv sync --locked
uv run uvicorn app.voice_gateway:app --host 127.0.0.1 --port 8788
```

用已有 HTTPS 反向代理将 `/device/voice` 转发至该服务，使用 ESP-IDF 证书包信任的证书，限制请求体大小和请求速率。该服务与网页聊天服务分开。音频经网关转发给所配置的供应商。网关本身在内存中处理 PCM 和 WAV。设备通过 NTP 获得 TLS 校验所需的时间。

## Windows 本地构建

在 ESP-IDF 5.5.4 窗口进入仓库，切到 `feat/h4-wifi-voice` 后运行：

```bat
python firmware\scripts\build.py --profile wifi --menuconfig
```

在 **Desktop-NOMI H2 local audio** 菜单填写 SSID、密码、完整 HTTPS URL（含 `/device/voice`）以及设备令牌并保存。设置保存在本地忽略的 `firmware/sdkconfig.wifi.local`，可从生成的固件中提取，请仅在自己的设备上使用并保护构建目录。

```bat
python firmware\scripts\build.py --profile wifi --reply-assets "D:\codex\NOMI-private-reply"
```

等出现 `Validated wifi:`。关闭串口监视器，逐行执行：

```bat
cd /d D:\codex\Desktop-NOMI\firmware\build-wifi
python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
python -m serial.tools.miniterm COM3 115200 --eol CRLF
```

看到 `Wi-Fi connected` 后，等待设备获取时间。短按 Key2，在聆听表情出现后说“开心一点”，核对串口转录、表情和播放。使用实际网络、凭据、板子和供应商完成验收。若转录出错，先看 `wifi_voice` 的 Wi-Fi、时间、采音或 HTTP 错误。
