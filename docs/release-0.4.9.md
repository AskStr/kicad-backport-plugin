# 0.4.9 发布说明：KiCad 6/7 往返与 KiCad 6–10.99 通用启动

发布日期：2026-09-18。包状态为 **stable**。本版本修复预发布验证中记录的四条 V6/V7 失败，
并为一个 PCM 安装包加入 KiCad 6–10.99 自动启动分流：KiCad 6–10 使用传统 ActionPlugin，
KiCad 10.99 使用 API/IPC。正式发布版本号为 **0.4.9**，沿用原 PCM 订阅地址。
如果安装过未发布的同版本测试包，请先卸载测试副本，再从正式仓库安装。

## 修复方案

### 位号、单元、页码

1. 在输出结构被降级清理后，仍从独立的源文档快照读取实例信息。
2. 以工程、根 UUID 和完整子页路径选择实例，不再总取第一条实例或只按文件名判断。
3. KiCad 6 写完整根级 `symbol_instances` / `sheet_instances` 表，覆盖共用和嵌套子页。
4. KiCad 7 已支持按工程/路径区分的本地 `instances`，和 8/9/10 一样保留或补齐路径。
5. 保留根 UUID、合法的引脚隐藏标记及多单元相同位号；不通过任意重编号“修复”冲突。
6. 共用子页只解析一次并累积各路径，只有真正的顶层原理图作为根处理，不改写工程外引用文件。

### 电源网络

KiCad 6/7 按电源输入引脚名命名网络，8 起使用放置符号的 Value。
仅保留 `(power)` 标记不够，因此降到 6/7 时：

- 按原库符号和 Value 创建独立、确定性命名的嵌入兼容定义。
- 将该定义的 power_in 引脚名设为对应 Value，保留电源身份、几何、编号和可见性。
- 相同 Value 复用定义；不同电源轨不共用被修改的定义；避免名字冲突和往返后重复增殖。
- 不改动原始共享定义，也不改普通器件的隐藏电源引脚。

例如，同一原库符号的 `+5V` 与 `+3V3` 实例会使用不同的兼容定义，旧版不再把它们短接到 `GENERIC`。
兼容定义保存在原理图内部，**不要盲目用原始符号库覆盖这些定义**；更新符号库后须重新核对网络。

## 验证范围与边界

- KiCad 6–10 源/目标 **5×5 矩阵，25 条路径通过**。6/7/8/9 源样例从原始 10 样例生成后，先经对应原生读取器验证，再参与矩阵。
- 因此 6/7→10 路径同时覆盖原始 10→6/7→10 往返；此前四条失败不再跳过，也未标为预期失败。
- 合成工程：两个共用子页、嵌套子页、R1–R6、同 lib_id 的两路电源；比较组件位号/Value/Footprint、具名网络及完整引脚集合。
- 真实 KiCad 6 `complex_hierarchy` 示例升级到 7/10：组件、所有网络的引脚集合和显式网络名保持一致。
  自动生成的网络名可能因 KiCad 版本而变化，因此真实示例不要求这些名称字符串完全一致。
- 补充回归覆盖多单元共用位号、其他工程实例、非默认根页码、重复转换、兼容定义碰撞/复用和源文件不变。
- **V6 格式由 KiCad 7 CLI 的旧格式读取器导出网表，并不等于在 KiCad 6 编辑器中完成保存/重开验收。**
- 局部电源降为全局仍属有损转换；包含未解析文本变量的电源 Value 也需人工检查，告警不会取消。
- 之前已经丢失位号/合并网络的输出不能凭空恢复，必须从完整原工程重新转换。

## 人工安装

1. 备份设计及现有插件，保留旧包。
2. KiCad 6+ 打开「插件与内容管理器 → 从文件安装」，选择 **`kicad-backport-v0.4.9-PCM.zip`**，应用更改后重启。
3. 确认插件版本 `0.4.9`；不要同时启用 PCM 副本和传统手动安装副本。
4. 使用同一个 ZIP 分别检查：KiCad 6/7/8/9/10 自动注册传统 PCB ActionPlugin；即使 9/10 已启用 API，也应由该入口启动；10.99 不注册旧入口并使用 API/IPC。
5. 若宿主创建 Python venv 失败，检查 KiCad 配置的解释器路径；这与 ZIP 格式是否正确是两项问题。

`-manual.zip` 是传统手动安装包，`-test-cases.zip` 是测试设计，不要在 PCM 中选择它们。
`metadata.json` 与 `icon.png` 是 PCM 发布材料，人工从文件安装时无需单独处理。

## 重点人工操作

1. 解压测试样例，用 KiCad 10 打开 `source_V10/issue4.kicad_pro`（不是单独打开子页）。
2. 使用插件的**工程文件夹或 .kicad_pro 工程模式**，从原始工程分别生成 6、7 副本。
3. 在实际 KiCad 6、7 编辑器中打开，依次查看两份共用子页和嵌套子页，核对 **R1–R6** 和页码。
4. 特别检查多单元器件：同一器件各单元的位号必须相同且单元号正确，不能出现人为添加的千位编号。
5. 检查 `+5V` 只连接 R1 的 1 脚，`+3V3` 只连接 R2 的 1 脚，不能出现将两者合并的 `GENERIC` 网络。
6. **保存 → 关闭 → 重新打开 → 再导出网表**，检查编辑器保存后实例、页码和兼容电源定义仍有效。
7. 从这些副本升级回 10，重复步骤 3–6；与原始工程及包内 `netlists/` 对照。
8. 在备份的真实工程中重复检查，并核对 PCB 关联、ERC/DRC 和转换报告。
   合成样例刻意保留未连接引脚，不要求 ERC 数量为零；请与源工程比较新增问题。

本地发布验证保存 `unittest`、原生运行时和矩阵报告；正式 PCM ZIP 仅包含运行所需文件与文档。
报告问题时请附 KiCad 完整版本、插件版本、源/目标版本、转换报告及去除机密的最小复现工程。

## 开发者复跑

```powershell
python -B scripts/schematic_matrix_smoke.py --kicad-root D:/KiCad --output dist/matrix-new-run
```

输出目录必须不存在。任何不一致都会写入报告并返回非零退出码；本轮 25 条路径全部通过。
运行完整原生测试时设置 `KICAD_NATIVE_ROOT`、`KICAD_SOURCE_REPO`、`KICAD7_CLI` 至
`KICAD10_CLI`、`KICAD1099_CLI`、`KICAD9_PYTHON` 和 `KICAD10_PYTHON`，再执行：

```powershell
python -B -m unittest discover -s tests -v
```

路径需按本机调整。省略环境变量会跳过相关原生测试，不应把跳过计为原生验证通过。
正式包使用默认 `stable` 状态构建；发布标签必须与 `plugin.json` 版本一致，本版本为 `V0.4.9`。

## English summary

Release 0.4.9 fixes the four V6/V7 failures recorded during pre-release
validation. The same ZIP selects the startup path by host version:
KiCad 6–10 register the traditional ActionPlugin even when the API server is enabled,
while KiCad 10.99 remains API/IPC-only.
Users of an unpublished 0.4.9 test build must uninstall it before installing the stable release. V6 uses complete legacy
root instance tables; V7+ preserves per-project, per-path local instances. Root
UUIDs and multi-unit references survive. Embedded power variants translate
Value-based net naming into the library-pin naming expected by V6/V7 without
mutating shared definitions. All 25 V6–V10 matrix paths pass, as do genuine V6
multi-unit hierarchy upgrades to V7/V10. V6 is read through the V7 CLI legacy
reader; native V6 editor save/reopen is still a manual gate. Local power scope
and unresolved variable warnings remain. Reconvert from originals, not damaged
outputs. This is the published stable 0.4.9 release; the stated validation boundaries still apply.
