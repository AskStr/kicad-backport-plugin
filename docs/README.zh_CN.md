# KiCad Backport

版权 (C) 问星

版本 0.1.1

KiCad Backport 用于创建可由旧版 KiCad 打开的工程或文件副本。原始工程不会被覆盖。

0.1.1 版本支持当前 KiCad 10.99 每夜版保存的工程，并可输出兼容 KiCad 10、KiCad 9、KiCad 8 或 KiCad 7 的副本。

## 语言

插件会尽可能跟随 KiCad 当前选择的语言。如果没有找到 KiCad 语言设置，则使用系统语言。

当前界面支持：英文、简体中文、繁體中文、法语、德语、意大利语。

## 跨平台兼容

支持系统：

- Windows x64 和 Windows ARM64
- macOS Intel 和 Apple Silicon
- Linux x64 和 Linux ARM64

插件会自动选择当前系统对应的转换器。

## 支持目标版本

支持输入版本：

- KiCad 10.99 每夜版
- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

支持输出目标：

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## 安装

1. 关闭 KiCad。
2. 将整个 `kicad_backport` 文件夹复制到 KiCad 用户 `plugins` 文件夹。
3. 对 KiCad 10.99 及更新的 API 插件，请使用带版本号的用户插件目录，例如 `C:\Users\<你>\Documents\KiCad\10.99\plugins`。
4. 在 KiCad 10.99 中，必须在偏好设置中启用 KiCad API/API server，否则 KiCad 不会识别或加载 API 插件。
5. 对旧版 KiCad，也将同一文件夹复制到 `scripting/plugins`。
6. 重新启动 KiCad。
7. 运行 `创建 KiCad 兼容副本`。

在 KiCad 10.99 中，API 插件不会从已安装程序的内置脚本目录加载，例如 `share/kicad/scripting/plugins`；请使用用户 `plugins` 文件夹，并确认已启用 KiCad API/API server。

## 使用

1. 选择 KiCad 文件或工程文件夹。
2. 选择不同的输出文件或文件夹。
3. 选择目标 KiCad 版本。
4. 点击 `转换`。

请在目标 KiCad 版本中检查转换后的副本，再用于共享或生产。
