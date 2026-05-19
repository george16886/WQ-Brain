# WQ-Brain 自動化工具

這是一個用於 WorldQuant Brain 平台的自動化腳本集，支援自動模擬 (Simulate)、抓取 (Scrape) 以及提交 (Submit) Alphas 策略。

## 功能特性

- **自動化模擬 (`main.py`)**: 讀取 `parameters.py` 和 `commands.py` 中生成的參數設定，使用多執行緒自動向 WQBrain 提交模擬請求，並將結果存為 CSV 格式。支援自動登入與 Cookie 存續，避免頻繁的生物辨識驗證。
- **抓取達標策略 (`scrape_alphas.py`)**: 抓取帳號內符合特定條件 (如 Sharpe > 1.25, Fitness > 1, 未提交等) 的 Alpha 策略，輸出結果至 CSV，方便後續篩選。
- **自動提交策略 (`submit_alphas.py`)**: 讀取抓取出來的 CSV 檔案，自動將符合條件且相關性低於限制的策略提交至系統中。
- **策略庫 (`commands.py`, `database.py`)**: 內建多種生成 Alphas 語法的函式庫，包含常見的價量計算與 101 Alphas 等論文策略。

## 檔案結構

- `main.py`: 主程式，負責 Alpha 的模擬與結果寫入。
- `scrape_alphas.py`: 抓取滿足條件且未提交的 Alphas 列表。
- `submit_alphas.py`: 讀取 CSV 將抓取出來的 Alphas 自動提交。
- `parameters.py`: 存放給 `main.py` 模擬用的 `DATA` 列表。
- `commands.py`: 存放大量用來生成 WorldQuant Brain Alpha 表達式的函式。
- `database.py`: 紀錄各類可用於生成的參數及欄位常數。
- `credentials.json`: 使用者的 WQBrain 登入帳密設定。
- `cookies.pkl`: 自動存放的登入 session cookies，用於跳過重複生物辨識。

## 安裝與設定

1. 安裝必要的 Python 套件：
   ```bash
   pip install requests pandas
   ```

2. 設定登入憑證：
   初次執行程式時，若找不到 `credentials.json`，終端機會提示您手動輸入 WorldQuant Brain 的 **Email** 與 **Password**，並自動替您儲存成 `credentials.json` 檔案。
   *(您也可以自行建立 `credentials.json` 檔案：)*
   ```json
   {
       "email": "your_email@example.com",
       "password": "your_password"
   }
   ```
   *注意：初次登入或 Cookie 失效時，程式碼將要求你手動透過瀏覽器完成生物辨識驗證，隨後 Cookie 將會被儲存至 `cookies.pkl`，以便後續自動登入。*

## 使用方式

### 1. 執行 Alpha 模擬

在 `parameters.py` 中的 `DATA` 變數設定你要測試的 Alpha 參數陣列，然後執行：

```bash
python main.py
```
這會啟動多個執行緒自動進行模擬，並將結果儲存至 `data/` 目錄下 (例如 `api_123456.csv`)。

### 2. 抓取達標的 Alphas

若要找出帳戶內已經模擬完成、達到提交標準且尚未提交的策略，執行：

```bash
python scrape_alphas.py
```
腳本會抓取相關紀錄，並輸出成 `data/alpha_scrape_result_<timestamp>.csv`。

### 3. 自動提交 Alphas

使用上述抓取到的 CSV 檔案，執行以下指令以自動送出符合條件的 Alpha：

```bash
python submit_alphas.py data/alpha_scrape_result_<timestamp>.csv
```

## 注意事項

- **API 頻率限制**: 執行緒數量已進行調控 (例如 `main.py` 中 `max_workers=3`)，以避免觸發 WorldQuant Brain 的反爬蟲機制導致 Session 提早過期。
- **安全**: 請妥善保管 `credentials.json` 與 `cookies.pkl`，切勿上傳至公開的程式碼儲存庫中。專案中的 `.gitignore` 已經有忽略這些檔案以防外洩。
