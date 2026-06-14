# KiCad Backport

版權 (C) 问星

版本 0.4.1

KiCad Backport 用於為舊版 KiCad 建立相容工程或檔案副本。它支援現代
S 表達式檔案與 KiCad 5 時代 legacy 檔案之間的降級和升級流程，原始工程
不會被覆蓋。

轉換核心為純 Python 實作。KiCad 5 時代的 Python 會透過外部 Python 3
直譯器啟動同一套 GUI，因此舊版 KiCad 也能使用目前轉換引擎。

## 目前能力

- 支援轉換整個工程資料夾或單一 KiCad 檔案。
- 在存在轉換路徑時，支援 PCB、原理圖、符號庫、封裝、圖框、設計規則、
  工程檔，以及 legacy 工程/符號庫/原理圖檔案。
- 可將現代 `.kicad_sch`、`.kicad_sym`、`.kicad_pro` 轉為 KiCad 5
  時代的 `.sch`、`.lib` / `.dcm`、`.pro`。
- 可將 legacy `.sch`、`.lib`、`.dcm`、`.pro` 升級為較新目標版本使用的
  KiCad 檔案。
- 會保留工程本地符號庫、規範化庫表，並在需要時重建 KiCad 6+ 原理圖層級
  與符號實例資訊。
- 對 V6/V7/V8 PCB 輸出，會寫入相容的工程本地 `.kicad_prl` 可見項和層設定。
- GUI 和 CLI 都可產生 JSON 轉換報告。

## 支援目標版本

GUI 可選目標：KiCad 10、9、8、7、6、5.1、5.0、4。

轉換核心還支援部分原始數字格式目標，例如開發版 PCB/封裝格式
`20260603` 和 `20260521`。

支援輸入系列包括目前 KiCad 10.99 每夜版、KiCad 10 到 KiCad 5 檔案，以及
legacy `.sch`、`.lib`、`.dcm`、`.pro` 檔案。

## 語言

外掛會盡可能跟隨 KiCad 目前選擇的語言。它會讀取 KiCad 5 風格的
`kicad_common` 等設定檔、常見 KiCad 語言環境變數，最後回退到作業系統
介面語言。

目前介面支援：英文、簡體中文、繁體中文、法文、德文、義大利文。

## 平台相容

支援系統：Windows、macOS、Linux。

GUI 會優先嘗試 wxPython，並在不可用時回退到 tkinter。KiCad 5 legacy 模式
會優先使用 tkinter，並把偵測到的 KiCad 語言和設定路徑傳給外部 Python 3
行程。

## 安裝

1. 關閉 KiCad。
2. 將整個 `kicad-backport` 資料夾複製到 KiCad 使用者 `plugins` 資料夾。
3. 對 KiCad 10.99 及更新的 API 外掛，請使用帶版本號的使用者外掛目錄，例如
   `C:\Users\<你>\Documents\KiCad\10.99\plugins`。
4. 在 KiCad 10.99 中，必須在偏好設定中啟用 KiCad API/API server。
5. 對舊版 KiCad，也將同一資料夾複製到 `scripting/plugins`。
6. 重新啟動 KiCad。
7. 執行 `建立 KiCad 相容副本`。

在 KiCad 10.99 中，API 外掛不會從已安裝程式的內建腳本目錄載入，例如
`share/kicad/scripting/plugins`；請使用使用者 `plugins` 資料夾，並確認已啟用
KiCad API/API server。

## 使用

1. 選擇 KiCad 檔案或工程資料夾。
2. 選擇不同的輸出檔案或資料夾。
3. 選擇目標 KiCad 版本。
4. 點擊 `轉換`。

輸出會自動追加目標後綴，例如 `_V7`、`_V5` 或 `_V10_99`。對 V5 目標，現代
原理圖和符號庫副檔名會自動改為 legacy 副檔名。

命令列入口：

```powershell
python plugin\plugin.py --input <input-path> --output <output-path> --target-version 5.0 --report report.json
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

請在目標 KiCad 版本中檢查轉換後的副本，再用於分享或製造。
