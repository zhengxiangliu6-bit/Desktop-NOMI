# H1：ESP32-S3 圆屏表情固件

状态：软件实现与云端验证记录见 [HANDOFF](HANDOFF.md)；**未连接实体硬件，Windows/备份/恢复/烧录均待实机验证**。不要将成功编译视为硬件验收。本阶段只有独立表情固件，现有 Pages Mock 与 API Key 安全机制不变。

## 已核对的官方依据

调查日期 2026-11-13（Asia/Shanghai），固定上游提交 `5a98b8da1948340c07032a408ac0d93c47ca558f`：

- [官方仓库/板载资源](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-1.85B/tree/5a98b8da1948340c07032a408ac0d93c47ca558f)。
- [Rev1.1 原理图](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-1.85B/blob/5a98b8da1948340c07032a408ac0d93c47ca558f/hardware/ESP32-S3-Touch-LCD-1.85B%20Rev1.1.pdf)：MCU ESP32-S3R8、外部 Flash、LCD/TP 网络、USB GPIO19/20、BOOT GPIO0 与 CHIP_PU/RESET 网络。原理图按键为 Key1 电源、Key2 BOOT，不假定存在独立 RESET 按钮。官方 README 标明 16 MB Flash / 8 MB PSRAM，官方 sdkconfig.defaults 配置八线 80 MHz PSRAM。
- [官方 ESP-IDF LVGL 示例](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-1.85B/tree/5a98b8da1948340c07032a408ac0d93c47ca558f/examples/esp-idf/01_lvgl_demo)：README 要求 IDF 5.5.4；主 manifest 固定 LVGL 9.5.0、esp_lvgl_adapter 0.3.2，BSP 依赖 esp_lcd_st77916 ^2.0.1、esp_lcd_touch_cst816s ^1.1.0。H1 不整体引入 BSP 的音频/网络依赖，显示专用改写说明见 [NOTICE](../firmware/components/nomi_panel/NOTICE.md)。
- [官方固件恢复说明](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-1.85B/blob/5a98b8da1948340c07032a408ac0d93c47ca558f/firmware/README.md)：合并镜像写 `0x0`，提供 20261109 / 20261027 / 20260328 版本。20261109 镜像包含语音模型，不含已上传照片的 assets 分区；恢复官方镜像与恢复自己整片备份不是同一操作。

## 准确板型与引脚

**仅适用带 B 后缀的 ESP32-S3-Touch-LCD-1.85B**。必须核对实物丝印/订单与 Rev1.1；不是 ESP32-S3-Touch-LCD-1.85、1.85C、1.28 等板的通用固件。下表取自该板官方 BSP `include/bsp/esp32_s3_touch_lcd_1_85B.h`，并核对原理图 LCD/TP 网络。

| 项目 | 参数 / GPIO |
| --- | --- |
| LCD 控制器 | ST77916，360×360，RGB565 RGB 顺序 |
| 接口 | SPI2，QSPI，80 MHz；命令 32 bit、参数 8 bit；无独立 DC |
| LCD SCLK | 40 |
| LCD DATA0 / 1 / 2 / 3 | 46 / 45 / 42 / 41 |
| LCD CS / RESET / 背光 | 21 / 3 / 5（LEDC PWM） |
| 触摸 | CST816 系列（官方 CST816S 驱动），H1 不初始化 |
| 共享 I²C SDA / SCL | 11 / 10，400 kHz |
| Touch RESET / INT | 1 / 4 |
| USB D− / D+ | 19 / 20；H1 使用原生 USB Serial/JTAG |
| BOOT | GPIO0，低有效；仅下载模式使用 |
| Flash / PSRAM | 16 MB QIO / 8 MB 八线 PSRAM 80 MHz |
| 开发框架 | ESP-IDF v5.5.4，LVGL v9.5.0，C++17 |

官方 BSP 先以 3 MHz 读面板 ID，再切至 80 MHz，根据 `00 7f 7f 7f` / `00 02 7f 7f` 选择两套初始化表，其他结果使用驱动默认表。H1 保留此流程并输出 ID/表选择日志。实际面板版本、颜色顺序、方向及 PSRAM 必须在自己的板上确认。原理图 R7 将 GPIO3 接至 LCD RESET，R10 将 GPIO1 接至触摸 RESET；本工程使用板载连接，不需要拆除 0Ω 电阻。

## Windows：先准备可恢复副本

以下 PowerShell 命令面向未开启 Flash 加密 / Secure Boot 的原厂开发板。先核对准确板型、下载好官方恢复镜像并保存两份整片备份，之后才进入 H1 烧录。不要在未确认恢复材料时先擦除。

1. 安装 Python 3、Git；安装 Espressif 官方 ESP-IDF **v5.5.4** 工具链，可使用官方 [Windows 安装说明](https://docs.espressif.com/projects/esp-idf/en/v5.5.4/esp32s3/get-started/windows-setup.html)。后续构建在其 ESP-IDF PowerShell/命令提示符中执行。备份工具可单独安装于虚拟环境：

   ```powershell
   py -3 -m venv "$env:USERPROFILE\nomi-flash-tools"
   & "$env:USERPROFILE\nomi-flash-tools\Scripts\python.exe" -m pip install esptool==4.11.0 pyserial==3.5
   $flashPython = "$env:USERPROFILE\nomi-flash-tools\Scripts\python.exe"
   ```

2. 使用可靠 USB 数据线，将板接入电脑。在设备管理器确认 USB Serial/JTAG 串口（可能重新枚举），记录 COM 号。示例 COM7 必须替换。无法枚举时先检查数据线、USB 驱动及设备管理器，不刷其他板驱动包。优先让 esptool 自动进入 ROM 下载模式。若失败，可在已确认板完全断电后按住 BOOT（原理图 Key2/GPIO0）并重新供电，枚举后松开 BOOT，再查看 COM 号；电池仍供电时仅拔 USB 不等于断电。原理图 Key1 是电源控制键，不将其当作 RESET；电源操作不确定时先向微雪确认实物版本，不猜测组合或拆电池/电阻。关闭占用串口的终端。

   ```powershell
   $port = "COM7"
   & $flashPython -m esptool --chip esp32s3 --port $port --after no_reset flash_id
   & $flashPython -m esptool --chip esp32s3 --port $port --after no_reset get_security_info
   ```

   确认 ESP32-S3、Detected flash size 为 16MB。若加密/Secure Boot 已启用、容量不符或读取失败，停止通用流程；备份可能是密文或被禁止，不能承诺以下方法恢复。不要使用任何烧写 eFuse、强制写入或关闭安全功能的参数。

3. 整片备份保存在仓库外。备份可能包含原厂 Wi-Fi 凭据、设置和照片，不能上传 GitHub/PR/公共日志。

   ```powershell
   $backupDir = "$env:USERPROFILE\NOMI-backup"
   New-Item -ItemType Directory -Force $backupDir
   & $flashPython -m esptool --chip esp32s3 --port $port --baud 460800 --after no_reset read_flash 0x0 0x1000000 "$backupDir\factory-full-a.bin"
   # 每条命令都应成功；失败时不要继续烧录。必要时降到 115200 重试。
   & $flashPython -m esptool --chip esp32s3 --port $port --baud 460800 --after no_reset read_flash 0x0 0x1000000 "$backupDir\factory-full-b.bin"
   (Get-Item "$backupDir\factory-full-a.bin").Length
   (Get-Item "$backupDir\factory-full-b.bin").Length
   Get-FileHash "$backupDir\factory-full-a.bin" -Algorithm SHA256
   Get-FileHash "$backupDir\factory-full-b.bin" -Algorithm SHA256
   & $flashPython -m esptool --chip esp32s3 --port $port --after no_reset verify_flash 0x0 "$backupDir\factory-full-a.bin"
   ```

   两个文件必须各 **16,777,216 字节**，SHA256 一致，verify_flash 成功。保存散列、板型/版本和工具版本，另复制到可靠位置。保持下载模式可避免原厂应用在两次读取间写设置。备份后可重新上电验证原厂仍启动；此步骤无需擦除或写 Flash。

4. 提前下载并校验本次核对的官方恢复镜像：[20261109 固定版本](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-1.85B/blob/5a98b8da1948340c07032a408ac0d93c47ca558f/firmware/ESP32-S3-Touch-LCD-1.85B_FactoryOnly_20261109.bin)（点击 Download raw file，不能保存 GitHub HTML 页面）。本次检出文件大小 **10,514,658 字节**，SHA256：

   ```text
   10dbcd2655fe44249840ff2b8879ff11152a7d73e1d6a3ebd8311c1f8e2b3b05
   ```

   ```powershell
   Get-FileHash .\ESP32-S3-Touch-LCD-1.85B_FactoryOnly_20261109.bin -Algorithm SHA256
   ```

   该镜像恢复官方应用，不保证恢复出厂原有版本/个人设置。自己的完整备份用于精确恢复该板刷写前内容；烧录及恢复命令尚未在本机设备上执行验证。

## Windows：构建并烧录 H1

确认上节板型、无加密、备份校验及官方恢复材料均已完成。在 ESP-IDF v5.5.4 终端拉取交付分支，进入工程：

```powershell
git clone --branch feat/h1-esp32-face https://github.com/zhengxiangliu6-bit/Desktop-NOMI.git
cd Desktop-NOMI\firmware
idf.py --version
python scripts/prepare.py
idf.py build
idf.py size
idf.py -p COM7 -b 460800 flash
idf.py -p COM7 monitor
```

已有仓库只需 fetch/切换分支。每一步检查成功再继续。**不先执行 erase_flash**；H1 的默认 single_app_large 分区会取代官方分区表，因此不可依赖旧分区内容保持可用。`idf.py flash` 使用生成的准确偏移与参数（bootloader 通常 0x0、partition table 0x8000、app 0x10000，以本次 build/flash_args 为准），会验证写入。先关闭串口查看器；自动复位失败再按上节 BOOT 上电条件进入下载模式。刷写完成复位/重新上电并重新确认 COM 号。连接错误/白屏时不要尝试别的板引脚；保存固定错误信息和板版本，按下节恢复。

## 两种恢复方式（任选符合目的的一种）

均需关闭串口终端、进入 ROM 下载模式，使用相同且已确认的板和 COM 号。以下是**恢复时**才执行的写入命令，不是在备份阶段执行。

恢复刷写前完整内容（仅同一块未加密板、备份 SHA/大小核对无误）：

```powershell
& $flashPython -m esptool --chip esp32s3 --port $port --baud 460800 write_flash 0x0 "$backupDir\factory-full-a.bin"
& $flashPython -m esptool --chip esp32s3 --port $port verify_flash 0x0 "$backupDir\factory-full-a.bin"
```

整片备份覆盖完整 16 MB，不需要另做整片擦除。复位/重新上电后检查原有桌面、设置及照片，记录结果。

恢复指定官方应用（会清除已保存的凭据/设置/照片，先备份）：

```powershell
& $flashPython -m esptool --chip esp32s3 --port $port erase_flash
& $flashPython -m esptool --chip esp32s3 --port $port --baud 460800 write_flash 0x0 .\ESP32-S3-Touch-LCD-1.85B_FactoryOnly_20261109.bin
& $flashPython -m esptool --chip esp32s3 --port $port verify_flash 0x0 .\ESP32-S3-Touch-LCD-1.85B_FactoryOnly_20261109.bin
```

这是官方 firmware/README 的整片擦除 + 合并镜像 0x0 方法。官方也允许不擦除以保留旧 assets，但 H1 已替换分区布局，不能将这项保留策略当作跨固件安全保证。复位后确认官方桌面；不要将 H1 app bin 用此合并镜像命令烧录。

## 串口日志与基础实机验收

`idf.py -p COM7 monitor` 查看启动日志，Ctrl+] 退出。交互命令也可使用单独备份虚拟环境中的 pyserial：

```powershell
& $flashPython -m serial.tools.miniterm COM7 115200 --eol CRLF
```

Ctrl+] 退出；输入 `status`、`demo`、`idle` 等并回车，必要时 Ctrl+T、Ctrl+E 切换本地回显（miniterm）。每次只开一个串口工具；USB 重新枚举后更新 COM。不要公开完整原厂日志/备份。

| 验收 | 操作与通过条件 |
| --- | --- |
| 启动 | 断电再上电至少 5 次；首个可见 UI 是 NOMI 的脸，没有原厂桌面或明显闪白；记录启动耗时 |
| 板型/内存 | 日志 PSRAM 初始化成功、size=8388608；ST77916 ID、所选表、RGB565、双缓冲日志正常；无反复复位 |
| 8 种表情 | 发送 demo，逐一观察 idle/blink/happy/sad/curious/thinking/listening/speaking，均完整落在圆内且可辨认；listening/speaking 无真实音频 |
| 自然眨眼 | idle 观察 1 分钟，间隔约 2.5–6 秒，眨眼后眼形恢复 |
| 状态切换/恢复 | happy 后立即 thinking、idle、sad；旧状态不抢占；单独预览 5 秒后恢复 idle；blink 不清除原状态 |
| 输入边界 | 输入未知命令、超过 47 字符的一行，均日志回退 idle；只发半行时动画仍推进 |
| 非阻塞 | demo 中不断 status/idle，输入响应通常在 100 ms 内；动画无长暂停、明显闪烁/撕裂/颜色错误 |
| 稳定性 | 观察至少 30 分钟，重复 demo，比较 status 内存，无持续下降、WDT、DMA timeout、重启或花屏 |
| 恢复 | 按所选恢复方案实际执行，复位确认官方应用/原有内容；记录工具版本、操作和结果 |

所有上述实机项目、Windows 驱动/COM 识别、USB 自动复位、实际刷新率/撕裂/亮度/功耗/热表现目前都**未验证**。离屏像素检查不能覆盖 LCD ID、QSPI 时序、屏幕批次差异或 PSRAM 稳定性。H1 不承诺触摸、音频、Wi-Fi 或后端设备连接；后续另行授权。
