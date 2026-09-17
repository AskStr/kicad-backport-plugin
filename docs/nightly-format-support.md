# KiCad 10.99 nightly compatibility / 每夜版兼容范围

## Verified snapshot / 核对基线

- Date: **2026-09-17 UTC**.
- Official KiCad master: `5ba95b2054efc54aeee48197f4a2d72e28ffbad8`.
- Symbol library / schematic: **20260830**.
- Board / footprint: **20260901**.
- Worksheet: **20231118**; design rules: **1**.


The local KiCad repository is now checked out on `master`, fast-forwarded to
`origin/master`, with a clean working tree. It is not a shallow clone. The
previous verified September 7 baseline `be90a7e200` is an ancestor of this
snapshot, with **390 commits** in the full comparison range. Format review uses
the serializer/parser and settings diff across that range, not a date-filtered
subset of commits.

本地源码已按用户要求切换并快进到 `master`，与 `origin/master` 一致且工作树干净。
历史完整、非浅克隆；9 月 7 日基线之后的 390 个提交均在核对范围内。

### Changes since the previous snapshot / 本次增量

- `19174c2b8b` (September 11): PCB format `20260901` introduces
  `drill_chart`, `drill_map`, and `setup.drill_symbol_profile`. Charts share the
  ordinary table's cached cells/geometry; maps save generation parameters, not
  pre-rendered graphics. The format date is **not** the feature's commit date.
- PCB table UUIDs were introduced at `20250907`; KiCad 9 supports tables but
  rejects that field. Converting a chart to a table therefore also requires
  removing the table UUID and its group references on KiCad 9. Cell UUIDs remain.
- `d939d0134c` (September 13): bus-vector expansion preserves leading zeros,
  **without a schematic format-version bump**. For example, `DATA[00..03]`
  now names `DATA00` through `DATA03`, not `DATA0` through `DATA3`. Older-target
  conversions warn about connectivity rather than guessing a safe label rewrite.
- Symbol/schematic format headers, worksheet and DRU versions are unchanged.
  Jumper-group and grid-item refactoring does not introduce new serialized
  syntax in this range; the inspected project settings changes require no new
  JSON-schema rewrite.

源码依据：`pcbnew/pcb_io/kicad_sexpr/pcb_io_kicad_sexpr.{h,cpp}` 及对应 parser、
`pcbnew/drill/drill_symbol_profile.cpp`、`eeschema/sch_file_versions.h`、
`common/project/net_settings.cpp`，均来自上述固定提交。

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
| `drill_chart` before `20260901` | KiCad 9/10: keep cached text/layout as a static `table`; before table support (`20240202`, including KiCad 4–8): remove with warning / 保留静态表格或删除并告警 |
| Chart `row_shapes` / regeneration | Remove symbol-shape cache, filters and regeneration settings with explicit loss warnings; text-based marks remain in cached cells / 图形符号及自动更新能力丢失，文字缓存保留 |
| PCB table UUID before `20250907` | Remove table UUID and its group references, including ordinary footprint tables; retain cell UUIDs / 兼容 KiCad 9 的表格解析器 |
| `drill_map` / `drill_symbol_profile` before `20260901` | Remove unsupported map/profile and dangling group references; do not remove actual pads, vias or drills / 删除钻孔标记图及符号配置，不删除实体钻孔 |
| Zero-padded schematic bus vectors | Preserve labels/aliases/sheet pins and warn on older snapshot targets, including legacy and same-header conversions / 保留文本并告警，不承诺旧版网络连接等价 |


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

The upstream PCB fixtures pinned to `5ba95b2054` are `via_stacks.kicad_pcb`,
`line_ending_zone_flood/line_ending_zone_flood.kicad_pcb`, and
`line_ending_drc/line_ending_drc_fail.kicad_pcb`, under `qa/data/pcbnew/`.
Native tests check loading and preservation of track/via counts. Structural
tests additionally check endpoints, fill, layer, UUIDs, group references,
font-width round trips, source-file preservation, and project/DRU conversion.

Verified on this machine: **65 unit tests**, including the optional native
cases and Python 3.8 grammar checks. Native checks include 21 pinned upstream
PCB conversions/loads plus 7 drill-documentation conversions/loads across
KiCad 4/5/6/7/8/9/10. KiCad 9/10 also re-save the static tables and verify their
cached text. Compatibility, i18n, KiCad 5 board-load smoke tests and the
7-case real-fixture smoke suite pass.

The separate C++ reference-message parity smoke also passes; the Python and C++
implementations expose matching downgrade-warning prefixes for their shared
rules.

The updated installed KiCad 10.99 executable is commit
`f7ca620278609187e348cc7bcc7eaf2b847e7ffc` (September 17 UTC) and declares
PCB format `20260901`. It natively loads the drill-chart/map fixture and exports
the documentation layer to SVG. The executable is slightly older than the
pinned source commit, but both use the same board, schematic and symbol format
versions covered here.

**Verification limit:** native load/export and older-version round trips do not
constitute exhaustive visual, electrical, DRC, or manufacturing validation, nor
validation on every operating system. Drill charts downgraded to static tables
must still be reviewed before fabrication because automatic regeneration and
symbol marks are intentionally unavailable in older targets.

**验证边界：**更新后的本机 10.99 已按 `20260901` 原生加载并导出钻孔文档夹具；
但原生加载、导出和旧版回读仍不等于完整的视觉、电气、DRC 或制造验收，也不代表
所有操作系统均已验收。降级后的静态钻孔表失去自动更新及图形符号，制造前必须复核。
