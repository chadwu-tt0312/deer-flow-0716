# 開發腳本說明

這個文件說明了 DeerFlow 專案中可用的開發腳本及其使用方法。

## 腳本概覽

### 後端 API 服務

#### `server.py`

後端 API 服務啟動腳本，支援從環境變數讀取配置。

**使用方法：**

```bash
python server.py [--host HOST] [--port PORT] [--log-level LEVEL]
```

**環境變數配置：**
- `NEXT_PUBLIC_API_URL`：API 服務的完整 URL（例如：`http://192.168.1.180:8000/api`）

**功能：**
- 自動從 `NEXT_PUBLIC_API_URL` 解析 host 和 port
- 支援命令列參數覆蓋環境變數
- 詳細的日誌輸出和錯誤處理

### 前端開發服務器

#### `web/scripts/dev-with-warmup.js`

根據環境變數配置啟動前端開發服務器並執行預熱功能。

**使用方法：**

```bash
cd web
pnpm dev:warmup
```

**環境變數配置：**
- `DEER_FLOW_URL`：前端應用的完整 URL（例如：`http://192.168.1.180:3000/chat`）

**功能：**
- 從 `DEER_FLOW_URL` 解析 host、port 和 path
- 自動設定 Next.js 的 hostname 和 port
- 檢測服務器準備狀態
- 自動執行路由預熱
- 支援多主機檢測
- 顯示配置資訊和訪問 URL

#### `web/scripts/warm-up.js`

預熱腳本，自動訪問路由進行預編譯。

**使用方法：**

```bash
cd web
node scripts/warm-up.js
```

**功能：**
- 自動訪問 `/chat` 和主頁路由
- 自動檢測本機 IP 地址
- 支援多主機檢測（localhost, 127.0.0.1, 自動檢測的 IP）
- 重試機制和錯誤處理
- 避免首次訪問的編譯等待時間

#### `web/scripts/env-test.js`
環境變數測試腳本，診斷 .env 檔案載入問題。

**使用方法：**
```bash
# 從 web 目錄執行
pnpm env:test
```

**功能：**
- 檢查 .env 檔案路徑（專案根目錄）
- 測試 dotenv 模組載入
- 顯示當前環境變數狀態
- 診斷環境變數載入問題

## 環境變數配置

### 後端 API 配置

```bash
# .env 檔案
NEXT_PUBLIC_API_URL="http://192.168.1.180:8000/api"
```

### 前端應用配置

```bash
# .env 檔案
DEER_FLOW_URL="http://192.168.1.180:3000/chat"
```

## 推薦使用方式

### 1. 分別啟動（推薦用於開發）

```bash
# 終端 1：啟動後端 API 服務
python server.py

# 終端 2：啟動前端開發服務器
cd web && pnpm dev:warmup
```

### 2. 前端開發（含預熱）

```bash
cd web && pnpm dev:warmup
```

### 3. 快速啟動（使用預設配置）

```bash
# 後端
python server.py

# 前端
cd web && pnpm dev
```

## 腳本說明

### `dev:warmup` 功能

- **開發服務器啟動**：根據環境變數配置啟動 Next.js 開發服務器
- **預熱功能**：自動執行路由預熱，避免首次訪問的編譯等待時間
- **環境配置**：支援從 `DEER_FLOW_URL` 解析 host、port 和 path
- **多主機支援**：支援多種主機配置（localhost, 127.0.0.1, 自定義 IP）

### 環境變數 vs 硬編碼

所有腳本都優先使用環境變數配置，如果環境變數未設定或解析失敗，則使用預設值：
- 後端預設：`localhost:8000`
- 前端預設：`localhost:3000`

## 注意事項

1. **環境變數**：確保 `.env` 檔案存在於根目錄並正確配置
2. **依賴安裝**：確保已安裝所有必要的依賴
3. **端口衝突**：確保指定的端口未被其他服務佔用
4. **網路配置**：如果使用非 localhost 的 IP，確保網路配置正確

## 故障排除

### 常見問題

1. **無法載入 .env 檔案**
   - 檢查 `.env` 檔案是否存在於根目錄
   - 確認檔案權限
   - 使用 `pnpm env:test` 診斷環境變數載入問題

2. **端口被佔用**
   - 檢查端口是否被其他服務使用
   - 修改環境變數中的端口配置

3. **服務啟動失敗**
   - 檢查依賴是否完整安裝
   - 查看錯誤日誌進行診斷

### 日誌輸出

所有腳本都會提供詳細的日誌輸出，包括：
- 配置資訊
- 服務啟動狀態
- 錯誤訊息
- 訪問 URL

使用這些腳本可以簡化開發環境的設定和啟動流程，提高開發效率。
