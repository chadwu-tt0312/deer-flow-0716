# DeerFlow 網路配置與連線紀錄完整指南

## 概述

本指南涵蓋 DeerFlow 的網路配置功能和連線紀錄系統，幫助您在特定網路限制環境中順利運行應用程式，並提供完整的連線除錯能力。

## 功能概覽

### 網路配置功能
- **自動代理偵測**：根據 URL 協議和端點自動判斷是否需要網路配置
- **代理伺服器支援**：支援 HTTP 和 HTTPS 代理伺服器
- **User-Agent 自訂**：可自訂 User-Agent 字串
- **快取機制**：自動快取配置以提高效能
- **無縫整合**：與現有的 HTTP 請求無縫整合

### 連線紀錄功能
- **完整的請求記錄**：記錄所有 HTTP 請求的詳細資訊
- **回應時間追蹤**：測量請求回應時間
- **錯誤記錄**：詳細記錄連線錯誤和異常
- **敏感資訊保護**：自動移除 API 金鑰等敏感資訊
- **可配置性**：可以啟用/停用，並自訂日誌檔案位置
- **JSON 格式**：結構化的日誌格式，便於分析

## 環境變數設定

### 網路配置

```bash
# 代理伺服器設定
# 格式: http://DOMAIN%5Cuser:pwd@proxy.ccc.com:8080
# 注意: %5C 是反斜線 \ 的 URL 編碼
HTTP_PROXY=http://DOMAIN%5Cuser:pwd@proxy.ccc.com:8080
HTTPS_PROXY=http://DOMAIN%5Cuser:pwd@proxy.ccc.com:8080

# User-Agent 設定
# 當 AZURE_OPENAI_ENDPOINT 或 BASIC_MODEL__BASE_URL 使用 HTTPS 時會自動套用
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/135.0.3179.54
```

### 連線紀錄配置

```bash
# 啟用連線紀錄功能，記錄所有 HTTP 請求的詳細資訊
ENABLE_CONNECTION_LOGGING=false

# 連線紀錄檔案路徑
CONNECTION_LOG_FILE=logs/connection.log
```

### 完整範例

```bash
# 網路配置
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# 連線紀錄配置
ENABLE_CONNECTION_LOGGING=true
CONNECTION_LOG_FILE=logs/connection.log

# Azure OpenAI 配置
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
```

## 觸發條件

### 網路配置觸發條件

網路配置會在以下情況下自動套用：

1. **HTTPS URL**：任何使用 HTTPS 協議的 URL
2. **Azure OpenAI 端點**：URL 匹配 `AZURE_OPENAI_ENDPOINT` 環境變數
3. **基本模型端點**：URL 匹配 `BASIC_MODEL__BASE_URL` 環境變數

### User-Agent Hook 機制

在特定網路限制環境中，當 `AZURE_OPENAI_ENDPOINT` 或 `BASIC_MODEL__BASE_URL` 使用 HTTPS (SSL) 時，系統會自動在所有 LLM 請求中注入 User-Agent header。

## 使用方式

### 1. 基本網路配置使用

```python
from src.utils.network_config import network_config

# 取得請求配置
url = "https://api.example.com/test"
config = network_config.get_request_config(url)

# 使用配置進行請求
import requests
response = requests.get(url, **config)
```

### 2. 更新現有 Headers

```python
# 現有的 headers
headers = {
    "Authorization": "Bearer token123",
    "Content-Type": "application/json"
}

# 更新 headers，加入 User-Agent
updated_headers = network_config.update_headers(headers)
```

### 3. 連線紀錄使用

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

### 4. 檢查連線紀錄狀態

```python
# 檢查是否已啟用
is_enabled = network_config.is_connection_logging_enabled()
print(f"連線紀錄已啟用: {is_enabled}")

# 取得日誌檔案路徑
log_file = network_config.get_connection_log_file()
print(f"日誌檔案: {log_file}")
```

### 5. 手動記錄連線資訊

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

Grounding Bing Search 工具已經更新為使用新的 HTTP 客戶端，會自動記錄所有連線資訊：

```python
from src.tools.grounding_bing_search import GroundingBingSearchAPIWrapper

# 建立搜尋實例
search = GroundingBingSearchAPIWrapper()

# 執行搜尋（自動記錄連線資訊）
results = search.search("聯電 CMOS 技術")
```

### LLM 整合

所有透過 `get_llm_by_type()` 建立的 LLM 實例都會自動帶入 User-Agent：

```python
from src.llms.llm import get_llm_by_type

# 自動帶入 User-Agent 的 LLM
llm = get_llm_by_type("basic")
response = llm.invoke("Hello, world!")
```

## 日誌格式

### 連線請求記錄

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

### 連線回應記錄

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

### 連線錯誤記錄

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

## 測試連線紀錄

使用提供的測試腳本：

```bash
# 執行快速測試
python test_quick_connection.py

# 執行完整測試
python test_connection_logging.py
```

測試腳本會：
1. 啟用連線紀錄
2. 執行各種 HTTP 請求
3. 顯示日誌檔案內容
4. 停用連線紀錄

## 故障排除

### 常見問題

1. **代理連線失敗**
   - 檢查代理伺服器 URL 格式是否正確
   - 確認認證資訊是否正確
   - 檢查網路連線是否正常

2. **User-Agent 未生效**
   - 確認環境變數名稱是否正確
   - 檢查 URL 是否為 HTTPS 或匹配特定端點
   - 查看日誌確認配置是否被載入

3. **日誌檔案未建立**
   - 檢查目錄權限
   - 確認 `ENABLE_CONNECTION_LOGGING=true`
   - 檢查日誌目錄是否存在

4. **日誌檔案過大**
   - 定期清理日誌檔案
   - 考慮使用日誌輪轉
   - 在不需要時停用連線紀錄

### 除錯技巧

1. **啟用詳細日誌**

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **檢查環境變數**

   ```python
   import os
   print(os.getenv('HTTP_PROXY'))
   print(os.getenv('HTTPS_PROXY'))
   print(os.getenv('USER_AGENT'))
   print(os.getenv('ENABLE_CONNECTION_LOGGING'))
   ```

3. **測試網路配置**

   ```python
   from src.utils.network_config import network_config
   
   url = "https://api.example.com/test"
   config = network_config.get_request_config(url)
   print(f"網路配置: {config}")
   ```

4. **檢查日誌檔案**

   ```bash
   tail -f logs/connection.log
   ```

5. **分析回應時間**

   ```bash
   # 在日誌中搜尋回應時間較長的請求
   grep "response_time_ms" logs/connection.log | sort -k2 -n
   ```

6. **檢查錯誤模式**

   ```bash
   # 統計錯誤類型
   grep "error_type" logs/connection.log | sort | uniq -c
   ```

## 效能考量

- **快取機制**：代理和 User-Agent 設定會自動快取，避免重複解析
- **條件式套用**：只有符合條件的 URL 才會套用網路配置
- **記憶體使用**：連線紀錄會佔用少量記憶體
- **磁碟空間**：日誌檔案會持續增長，需要定期清理
- **CPU 影響**：JSON 序列化會消耗少量 CPU 資源
- **網路影響**：連線紀錄不會影響網路效能

## 安全性注意事項

- **認證資訊**：代理伺服器 URL 中的認證資訊會以明文形式存在環境變數中
- **網路安全**：確保代理伺服器連線使用適當的安全協議
- **日誌記錄**：避免在日誌中記錄包含認證資訊的完整代理 URL
- **敏感資訊保護**：系統會自動移除 API 金鑰、認證資訊等
- **日誌檔案權限**：確保日誌檔案有適當的存取權限
- **生產環境**：在生產環境中謹慎使用，避免記錄過多資訊

## 相關檔案

- [網路配置工具](../src/utils/network_config.py)
- [HTTP 客戶端](../src/utils/http_client.py)
- [LLM 配置](../src/llms/llm.py)
- [完整測試腳本](../test_connection_logging.py)
- [快速測試腳本](../test_quick_connection.py)
- [環境變數範例](../env.example)

## 更新日誌

- **v1.0.0** - 初始版本
  - 支援 HTTP/HTTPS 代理
  - 支援自訂 User-Agent
  - 自動偵測 HTTPS URL 和特定端點
  - 快取機制提升效能
  - 支援完整的 HTTP 請求記錄
  - 支援回應時間追蹤
  - 支援錯誤記錄
  - 自動敏感資訊保護
  - 可配置的日誌檔案位置 