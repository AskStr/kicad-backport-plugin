# KiCad Backport

版权 (C) 问星

版本 0.4.1

KiCad Backport 用于为旧版 KiCad 创建兼容工程或文件副本。它支持现代
S 表达式文件与 KiCad 5 时代 legacy 文件之间的降级和升级流程，原始工程
不会被覆盖。

转换核心为纯 Python 实现。KiCad 5 时代的 Python 会通过外部 Python 3
解释器启动同一套 GUI，因此旧版 KiCad 也能使用当前转换引擎。

## 当前能力

- 支持转换整个工程文件夹或单个 KiCad 文件。
- 在存在转换路径时，支持 PCB、原理图、符号库、封装、图框、设计规则、
  工程文件，以及 legacy 工程/符号库/原理图文件。
- 可将现代 `.kicad_sch`、`.kicad_sym`、`.kicad_pro` 转为 KiCad 5
  时代的 `.sch`、`.lib` / `.dcm`、`.pro`。
- 可将 legacy `.sch`、`.lib`、`.dcm`、`.pro` 升级为较新目标版本使用的
  KiCad 文件。
- 会保留工程本地符号库、规范化库表，并在需要时重建 KiCad 6+ 原理图层级
  与符号实例信息。
- 对 V6/V7/V8 PCB 输出，会写入兼容的工程本地 `.kicad_prl` 可见项和层设置。
- GUI 和 CLI 都可生成 JSON 转换报告。

## 支持目标版本

GUI 可选目标：KiCad 10、9、8、7、6、5.1、5.0、4。

转换核心还支持部分原始数字格式目标，例如开发版 PCB/封装格式
`20260603` 和 `20260521`。

支持输入系列包括当前 KiCad 10.99 每夜版、KiCad 10 到 KiCad 5 文件，以及
legacy `.sch`、`.lib`、`.dcm`、`.pro` 文件。

## 语言

插件会尽可能跟随 KiCad 当前选择的语言。它会读取 KiCad 5 风格的
`kicad_common` 等配置文件、常见 KiCad 语言环境变量，最后回退到操作系统
界面语言。

当前界面支持：英文、简体中文、繁体中文、法语、德语、意大利语。

## 平台兼容

支持系统：Windows、macOS、Linux。

GUI 会优先尝试 wxPython，并在不可用时回退到 tkinter。KiCad 5 legacy 模式
会优先使用 tkinter，并把检测到的 KiCad 语言和配置路径传给外部 Python 3
进程。

## 安装

1. 关闭 KiCad。
2. 将整个 `kicad-backport` 文件夹复制到 KiCad 用户 `plugins` 文件夹。
3. 对 KiCad 10.99 及更新的 API 插件，请使用带版本号的用户插件目录，例如
   `C:\Users\<你>\Documents\KiCad\10.99\plugins`。
4. 在 KiCad 10.99 中，必须在偏好设置中启用 KiCad API/API server。
5. 对旧版 KiCad，也将同一文件夹复制到 `scripting/plugins`。
6. 重新启动 KiCad。
7. 运行 `创建 KiCad 兼容副本`。

在 KiCad 10.99 中，API 插件不会从已安装程序的内置脚本目录加载，例如
`share/kicad/scripting/plugins`；请使用用户 `plugins` 文件夹，并确认已启用
KiCad API/API server。

## 使用

1. 选择 KiCad 文件或工程文件夹。
2. 选择不同的输出文件或文件夹。
3. 选择目标 KiCad 版本。
4. 点击 `转换`。

输出会自动追加目标后缀，例如 `_V7`、`_V5` 或 `_V10_99`。对 V5 目标，现代
原理图和符号库扩展名会自动改为 legacy 扩展名。

命令行入口：

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

请在目标 KiCad 版本中检查转换后的副本，再用于共享或生产。
