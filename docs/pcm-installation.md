# PCM 安装与检查更新 / Install and update

## 用户只需配置一次

兼容 **KiCad 6–10.99**。在「插件与内容管理器 → 管理仓库」添加：

```text
https://github.com/AskStr/kicad-backport-plugin/releases/latest/download/repository.json
```

然后刷新，选择 **KiCad Backport → 安装 → 应用挂起的更改**，安装后重启 KiCad。
以后只需在 PCM **刷新 → 更新 / 更新全部 → 应用更改**，更新后重启；不需要重新输入
URL、下载索引或手动处理图标。已订阅这个地址的用户无需改配置。

本插件尚未收录到 KiCad official repository，所以首次仍需添加一次上述仓库。
Round Tracks 已被官方收录，其用户省去了这一步；不能仅通过插件代码跳过官方审核。
“从文件安装”只安装 ZIP，不等于订阅仓库。旧的本地安装若无法关联，请先备份，
在 PCM 卸载后从仓库重新安装。不要同时保留会重复注册的手动安装副本。

## 各 KiCad 版本的运行前提

| KiCad | 运行入口 | PCM 检查更新 |
|---|---|---|
| 6 / 7 / 8 | 内置 Python、pcbnew、wxPython ActionPlugin | 同一订阅地址和版本历史 |
| 9 / 10，API 关闭 | 保留上述旧入口 | 同上 |
| 9 / 10，API 开启 | Python API 操作，不重复注册旧入口 | 同上 |
| 10.99 | 必须启用 KiCad API，配置可用 Python | 同上 |

插件最低 Python **3.8**；外部 Python 需提供 Tk 或 wxPython，API 环境还需 venv/pip。
转换核心不新增第三方运行依赖。PCM 的列表、图标、兼容性筛选和更新由 KiCad 管理，
不会新增插件内后台更新器，也不会自行改写用户的 PCM 配置或安装数据库。

所有当前发布版本的 PCM 兼容范围保持 `6.0`–`10.99`，标识符保持
`com.askstar.kicad.backport`。同一版本重发不会触发更新提示；插件内容变更应提升版本号。
这次对 V0.4.7 的修订只简化发布工具，已公开 ZIP 字节和下载哈希保持不变。

## 维护者：不再手动拼 URL 或上传多个索引

**正常发布：**修改版本号并提交，推送对应的 `V<版本>` 标签。
GitHub Actions 的 **Publish PCM update** 自动完成：

1. 获取上一正式 Release 的历史索引；获取失败就停止，避免丢失历史。
2. 打包、校验并自动生成下载地址、版本列表、图标和更新时间戳。
3. 上传完整资产，全部就绪后才发布为最新正式 Release。
4. 匿名验证固定订阅地址、每个版本的下载大小和 SHA-256。

**补跑发布：**在 GitHub「Actions → Publish PCM update → Run workflow」输入现有标签。
已发布标签会直接复用原 ZIP，不会偷偷重打包或覆盖安装包。工作流串行运行，拒绝将
旧版本重新设为 latest。请不要再手动发布一个没有更新索引的“最新”Release。

### 本地打包也只需一条命令

安装构建依赖后执行：

```sh
python -m pip install -r requirements-dev.txt
python package_plugin.py
```

参考 Round Tracks，输出 PCM ZIP、`dist/metadata.json` 和 `dist/icon.png`。
需要同时准备现有自建更新源时：

```sh
python package_plugin.py --repository
```

下载地址自动按本项目的 `V<版本>` 标签生成，历史自动合并。独立的
`package_repository.py` 仍保留给自定义部署，不是日常必需步骤。

V0.4.7 已经发布，不应因文档或打包工具修改而重建同版本 ZIP。复用已发布归档：

```sh
python package_plugin.py --archive dist/kicad-backport-v0.4.7-PCM.zip --repository
```

`--format zip` / `--format all` 仍支持传统手动安装包。

## 官方仓库接入（可选，不影响当前 PCM 更新）

生成的 `metadata.json` 和 `icon.png` 是官方接入材料，不需要用户安装这两个文件。
按 KiCad 官方流程，将它们放入官方 metadata 仓库的
`packages/com.askstar.kicad.backport/`，验证并提交 merge request。
官方审核通过并同步后，用户才能在默认官方仓库直接找到本插件。
包名/命名空间仍需官方审核；不擅自更换现有标识符，以免破坏已安装用户的更新关联。

官方维护版本目录；GitHub 负责托管 ZIP。单纯在 GitHub 发布新版本，不会自动完成
官方 metadata 的审核与更新。当前自建订阅源已自动化，不必等待官方收录才能检查更新。

## 验证与边界

```sh
python -m unittest discover -s tests
python scripts/pcm_native_smoke.py --kicad-root D:/KiCad
python scripts/pcm_repository_smoke.py --url https://github.com/AskStr/kicad-backport-plugin/releases/latest/download/repository.json
```

覆盖范围包括版本历史/不可变归档、图标、Schema、HTTP 下载和更新索引、命令行、
Python 3.8 语法与 KiCad 6–10.99 的兼容声明。Windows KiCad 6–10 的原生注册及 PNG
解码、10.99 官方 Schema 已验证。未声称所有操作系统/nightly 或完整 PCM GUI
安装→更新→卸载交互都已验收。资源图标可能受 KiCad 自身缓存节流影响，不需要改缓存文件。

## English quick guide

Add the fixed JSON URL above once in PCM **Manage Repositories**, refresh, and install
KiCad Backport from that repository. Later, use PCM **Refresh → Update → Apply Changes**
and restart KiCad. Existing subscribers keep the same URL. KiCad 6–10.99 use the same
feed; only the plugin runtime prerequisites differ as listed above. Python 3.8+ is required.

Tag pushes trigger **Publish PCM update**, which restores history, builds and validates,
uploads all assets, and publishes only after everything is complete. Use **Run workflow**
to retry an existing tag; its already-published ZIP is reused, never rebuilt. A single local
`python package_plugin.py` generates ZIP + official metadata/icon; add `--repository` for
the existing custom feed. `--archive <published.zip>` preserves a released archive.

Official-repository inclusion, like Round Tracks, requires a separate reviewed submission.
The exported metadata/icon support that process; they do not mean the plugin has already
been accepted. No background self-updater or automatic user-configuration changes are added.
