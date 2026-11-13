# Desktop-NOMI H1 固件

目标仅为 **Waveshare ESP32-S3-Touch-LCD-1.85B，360×360**。这是独立 ESP-IDF 工程，不运行 React/Aora，不连接前后端，不含 Wi-Fi、AI、录音、播放、记忆或舵机。启动直接绘制 NOMI 的脸，完成首帧后才打开背光。

**先阅读 [硬件、备份、恢复及 Windows 烧录说明](../docs/HARDWARE_H1.md)。云端构建/离屏渲染不代表实体设备通过。**

## 构建

使用官方示例对应的 **ESP-IDF v5.5.4**（含其工具链）、Python 3、Git。不要将 Arduino 或其他板的配置套用到此工程。在 ESP-IDF 终端执行：

```sh
cd firmware
python scripts/prepare.py
idf.py build
idf.py size
```

`prepare.py` 从 GitHub 获取 LVGL **9.5.0** 并核对完整提交 SHA，拒绝错误版本及有修改的依赖。下载目录被忽略；不需要 Espressif 组件注册表。显示驱动及两版初始化表已随源码保留；来源、许可证与修改说明见 [NOTICE](components/nomi_panel/NOTICE.md)。工具链必须是 v5.5.4；不使用未锁定的组件解析。不要提交 sdkconfig、build 或设备备份。

输出为 `build/desktop_nomi_h1.bin`、bootloader、partition-table、ELF、map 和 `flash_args`。推荐用同一构建目录的 `idf.py -p COMx flash`，不要把 app bin 单独写入 `0x0`。本工程固定 esp32s3、16 MB QIO Flash、8 MB 八线 PSRAM 80 MHz；USB Serial/JTAG 控制台。首次构建使用 sdkconfig.defaults，切换工程/配置后删除旧构建和本地 sdkconfig 再重建，避免继承别的板配置。

## 本地表情调试

串口 115200，发送一行 ASCII 命令并回车：

| 命令 | 行为 |
| --- | --- |
| `idle` | 取消预览/眨眼，回待机 |
| `blink` | 180 ms 闭合/张开，恢复原情绪/阶段 |
| `happy` / `sad` / `curious` | 设置情绪，5 秒到期 |
| `thinking` / `listening` / `speaking` | 设置对话阶段，5 秒到期；均为无声动画 |
| `demo` | 按上述八种表情依次演示，各 3 秒，一轮后 idle |
| `status` | 输出阶段/情绪枚举、可用内存和历史最低内存 |

情绪和阶段正交：阶段覆盖情绪显示但不延长情绪 TTL。可以先发 happy 再发 speaking 检查两者独立；阶段到期若情绪也已过期就恢复 idle。任意表情命令取消 demo；status 不打断。未知命令及超过 47 字符的输入行清空状态并回退 idle；空行忽略。单轮最多读取 32 字节，未完成的输入行不阻塞动画。不是设备网络协议或 HTTP API。

status 数值：phase 0/1/2/3 = idle/thinking/listening/speaking，emotion 0/1/2/3 = neutral/happy/sad/curious。它反映逻辑状态，眨眼不改变这两个字段。

待机每 2.5–6 秒触发自然眨眼；状态切换使用 180 ms 平滑插值，20 ms 更新几何，LVGL 默认 33 ms 刷新。所有图形位于圆心 (180,180)、半径 160 的安全圆内。只创建固定数量对象，随后修改坐标/透明度，不反复创建图形或保存图片帧。两块 RGB565 内部 DMA 缓冲总计 **23,040 字节**，不使用全屏图片缓存。动画以单调时钟推进；主循环 5 ms FreeRTOS yield，DMA 等待用信号量让出 CPU；初始化阶段保留官方复位/面板指令所需等待。

H1 暂不驱动 CST816 触摸；不用触摸也能完成全部表情验证。面板 ID 读取和两版表选择沿用官方流程；未知 ID 会日志提示并使用驱动默认表，须实机确认，不能把默认回退视为已匹配新硬件版本。

## 自动化测试

原生 C++17 状态机测试（无需硬件或 LVGL）：

```sh
cmake -S tests -B /tmp/nomi-model-tests
cmake --build /tmp/nomi-model-tests
ctest --test-dir /tmp/nomi-model-tests --output-on-failure
```

Windows 将 `/tmp/nomi-model-tests` 换为本机临时目录。安装 Git/LVGL 依赖后可运行实际 LVGL 离屏渲染与安全区域检查：

```sh
python scripts/prepare.py
cmake -S tests -B /tmp/nomi-render-tests -DNOMI_RENDER_TESTS=ON
cmake --build /tmp/nomi-render-tests
ctest --test-dir /tmp/nomi-render-tests --output-on-failure
```

渲染测试在测试构建目录生成八张 PPM；它验证矢量渲染和像素边界，不模拟 SPI/PSRAM/实体屏幕。构建结果及实机待测项见 [HANDOFF](../docs/HANDOFF.md)。
