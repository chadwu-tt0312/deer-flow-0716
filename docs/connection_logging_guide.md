# 連線紀錄功能使用指南

## 概述

DeerFlow 提供了完整的連線紀錄功能，可以追蹤所有 HTTP 請求的詳細資訊，包括 URL、headers、代理設定、回應時間等。這對於除錯網路連線問題非常有用。

## 功能特點

- **完整的請求記錄**：記錄所有 HTTP 請求的詳細資訊
- **回應時間追蹤**：測量請求回應時間
- **錯誤記錄**：詳細記錄連線錯誤和異常
- **敏感資訊保護**：自動移除 API 金鑰等敏感資訊
- **可配置性**：可以啟用/停用，並自訂日誌檔案位置
- **JSON 格式**：結構化的日誌格式，便於分析

## 環境變數設定

### 基本設定

```bash
# 啟用連線紀錄
ENABLE_CONNECTION_LOGGING=true

# 指定日誌檔案路徑（可選）
CONNECTION_LOG_FILE=logs/connection.log
```

### 完整範例

```bash
# 連線紀錄配置
ENABLE_CONNECTION_LOGGING=true
CONNECTION_LOG_FILE=logs/connection.log

# 網路配置
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Azure OpenAI 配置
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
```

## 使用方式

### 1. 程式碼中使用

```python
from src.utils.network_config import network_config
from src.utils.http_client import http_client

# 啟用連線紀錄
network_config.enable_connection_logging(True, "logs/my_connection.log")

# 使用 HTTP 客戶端（自動記錄）
response = http_client.get("https://api.example.com/data")
response = http_client.post("https://api.example.com/submit", json={"data": "value"})

# 停用連線紀錄
network_config.enable_connection_logging(False)
```

### 2. 檢查連線紀錄狀態

```python
# 檢查是否已啟用
is_enabled = network_config.is_connection_logging_enabled()
print(f"連線紀錄已啟用: {is_enabled}")

# 取得日誌檔案路徑
log_file = network_config.get_connection_log_file()
print(f"日誌檔案: {log_file}")
```

### 3. 手動記錄連線資訊

```python
# 記錄請求
network_config.log_connection_request(
    method="POST",
    url="https://api.example.com/test",
    headers={"Content-Type": "application/json"},
    data={"test": "data"},
    proxies={"https": "http://proxy.example.com:8080"}
)

# 記錄回應
network_config.log_connection_response(
    url="https://api.example.com/test",
    status_code=200,
    response_headers={"Content-Type": "application/json"},
    response_size=1024,
    response_time=1.5
)

# 記錄錯誤
try:
    # 執行請求
    pass
except Exception as e:
    network_config.log_connection_error(
        url="https://api.example.com/test",
        error=e,
        method="POST"
    )
```

## 日誌格式

### 請求記錄

```json
{
  "timestamp": "2025-01-21T10:30:45.123456",
  "method": "POST",
  "url": "https://api.example.com/test",
  "headers": {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0...",
    "Authorization": "***REDACTED***"
  },
  "proxies": {
    "https": "http://proxy.example.com:8080"
  },
  "timeout": 30.0,
  "data_size": 45,
  "data_preview": "{\"test\": \"data\"}"
}
```

### 回應記錄

```json
{
  "timestamp": "2025-01-21T10:30:46.654321",
  "url": "https://api.example.com/test",
  "status_code": 200,
  "response_headers": {
    "Content-Type": "application/json",
    "Content-Length": "1024"
  },
  "response_size": 1024,
  "response_time_ms": 1530.25
}
```

### 錯誤記錄

```json
{
  "timestamp": "2025-01-21T10:30:45.123456",
  "method": "POST",
  "url": "https://api.example.com/test",
  "error_type": "ConnectionError",
  "error_message": "Failed to establish a new connection",
  "error_details": {
    "args": ["Failed to establish a new connection"],
    "str": "Failed to establish a new connection"
  }
}
```

## 整合範例

### 更新現有模組

如果您想將現有的 `requests` 呼叫更新為使用連線紀錄：

```python
# 舊的方式
import requests
response = requests.get("https://api.example.com/data")

# 新的方式
from src.utils.http_client import http_client
response = http_client.get("https://api.example.com/data")
```

### Grounding Bing Search 整合

```python
from src.tools.grounding_bing_search import GroundingBingSearchAPIWrapper

# 建立搜尋實例
search = GroundingBingSearchAPIWrapper()

# 執行搜尋（自動記錄連線資訊）
results = search.search("聯電 CMOS 技術")
```

## 測試連線紀錄

使用提供的測試腳本：

```bash
# 執行測試
python test_connection_logging.py
```

測試腳本會：
1. 啟用連線紀錄
2. 執行各種 HTTP 請求
3. 顯示日誌檔案內容
4. 停用連線紀錄

## 故障排除

### 常見問題

1. **日誌檔案未建立**
   - 檢查目錄權限
   - 確認 `ENABLE_CONNECTION_LOGGING=true`
   - 檢查日誌目錄是否存在

2. **日誌檔案過大**
   - 定期清理日誌檔案
   - 考慮使用日誌輪轉
   - 在不需要時停用連線紀錄

3. **敏感資訊洩露**
   - 系統會自動移除 API 金鑰等敏感資訊
   - 檢查日誌檔案確認敏感資訊已被正確處理

### 除錯技巧

1. **檢查日誌檔案**
   ```bash
   tail -f logs/connection.log
   ```

2. **分析回應時間**
   ```python
   # 在日誌中搜尋回應時間較長的請求
   grep "response_time_ms" logs/connection.log | sort -k2 -n
   ```

3. **檢查錯誤模式**
   ```python
   # 統計錯誤類型
   grep "error_type" logs/connection.log | sort | uniq -c
   ```

## 效能考量

- **記憶體使用**：連線紀錄會佔用少量記憶體
- **磁碟空間**：日誌檔案會持續增長，需要定期清理
- **CPU 影響**：JSON 序列化會消耗少量 CPU 資源
- **網路影響**：連線紀錄不會影響網路效能

## 安全性注意事項

- **敏感資訊保護**：系統會自動移除 API 金鑰、認證資訊等
- **日誌檔案權限**：確保日誌檔案有適當的存取權限
- **生產環境**：在生產環境中謹慎使用，避免記錄過多資訊

## 相關檔案

- [網路配置工具](../src/utils/network_config.py)
- [HTTP 客戶端](../src/utils/http_client.py)
- [測試腳本](../test_connection_logging.py)
- [環境變數範例](../env.example) 