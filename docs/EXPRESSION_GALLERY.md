# 0.5.0：14种圆屏表情与网页预览

本版包含此前0.4.3固定“好的”回应，固件和PC必须成对升级到0.5.0；用户已经验证0.4.2基线效果很好，但本版新增表情和扬声器尚未实机验收。仍由Windows本地ASR识别板载麦克风，不是ESP32独立中文转录；不上传音频，不接AI或动态TTS。

## 可用表情

先说“小米同学”或“你好小米同学”，看到编号确认再说一条指令；只执行最终识别、严格词表匹配。正在聆听时重复叫名只续期，不反复回应。普通表情展示5秒后，在尚未到期的会话内恢复Listening，聆听窗口20秒到期回idle；blink是短暂闭眼后恢复原表情，idle会结束会话。Listening/speaking为展示状态，不暗示ASR/TTS正在板上运行。

| 表情 | 串口命令 | 唤醒后说 | 外观区别 |
| --- | --- | --- | --- |
| 待机 | `idle` | 回到待机 | 自然竖眼、轻微笑，自动眨眼 |
| 眨眼 | `blink` | 眨一下眼 | 双眼快速闭合再睁开 |
| 开心 | `happy` | 开心一点 | 弯弯笑眼与大笑嘴 |
| 难过 | `sad` | 难过一点 | 内侧抬眉、下垂视线、蓝色眼泪 |
| 好奇 | `curious` | 好奇一点 | 左眼大右眼小、向右看 |
| 思考 | `thinking` | 思考一下 | 向左上看、嘴平、三个思考点 |
| 聆听 | `listening` | 认真听讲 | 双眼睁大，外圈呼吸光环 |
| 说话 | `speaking` | 说话表情 | 眼睛正常，嘴巴持续开合 |
| 生气 | `angry` | 生气一点 | 明显V形眉、窄眼、红色怒气符号 |
| 惊讶 | `surprised` | 惊讶一下 | 大圆眼、抬眉、圆形张嘴 |
| 困倦 | `sleepy` | 困倦一下 | 细长半闭眼、小嘴和Zzz |
| 单眼眨眼 | `wink` | 单眼眨眼 | 右眼闭合，左眼睁开，俏皮笑嘴 |
| 喜欢 | `love` | 喜欢表情 | 粉色爱心眼和笑嘴 |
| 疑惑 | `confused` | 疑惑一下 | 右眼大左眼小、锯齿嘴、问号 |

## 先静音测试表情，再测试声音

新完整包解压到例如`D:\NOMI-050`。关闭旧程序和串口监视器，保留已验证的原厂备份；不需要整片擦除，不覆盖备份。ESP-IDF 5.5.4终端：

```bat
cd /d D:\NOMI-050
python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
```

仅使用`usb_asr`完整包，不能拿audio/benchmark/commands包搭配PC控制。将新包的`pc`文件合并到原`D:\NOMI-ASR-debug\pc`，保留原`.venv`及`models`；所有同名源码文件一起替换，不需要setup或重新下载模型：

```bat
cd /d D:\NOMI-ASR-debug\pc
start_control.cmd COM3 --silent-replies
```

按Enter开始采音，看到0.5.0的14表情协议就绪再测试。此选项不请求扬声器播放，便于先看脸。下一轮结束程序后去掉`--silent-replies`，才开始“好的”实机听测，见[SPOKEN_OKAY](SPOKEN_OKAY.md)。固定音频输出约0.5秒，总保护约0.9秒；保护期间用户语音也忽略，听完并看到恢复识别后再说下一句。

不想使用语音时，Ctrl+C退出PC程序，再打开：

```bat
python -m serial.tools.miniterm COM3 115200 --eol CRLF
```

输入`demo`回车：14种表情按表格顺序每3秒一项，结束回idle；输入任何表情ASCII命令取消demo。手动ASCII命令不播放回应；Ctrl+]退出。不要同时占用COM3。

## 网页查看与合并

网页原聊天Mock、Aora及API Key安全机制保留，新增“圆屏表情”入口与14张选择卡、循环演示、重播、语音指令提示。网页仅预览，不连接或控制硬件，不请求麦克风权限；360×360造型来自同一目录，SVG与LVGL的抗锯齿和动画时序并非逐像素相同。

代码分支`feat/h2-expression-gallery`包含先前所有H1/H2、0.4.2修复、固定回复和本次表情变更。此前代码均已推送GitHub。只需合并最终分支一次，不需逐个合并旧分支。当前main仍未包含这些变更，正式Pages不会因推送功能分支而自动更新。

用户需要发布时操作：

1. 打开[main与最终分支比较页](https://github.com/zhengxiangliu6-bit/Desktop-NOMI/compare/main...feat/h2-expression-gallery?expand=1)，确认base是main，compare是feat/h2-expression-gallery。
2. 点击Create pull request；等待固件、PC和Mock页面检查通过，再自行Merge pull request。本任务不自动创建PR或合并main。
3. main上的“Mock preview on GitHub Pages”工作流完成部署后，打开[圆屏表情预览](https://zhengxiangliu6-bit.github.io/Desktop-NOMI/#hardware-expressions)。必要时Ctrl+F5刷新。

功能分支Actions会提供`nomi-static-expression-preview`静态构建产物供审阅，但不部署正式站点。固件Actions提供四个profile包；本次用户应取usb_asr。PC源文件更新包不含模型、虚拟环境或用户录音。

## 实现与复现

- `shared/expressions.json`为14种造型/命令/语音别名的唯一目录；`python firmware/scripts/generate_faces.py`同步C++/Python/TypeScript，`--check`拒绝过期生成文件。LVGL纯矢量，无大图序列。180ms姿态插值、非阻塞动画；表情模型与语音会话独立。
- 新`probeall`能力握手确保PC不把14表情发给仅支持8种的旧固件；保留原串口命令，ACK序号/校验/幂等及固件端超时机制。
- 原生LVGL实际渲染14张图，检查半径160安全区；全部91对表情至少有500个不同像素。网页单元测试、桌面/手机浏览器、Pages子路径与Mock回归另行验证。
- 本次不扩展Web聊天情绪API枚举；新图库隔离展示硬件目录，不改变后端协议或密钥流程。

## 实体验收记录表（待用户填写）

逐项说表格里的14个短语，记录“最终中文/编号确认/实际屏幕是否正确”；不要只凭日志判定视觉成功。验证demo完整轮播、每张无裁切、无明显闪烁，单眼/双眼眨眼及idle超时；重复唤醒只续期，表情结束后可继续Listening，但会话20秒到期必须回idle。运行30分钟观察重启、RAM/PSRAM/帧间隔；静音测试通过后单独验收扬声器、音量、爆音及防回灌。尚未验收项不能写成实体通过。

恢复：可重新刷已验证0.4.2配套包和PC，或依照[H1备份恢复](HARDWARE_H1.md)恢复原厂整片备份。不要为切换表情执行整片擦除。
