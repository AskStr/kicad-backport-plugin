# KiCad Backport

版權 (C) 问星

版本 0.3.0

KiCad Backport 用於建立可由舊版 KiCad 開啟的工程或檔案副本。原始工程不會被覆蓋。

0.3.0 版本支援目前 KiCad 10.99 每夜版儲存的工程，並可輸出相容 KiCad 10、KiCad 9、KiCad 8 或 KiCad 7 的副本。

## 0.3.0 版本亮點

- 大幅優化轉換執行效率，在大型工程測試中約提升 3 倍。
- 優化 S 表達式解析、格式化和樹遍歷邏輯，更好地處理大型檔案。
- 合併降級規則處理，減少重複全量遍歷。
- 改進 KiCad 7 Python 相容性，並增加打包完整性檢查。

## 語言

外掛會盡可能跟隨 KiCad 目前選擇的語言。如果沒有找到 KiCad 語言設定，則使用系統語言。

目前介面支援：英文、簡體中文、繁體中文、法文、德文、義大利文。

## 跨平台相容

KiCad Backport 的轉換核心已全部用 Python 實作，並在外掛行程內直接執行，正常使用不再需要依平台提供獨立轉換器二進位檔。

支援系統：

- Windows
- macOS
- Linux

## 支援目標版本

支援輸入版本：

- KiCad 10.99 每夜版
- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

支援輸出目標：

- KiCad 10
- KiCad 9
- KiCad 8
- KiCad 7

## 安裝

1. 關閉 KiCad。
2. 將整個 `kicad-backport` 資料夾複製到 KiCad 使用者 `plugins` 資料夾。
3. 對 KiCad 10.99 及更新的 API 外掛，請使用帶版本號的使用者外掛目錄，例如 `C:\Users\<你>\Documents\KiCad\10.99\plugins`。
4. 在 KiCad 10.99 中，必須在偏好設定中啟用 KiCad API/API server，否則 KiCad 不會識別或載入 API 外掛。
5. 對舊版 KiCad，也將同一資料夾複製到 `scripting/plugins`。
6. 重新啟動 KiCad。
7. 執行 `建立 KiCad 相容副本`。

在 KiCad 10.99 中，API 外掛不會從已安裝程式的內建腳本目錄載入，例如 `share/kicad/scripting/plugins`；請使用使用者 `plugins` 資料夾，並確認已啟用 KiCad API/API server。

## 使用

1. 選擇 KiCad 檔案或工程資料夾。
2. 選擇不同的輸出檔案或資料夾。
3. 選擇目標 KiCad 版本。
4. 點擊 `轉換`。

請在目標 KiCad 版本中檢查轉換後的副本，再用於分享或製造。
