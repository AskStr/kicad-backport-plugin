# KiCad Backport

版權 (C) 问星

版本 0.0.2

KiCad Backport 用於建立可由舊版 KiCad 開啟的工程或檔案副本。原始工程不會被覆蓋。

## 語言

外掛會盡可能跟隨 KiCad 目前選擇的語言。如果沒有找到 KiCad 語言設定，則使用系統語言。

目前介面支援：英文、簡體中文、繁體中文、法文、德文、義大利文。

## 跨平台相容

支援系統：

- Windows x64 和 Windows ARM64
- macOS Intel 和 Apple Silicon
- Linux x64 和 Linux ARM64

外掛會自動選擇目前系統對應的轉換器。

## 支援目標版本

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## 安裝

1. 關閉 KiCad。
2. 將整個 `kicad_backport` 資料夾複製到 KiCad 的 `plugins` 資料夾。
3. 對舊版 KiCad，也將同一資料夾複製到 `scripting/plugins`。
4. 重新啟動 KiCad。
5. 執行 `建立 KiCad 相容副本`。

## 使用

1. 選擇 KiCad 檔案或工程資料夾。
2. 選擇不同的輸出檔案或資料夾。
3. 選擇目標 KiCad 版本。
4. 點擊 `轉換`。

請在目標 KiCad 版本中檢查轉換後的副本，再用於分享或製造。
