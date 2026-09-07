# KiCad 10.99 nightly compatibility / 每夜版兼容范围

## Verified snapshot / 核对基线

- Date: **2026-09-07**.
- Official KiCad master: `be90a7e20034bdbc902cc4a363998b5f8b6a2ca4`.
- Symbol library / schematic: **20260830**.
- Board / footprint: **20260831**.
- Worksheet: **20231118**; design rules: **1**.

The `10.99` core target refers to this snapshot, not every historical or future
nightly executable. Older nightlies may reject these version headers. Inputs
with newer, unverified format versions are reported as such. Source projects
are not overwritten; all lossy changes are reported in the conversion report.
The GUI target list is unchanged; `10.99` remains available through the core/CLI.

`10.99` 档位代表上述源码快照，不代表所有过去或未来的每夜版。更早的 nightly
可能拒绝这些版本头；未来格式会明确告警。没有升级发布版本、构建安装包或修改
GUI。请阅读转换报告，特别是涉及铜层几何、制造约束和旧版不具备的功能时。

## Conversion policy / 转换策略

| Feature / 特性 | Older target / 旧版目标处理 |
| --- | --- |
| `custom_property` | Remove with warning; retain ordinary `property` fields / 删除并告警，不误删普通字段 |
| `start_shape`, `end_shape` | Bake arrows/circles/squares into compatible graphics; shorten the body; preserve layer, connectivity and group membership / 烘焙图元、缩短线身、保留层、网络和组成员 |
| `generated (type via_stitch)` | Before 20260816, convert to a group; retain physical vias/tracks / 退化为组，保留实际实体 |
| `generated (type via_stack)` | Before 20260830, convert to a group; retain physical vias/tracks / 退化为组，保留实际实体 |
| Groups before KiCad 6 | Remove the grouping metadata, not the physical items / 删除分组元数据而非过孔或走线 |
| Bold stroke width | Across 20260826, migrate baked width ↔ base width with the upstream 1.6 multiplier; exclude outline fonts and automatic widths / 双向迁移，不影响轮廓字体和自动线宽 |
| Footprint `exclude_from_sim` | Before 20260828, remove the attr atom and variant child; preserve supported schematic/symbol flags / 分别处理封装属性和变体，不误删原理图已有功能 |
| Microvia DRC constraints | Before 20260830, remove unsupported `microvia_stack_depth` / `microvia_aspect_ratio` constraints; keep supported constraints and surrounding comments; remove rules left without constraints / 删除不支持约束并明确提示这些制造检查不再执行 |
| Project JSON settings | Preserve the JSON; warn about unavailable microvia presets and changed BOM/IPC-2581 export semantics / 保留 JSON，对预设和导出语义差异告警 |
| Schematic polygons | Preserve compatible `polyline` geometry and explicit closure / 保留兼容多边形，不直接删除 |

Line-ending conversion is a geometry approximation, not preservation of the
parametric editing feature. Circles use 32 segments. Bezier length/orientation
uses 128 sampling intervals while retaining a cubic body. Footprint transforms
are baked after new geometry is generated. The existing non-uniform transform
approximation warning still applies. Legacy schematic note drawings cannot
retain fills or individual stroke styles; that loss is separately reported.

线端转换不保留参数化编辑能力。圆形采用 32 段；贝塞尔长度/方向用 128 个区间
估计，线身仍保留为三次曲线。封装变换在新图元生成后烘焙；非均匀变换继续有
近似告警。旧 `.sch` 的 Notes 图形不能保留填充和独立线型，另行报告损失。

**Removing an unsupported DRC constraint does not make a design safe to
manufacture. Review the report and re-check the affected constraints using a
version/tool that supports them.**

**删除旧版不支持的 DRC 约束不代表设计已经满足制造条件。请审阅报告，并用支持
这些约束的版本或工具重新检查。**

## Python compatibility / Python 兼容性

Supported runtime minimum: **Python 3.8**. This is the plugin's support policy,
not KiCad 6's upstream build minimum.
This applies to the conversion core, GUI launcher, and CLI, including the new
nightly conversion paths. `plugin.json` declares the same minimum. No new
third-party runtime dependency is required; the optional newer zstd providers
remain optional. Packaging/schema validation uses separate development
dependencies, not KiCad's runtime environment.

最低支持的运行时调整为 **Python 3.8**；这是插件的支持下限，不是 KiCad 6 自身的构建下限。
新增 nightly 转换逻辑、GUI 启动器与命令行均维持该下限；打包和 Schema 验证的
开发依赖不属于插件运行要求。

Run these checks with the interpreter being certified; no development packages
are needed. On a newer interpreter the syntax test also parses runtime/smoke
sources using Python 3.8 grammar. This static check alone cannot certify standard
library API compatibility, so testing on the actual old interpreter is required.

```sh
python -m unittest discover -s tests -p test_python_compat.py
python -m unittest discover -s tests -p test_nightly_formats.py
python scripts/compat_smoke.py
python scripts/i18n_smoke.py
python scripts/reference_parity_smoke.py
```

Verified on September 7, 2026 with KiCad 6.0.11's bundled Python **3.9.14**:
all **30** runtime/nightly tests, including the optional native cases configured
below. The compatibility, i18n, reference-parity, and seven real-fixture smoke
cases also passed on this interpreter. Earlier checks on Python 3.6.8 were
exploratory; Python versions below 3.8 are no longer part of the support contract.
The Python 3.8 grammar check is not a claim of native Python 3.8 runtime testing.

实测 KiCad 6 自带 Python 3.9.14 通过 30 项运行时/nightly 测试（含下述原生验证），
以及兼容性、多语言、规则对照和 7 项真实工程检查。测试覆盖命令行导入、最新 PCB
转 KiCad 6、源文件保留和报告生成，另通过插件注册/模块导入检查。
此前 Python 3.6.8 的测试仅作为探索记录，不再承诺支持低于 3.8 的版本。
Python 3.8 目前有语法检查，但未进行该版本解释器的原生运行验收；
也未声称覆盖所有平台的 Python 或 wxPython 发行组合。

## Reproducible verification / 可重复验证

Full regression suite (no KiCad installation required; install the development
requirements for the packaging/schema tests):

```sh
python -m unittest discover -s tests
python scripts/compat_smoke.py
```

Optional native tests are in `tests/test_nightly_formats.py`. Set executable
paths for PCB load and schematic/symbol SVG export tests. The larger Windows
installation matrix also accepts a local KiCad Git repository and an installation
root containing versioned directories. It reads the pinned commit with `git show`;
it does not check out branches or modify the upstream repository.

```powershell
# Replace these example paths with your own installations.
$env:KICAD10_PYTHON = 'C:\KiCad\10.0\bin\python.exe'
$env:KICAD10_CLI = 'C:\KiCad\10.0\bin\kicad-cli.exe'
$env:KICAD_SOURCE_REPO = 'C:\src\kicad'
$env:KICAD_NATIVE_ROOT = 'C:\KiCad'
python -m unittest discover -s tests -p test_nightly_formats.py
```

The pinned upstream PCB fixtures are `via_stacks.kicad_pcb`,
`line_ending_zone_flood/line_ending_zone_flood.kicad_pcb`, and
`line_ending_drc/line_ending_drc_fail.kicad_pcb`, under `qa/data/pcbnew/`.
Native tests check loading and preservation of track/via counts. Structural
tests additionally check endpoints, fill, layer, UUIDs, group references,
font-width round trips, source-file preservation, and project/DRU conversion.

Verified on this machine: all 54 tests, including the optional native cases;
21 upstream PCB conversions/loads across KiCad 4/5/6/7/8/9/10; schematic and
symbol SVG exports in KiCad 7/8/9/10; existing compatibility, i18n, reference
parity, real-fixture, and KiCad 5 smoke tests.

**Verification limit:** the installed 10.99 executable is
`10.99.0-2335-g1899bad41c`, predating these new formats. Latest-output version
headers and preservation are verified against upstream source and structural
tests, not by loading them in a matching current nightly executable. Native
loading does not constitute exhaustive visual, electrical, DRC, or manufacturing
validation, nor validation on every operating system.

**验证边界：**本机 10.99 可执行文件早于新增格式；最新输出通过源码对照及结构测试
验证，不能宣称已在匹配的最新 nightly 中原生加载。原生加载成功也不等于完整的
视觉、电气、DRC 或制造验收，亦不代表所有操作系统均已验收。
