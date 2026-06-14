# KiCad Backport

版權 (C) 問星/askstar

版本 0.4.3

KiCad Backport 用於為舊版 KiCad 目標版本建立相容的專案或檔案副本。它面向
現代 S 表達式檔案與 KiCad 5 時代 legacy 檔案之間的實際降級和升級流程。
原始專案不會被覆寫。

轉換核心使用純 Python 實作，正常外掛使用時在行程內執行。KiCad 5 時代的
Python 會透過外部 Python 3 直譯器啟動同一套 GUI，因此舊版 KiCad 安裝也能
繼續使用目前轉換引擎。

## 翻譯

- [English](README.en.md)
- [简体中文](README.zh_CN.md)
- [繁體中文](README.zh_TW.md)
- [Français](README.fr.md)
- [Deutsch](README.de.md)
- [Italiano](README.it.md)

## 目前能力

- 支援轉換整個 KiCad 專案資料夾或單一 KiCad 檔案。
- 在目標格式存在轉換路徑時，支援 PCB、原理圖、符號庫、封裝、圖框、設計
  規則、專案檔，以及 legacy 專案/符號庫/原理圖檔案。
- 對 V5 目標，可將現代 `.kicad_sch`、`.kicad_sym`、`.kicad_pro` 轉為
  KiCad 5 時代的 `.sch`、`.lib` / `.dcm`、`.pro`。
- 可將 legacy `.sch`、`.lib`、`.dcm`、`.pro` 升級回較新目標使用的 KiCad
  S 表達式或 JSON 專案檔。
- 保留專案本地符號庫，並為舊目標正規化庫表。
- 在需要時為現代專案輸出重建 KiCad 6+ 原理圖階層和符號實例資料。
- 對 V6/V7/V8 PCB 輸出，寫入相容的專案本地 `.kicad_prl` 可見項和層設定。
- 當 zstd 解壓可用時，將 PCB/封裝內嵌的 3D 模型資源提取到專案本地 `3D/`
  檔案。核心包含一個小型內建 zstd 影格解碼器，支援 raw/RLE 區塊；完整壓
  縮區塊可使用 Python 標準函式庫 `compression.zstd`、系統 `libzstd` 或
  可選 `zstandard` 套件。
- 對較新版 PCB、封裝、原理圖、符號、圖框和設計規則中舊 KiCad 不接受的
  功能進行相容性改寫。
- 透過 CLI 要求或從 GUI 啟動時，可寫出 JSON 轉換報告。

部分現代 KiCad 功能在轉換到很舊格式時天然會有損失。轉換器會移除、改寫或
近似處理不支援的結構，並為這些變更報告警告。

## 支援目標版本

GUI 目標列表：

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7
- KiCad 6
- KiCad 5.1
- KiCad 5.0
- KiCad 4

轉換核心還接受受支援的原始數字格式目標，包括 `20260603`、`20260521` 等
開發版 PCB/封裝格式。

支援輸入系列包括：

- 目前 KiCad 10.99 每夜版檔案
- KiCad 10、9、8、7、6、5 檔案
- KiCad legacy `.sch`、`.lib`、`.dcm`、`.pro` 檔案

## 語言

外掛會盡可能跟隨 KiCad 目前選擇的語言。它還會檢查 KiCad 5 風格設定檔
（例如 `kicad_common`）、常見 KiCad 語言環境變數，最後回退到作業系統介面
語言。

支援的介面語言：

- 英文
- 簡體中文
- 繁體中文
- 法文
- 德文
- 義大利文

修改 KiCad 語言後，請重新啟動 KiCad 或重新開啟外掛視窗。

## 平台相容

支援系統：

- Windows
- macOS
- Linux

GUI 會優先嘗試 wxPython，並在不可用時回退到 tkinter。KiCad 5 legacy 模式
中，啟動器會優先使用 tkinter，並把偵測到的 KiCad 語言和設定路徑傳給外部
Python 3 行程。

## 安裝

1. 關閉 KiCad。
2. 將整個 `kicad-backport` 資料夾複製到 KiCad 使用者 `plugins` 資料夾。
3. 對 KiCad 10.99 及更新的 API 外掛，請使用帶版本號的使用者外掛目錄，例如
   `C:\Users\<你>\Documents\KiCad\10.99\plugins`。
4. 在 KiCad 10.99 中，於偏好設定中啟用 KiCad API/API server；否則 KiCad
   不會發現或載入 API 外掛。
5. 對舊版 KiCad，也將同一資料夾複製到 KiCad 的 `scripting/plugins` 資料夾。
6. 重新啟動 KiCad。
7. 開啟 KiCad 外掛管理器或應用工具列/選單，尋找 `建立 KiCad 相容副本`。

如果看不到該操作，請確認資料夾已複製到目前 KiCad 版本使用的外掛資料夾中。
在 KiCad 10.99 中，API 外掛不會從已安裝程式的內建腳本目錄載入，例如
`share/kicad/scripting/plugins`；請使用使用者 `plugins` 資料夾，並確認已啟用
KiCad API/API server。

## 在 KiCad 中使用

1. 執行 `建立 KiCad 相容副本`。
2. 選擇專案資料夾或受支援的 KiCad 檔案。
3. 選擇一個不同的輸出檔案或資料夾。
4. 選擇目標 KiCad 版本。
5. 點擊 `轉換`。

輸出會寫入帶目標後綴的路徑，例如 `_V7`、`_V5` 或 `_V10_99`。對 V5 目標，
現代原理圖和符號庫副檔名會自動改為 legacy 副檔名。

## 從命令列使用

帶參數執行啟動器：

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
```

列出 GUI 支援的目標：

```powershell
python plugin\plugin.py --list-targets
```

## 建置安裝包

在倉庫根目錄建置外掛壓縮包：

```powershell
.\build.ps1 -Format all
```

```sh
./build.sh --format all
```

支援的打包格式為 `zip`、`tar.gz` 和 `all`。

常用環境變數：

- `KICAD_BACKPORT_PYTHON`：KiCad 5 啟動器使用的 Python 3 可執行檔。
- `KICAD_BACKPORT_GUI_BACKEND`：`wx`、`tk`、`auto` 或 `legacy`。
- `KICAD_BACKPORT_LANGUAGE`：明確介面語言覆寫。
- `KICAD_BACKPORT_KICAD_CONFIG_PATH`：用於語言偵測的 KiCad 設定檔或資料夾。

## 重要說明

- 一律選擇不同於原始專案的輸出路徑。
- 在分享或用於生產前，請在目標 KiCad 版本中檢查轉換後的副本。
- 很舊的目標無法保留所有現代功能。請檢視轉換報告和警告資訊。
