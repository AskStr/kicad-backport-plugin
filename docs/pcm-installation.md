# PCM 安装、检查更新与发布 / PCM installation and updates

## 适用范围

从 **0.4.5** 开始，`kicad-backport-v<版本>-PCM.zip` 是统一的 KiCad **6.0–10.99**
插件与内容管理器（PCM）安装包。转换目标版本与这里的“运行插件的 KiCad 版本”是两回事。

| 运行环境 | 入口与前提 |
|---|---|
| KiCad 6 / 7 / 8 | 内置 Python、pcbnew、wxPython ActionPlugin；不需要 API |
| KiCad 9 / 10，API 关闭 | 同上，保留旧版入口 |
| KiCad 9 / 10，API 开启 | `plugin.json` 的 Python API 操作；不重复注册 ActionPlugin |
| KiCad 10.99 | API/Python 操作；必须启用 KiCad API，并设置可用的外部 Python |

API 使用的 Python 需要 **Python 3.8+**、`venv`、`pip`，以及 `tkinter` / `_tkinter` /
Tcl/Tk（或可用的 wxPython）。仅有 Python 可执行文件不代表具备 GUI 组件；Linux 发行版通常
将 Tk 拆为独立系统包。插件的 `requirements.txt` 不要求第三方 pip 包，但 KiCad 自身的
虚拟环境初始化仍可能需要网络。安装后如 API 被 PCM 提示开启，请检查 Python 配置并完整重启 KiCad。

该插件处理磁盘上的文件，不需要 `kicad-python`，不会主动连接 IPC 或修改当前板子。
保持原有界面和转换核心；API 仅负责发现和启动独立 Python 操作。

## 用户安装

1. 从维护者发布页下载带 **`-PCM.zip`** 后缀的安装包，**不要解压**。
2. 从 KiCad 项目管理器打开“插件与内容管理器”，选择“从文件安装”，选中这个 ZIP。
3. 应用安装操作，完整关闭并重新启动 KiCad 和已打开的编辑器。
4. 在 PCB 编辑器的插件菜单/工具栏查找 `Create KiCad Backport` / `创建 KiCad 兼容副本`。
   API 操作在宿主支持的其他范围也可用；旧 ActionPlugin 仅在 PCB 编辑器中提供。
5. 如此前手动复制过插件，请先自行备份并移走旧副本，避免手动副本和 PCM 副本各注册一个按钮。

PCM 自动将 `plugins/` 内容安装到当前 KiCad 版本的第三方目录，包目录类似
`third-party/plugins/com_askstar_kicad_backport/`。不要在 ZIP 内再嵌套这个包名目录。
不同 KiCad 大版本的 PCM 安装和设置相互独立，需要分别安装。

`kicad-backport.zip` 和 `.tar.gz` 仍是**传统手动安装包**，不能用“从文件安装”导入。
KiCad 4/5 继续使用原手动安装方案，不在 PCM 6–10.99 范围内。

## 检查更新：必须添加在线仓库

本地 ZIP 提供安装能力，**并不自动订阅更新源**。维护者发布仓库后：

1. 在 PCM 的“管理仓库”中添加维护者提供的完整 `repository.json` URL。
2. 刷新仓库/重新打开 PCM，等待仓库索引下载。
3. 对已安装插件查看可用版本，选择更新并应用；更新后完整重启 KiCad。
4. 如果最初从文件安装后仍标记为本地包或未关联仓库，请先备份，再在 PCM 卸载本地包，
   从新增仓库重新安装一次。不要通过手工修改 PCM 安装数据库强行关联。

同一个包必须始终使用 `com.askstar.kicad.backport` 标识。更新按数值版本判断，重新发布
相同版本或只改下载地址不会成为新版本。API 开关变化后同样需要重启，才能切换运行入口。

插件没有后台联网、自更新线程、自动覆盖安装目录或自动修改用户 KiCad 配置的行为。
检查、安装、卸载及更新均由 PCM 负责。离线、HTTP/证书错误或仓库尚未发布时，不能检查在线更新。

## 开发者构建

在仓库根目录安装**仅构建/测试**所需依赖（不会打入插件运行包）：

```sh
python -m pip install -r requirements-dev.txt
python package_plugin.py --format pcm
```

上述命令产生 `dist/kicad-backport-v0.4.6-PCM.zip`。不加参数的 `python package_plugin.py` 默认仅生成 PCM ZIP。输出是可复现 ZIP：固定时间、权限和条目顺序。
源码 `plugin.json` 与 `plugin/backport_core.py` 的版本必须一致。支持 `--status testing` 等
PCM 状态覆盖；默认 `stable`。同一输出文件已有不同内容时拒绝覆盖，正式发布后必须升版本。
本地试验应使用 `--output dist/trial-PCM.zip` 等独立路径，不要复用正式版本文件。

```sh
python package_plugin.py --format all
```

| format | 输出 |
|---|---|
| `pcm`（默认） | 仅统一 PCM ZIP |
| `zip` | PCM ZIP、传统 ZIP、解包后的手动目录 |
| `tar.gz` | 传统 tar.gz、解包后的手动目录 |
| `all` | PCM ZIP、传统 ZIP、传统 tar.gz、解包后的手动目录 |

所有打包逻辑由 Python 执行，不依赖 Shell、PowerShell、外部 `zip` 或 `tar`。
只保留两个职责独立的打包入口，不再提供额外转发脚本：
- `package_plugin.py`：生成 PCM 和传统手动安装包。
- `package_repository.py`：读取已有 PCM ZIP，生成更新仓库索引，不重复打包插件。

`tests/` 保留 Python 回归测试，`scripts/` 仅保留 Python 冒烟测试脚本。

构建不会清空整个 `dist/`，保留旧发布 ZIP 和更新仓库历史。解包后的便利目录不做递归清理，
可能留有开发过程中已删除的旧文件；正式分发请使用按当前源码重新生成的 ZIP/tar.gz。
`--version` / `-v` 只校验版本，不再打印与包内容不一致的版本号。

## 生成仓库与发布

以下 URL 是**发布规划示例，不代表已上线**。如使用不同域名、GitHub tag 或路径，必须替换为
自己的最终公开地址；`--download-url` 必须指向 ZIP 原始字节，不能是 Release HTML 页面。

```sh
python package_repository.py --archive dist/kicad-backport-v0.4.6-PCM.zip --output dist/pcm-repository --base-url https://askstr.github.io/kicad-backport-plugin/pcm --download-url https://github.com/AskStr/kicad-backport-plugin/releases/download/v0.4.6/kicad-backport-v0.4.6-PCM.zip
```

生成器完全离线，生成：

- `packages.json`：历史版本来源，供下一次发布合并；不能丢失。
- `packages-<SHA256>.json`：不可变在线索引，与 `packages.json` 内容一致。
- `repository.json`：指向不可变索引，包含 SHA-256 和递增的 `update_timestamp`。

发布顺序：

1. 上传带版本号的 PCM ZIP，确认可公开下载且不是认证/HTML 页面。
2. 上传 `packages-<SHA256>.json` 和作为历史备份的 `packages.json`。
3. **最后**替换公开的 `repository.json`，避免用户取得指向未上传内容的索引。
4. 保留旧 ZIP 和旧哈希索引，让仍持有旧根索引缓存的用户继续下载。
5. 将最终 `repository.json` URL 提供给用户，并在实际 PCM 中验收首次安装、更新与卸载。

工具不会创建 GitHub Release、上传、推送提交或自动配置 Pages。仓库根索引应允许重新验证缓存，
避免 CDN 对 `repository.json` 使用永久不可变缓存；哈希索引和版本化 ZIP 可以长期缓存。

下一版本发布时递增源版本，并使用相同输出目录自动读取历史，或明确传入：

```sh
python package_repository.py --archive dist/kicad-backport-v0.4.6-PCM.zip --output dist/pcm-repository --previous-packages previous/packages.json --base-url https://askstr.github.io/kicad-backport-plugin/pcm --download-url https://github.com/AskStr/kicad-backport-plugin/releases/download/v0.4.6/kicad-backport-v0.4.6-PCM.zip
```

同版本 ZIP 字节变化会被拒绝；保持历史包和数值版本排序。内容未变时根索引和时间戳保持不变；
内容变化时自动递增时间戳。可用 `--timestamp <Unix秒>` 做可重复发布测试，但必须大于已有变更
索引的时间戳并满足官方日期格式。

回滚请发布一个**更高版本号**的修复包或在 PCM 手动重新安装旧版本，不要篡改已经发布版本的 ZIP。
生成器不负责并发发布锁；同一个仓库应串行发布，并以最新的 `packages.json` 为历史输入。

## 验证与限制

```sh
python -m unittest discover -s tests -v
python scripts/compat_smoke.py
python scripts/i18n_smoke.py
python scripts/pcm_native_smoke.py --kicad-root D:/KiCad
```

2026-09-06 验证范围：

- 单元测试覆盖双 Schema、实际 PCM 目录解包、运行入口、跨平台配置定位、损坏配置、无 pcbnew、
  CLI、可复现构建、历史保留、版本不可变、哈希与时间戳、路径/清单校验及手动包兼容。
- Windows 原生 KiCad **6.0.11 / 7.0.11 / 8.0.9 / 9.0.7 / 10.0.4** 的内置 Python/
  pcbnew 实际 ActionPlugin 注册及运行代码导入通过；API 开/关下的注册数量符合预期。
- 对本机 **10.99.0-2335-g1899bad41c** 的官方 PCM/API Schema 校验通过。其 IPC-only 安装不含
  `python.exe`，不把“无 pcbnew 安全导入”测试声称为原生 10.99 PCM GUI 安装成功。
- 现有转换、国际化、参考规则与真实夹具 smoke 均需保持通过。

**尚不能据此宣称**：所有操作系统和全部 10.99 nightly 均已实机验收；正式在线仓库已上线；
PCM GUI 首次安装→联网更新→卸载全流程已实机通过。开发版可继续改变插件协议，需要跟随验证。

---

## English quick guide

Use `kicad-backport-v0.4.6-PCM.zip` with **Plugin and Content Manager → Install from File**.
Do not unpack it. Restart KiCad afterwards. Remove old manual copies yourself to avoid duplicate actions.
The unified package supports KiCad 6–10.99: legacy pcbnew/wx on 6–8 and API-disabled 9–10;
Python API actions on API-enabled 9+. KiCad 10.99 requires the API and a usable Python environment with
Tk (or wxPython), venv and pip. No third-party pip dependency is required by the converter.

A local ZIP does **not** subscribe to updates. Add the publisher's live `repository.json` URL in
**Manage Repositories**, refresh PCM, then apply an available update and restart. If a local install is
not associated with that repository, back it up, uninstall through PCM, and install from the repository.
There is no background self-updater and no automatic change to user settings.

Build with `python -m pip install -r requirements-dev.txt`, then `python package_plugin.py --format all`.
All packaging runs in Python; no shell, external ZIP utility or tar executable is required.
`python package_plugin.py` defaults to PCM only; use `--format zip` for PCM + traditional ZIP,
or `--format all` to include tar.gz. The only packaging entrypoints are `package_plugin.py`
(plugin archives) and `package_repository.py` (update indexes from an existing PCM ZIP).
Traditional `kicad-backport.zip` / `.tar.gz` remain manual-install archives, not PCM inputs.

Use `package_repository.py --help` and the commands above to generate offline indexes. The example
public URLs are **not a statement that a repository has been deployed**. Upload the release ZIP first,
the immutable hash-named package index next, and `repository.json` last. Preserve previous releases
and indexes. Keep release versions immutable, bump versions for fixes, and serialize publishing.

Native Windows registration was tested on KiCad 6.0.11 through 10.0.4; 10.99 schema validation and
IPC-only import were checked. Full native PCM GUI installation/update/uninstallation, a live repository,
and every OS/nightly build are not claimed as verified.
