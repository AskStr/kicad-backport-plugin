# KiCad Backport

版权 (C) 问星/askstar

版本 0.4.4

KiCad Backport 用于为旧版 KiCad 目标版本创建兼容的工程或文件副本。它面向
现代 S 表达式文件与 KiCad 5 时代 legacy 文件之间的实际降级和升级流程。
原始工程不会被覆盖。

转换核心使用纯 Python 实现，正常插件使用时在进程内运行。KiCad 5 时代的
Python 会通过外部 Python 3 解释器启动同一套 GUI，因此旧版 KiCad 安装也能
继续使用当前转换引擎。

## 翻译

- [English](README.en.md)
- [简体中文](README.zh_CN.md)
- [繁體中文](README.zh_TW.md)
- [Français](README.fr.md)
- [Deutsch](README.de.md)
- [Italiano](README.it.md)

## 当前能力

- 支持转换整个 KiCad 工程文件夹或单个 KiCad 文件。
- 在目标格式存在转换路径时，支持 PCB、原理图、符号库、封装、图框、设计
  规则、工程文件，以及 legacy 工程/符号库/原理图文件。
- 对 V5 目标，可将现代 `.kicad_sch`、`.kicad_sym`、`.kicad_pro` 转为
  KiCad 5 时代的 `.sch`、`.lib` / `.dcm`、`.pro`。
- 可将 legacy `.sch`、`.lib`、`.dcm`、`.pro` 升级回较新目标使用的 KiCad
  S 表达式或 JSON 工程文件。
- 保留工程本地符号库，并为旧目标规范化库表。
- 在需要时为现代工程输出重建 KiCad 6+ 原理图层级和符号实例数据。
- 对 V6/V7/V8 PCB 输出，写入兼容的工程本地 `.kicad_prl` 可见项和层设置。
- 当 zstd 解压可用时，将 PCB/封装内嵌的 3D 模型资源提取到工程本地 `3D/`
  文件。核心包含一个小型内置 zstd 帧解码器，支持 raw/RLE 块；完整压缩块
  可使用 Python 标准库 `compression.zstd`、系统 `libzstd` 或可选
  `zstandard` 包。
- 对较新版 PCB、封装、原理图、符号、图框和设计规则中旧 KiCad 不接受的
  特性进行兼容性改写。
- 通过 CLI 请求或从 GUI 启动时，可写出 JSON 转换报告。

部分现代 KiCad 特性在转换到很旧格式时天然会有损失。转换器会移除、改写或
近似处理不支持的结构，并为这些变化报告警告。

## 支持目标版本

GUI 目标列表：

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7
- KiCad 6
- KiCad 5.1
- KiCad 5.0
- KiCad 4

转换核心还接受原始的开发格式日期目标，覆盖 `20260410` 到当前
PCB/封装格式 `20260728` 等检查点。内置的 10.99 档位当前输出：符号库
`20260629`、原理图 `20260722`、PCB/封装 `20260728`。

当目标版本早于这些 10.99 新特性时，原生椭圆会近似为兼容的折线/多边形，
封装仿射变换会烘焙到旧版可读取的位置和几何字段。pin-to-pad 映射、变体
`symbol_override`、net chain、几何约束和自定义网格没有等价旧格式时才会删除；
所有近似或删除都会写入 JSON 转换报告。跨越修正 PPI 的格式边界
`20260623` 时，嵌入 PNG 参考图会重算 scale 以保持显示尺寸。

支持输入系列包括：

- 当前 KiCad 10.99 每夜版文件
- KiCad 10、9、8、7、6、5 文件
- KiCad legacy `.sch`、`.lib`、`.dcm`、`.pro` 文件

## 语言

插件会尽可能跟随 KiCad 当前选择的语言。它还会检查 KiCad 5 风格配置文件
（例如 `kicad_common`）、常见 KiCad 语言环境变量，最后回退到操作系统界面
语言。

支持的界面语言：

- 英文
- 简体中文
- 繁体中文
- 法语
- 德语
- 意大利语

修改 KiCad 语言后，请重启 KiCad 或重新打开插件窗口。

## 平台兼容

支持系统：

- Windows
- macOS
- Linux

GUI 会优先尝试 wxPython，并在不可用时回退到 tkinter。KiCad 5 legacy 模式
中，启动器会优先使用 tkinter，并把检测到的 KiCad 语言和配置路径传给外部
Python 3 进程。

## 安装

1. 关闭 KiCad。
2. 将整个 `kicad-backport` 文件夹复制到 KiCad 用户 `plugins` 文件夹。
3. 对 KiCad 10.99 及更新的 API 插件，请使用带版本号的用户插件目录，例如
   `C:\Users\<你>\Documents\KiCad\10.99\plugins`。
4. 在 KiCad 10.99 中，在偏好设置中启用 KiCad API/API server；否则 KiCad
   不会发现或加载 API 插件。
5. 对旧版 KiCad，也将同一文件夹复制到 KiCad 的 `scripting/plugins` 文件夹。
6. 重新启动 KiCad。
7. 打开 KiCad 插件管理器或应用工具栏/菜单，查找 `创建 KiCad 兼容副本`。

如果看不到该操作，请确认文件夹已复制到当前 KiCad 版本使用的插件文件夹中。
在 KiCad 10.99 中，API 插件不会从已安装程序的内置脚本目录加载，例如
`share/kicad/scripting/plugins`；请使用用户 `plugins` 文件夹，并确认已启用
KiCad API/API server。

## 在 KiCad 中使用

1. 运行 `创建 KiCad 兼容副本`。
2. 选择工程文件夹或受支持的 KiCad 文件。
3. 选择一个不同的输出文件或文件夹。
4. 选择目标 KiCad 版本。
5. 点击 `转换`。

输出会写入带目标后缀的路径，例如 `_V7`、`_V5` 或 `_V10_99`。对 V5 目标，
现代原理图和符号库扩展名会自动改为 legacy 扩展名。

## 从命令行使用

带参数运行启动器：

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

列出 GUI 支持的目标：

```powershell
python plugin\plugin.py --list-targets
```

## 构建安装包

在仓库根目录构建插件压缩包：

```powershell
.\build.ps1 -Format all
```

```sh
./build.sh --format all
```

支持的打包格式为 `zip`、`tar.gz` 和 `all`。

常用环境变量：

- `KICAD_BACKPORT_PYTHON`：KiCad 5 启动器使用的 Python 3 可执行文件。
- `KICAD_BACKPORT_GUI_BACKEND`：`wx`、`tk`、`auto` 或 `legacy`。
- `KICAD_BACKPORT_LANGUAGE`：显式界面语言覆盖。
- `KICAD_BACKPORT_KICAD_CONFIG_PATH`：用于语言检测的 KiCad 配置文件或文件夹。

## 重要说明

- 始终选择不同于原始工程的输出路径。
- 在共享或用于生产前，请在目标 KiCad 版本中检查转换后的副本。
- 很旧的目标无法保留所有现代特性。请查看转换报告和警告信息。
