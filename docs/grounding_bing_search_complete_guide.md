# Grounding Bing Search 完整指南

## 概述

Grounding Bing Search 是 DeerFlow 新增的搜尋引擎選項，基於 Azure OpenAI 的 Bing Grounding 功能，提供更準確和相關的搜尋結果。此功能特別適合需要高品質搜尋結果的應用場景。

## 功能特點

- **高品質搜尋結果**：利用 Azure OpenAI 的 Bing Grounding 技術
- **多語言支援**：支援繁體中文、簡體中文、英文等多種語言
- **可配置參數**：可自訂搜尋結果數量、市場區域、語言設定等
- **自動資源管理**：自動清理 Assistant 和 Thread 資源
- **完整錯誤處理**：詳細的異常處理和日誌記錄
- **連線紀錄整合**：自動記錄所有 API 請求的詳細資訊

## 前置需求

### 1. Azure 資源

您需要以下 Azure 資源：

- **Azure AD 應用程式**：用於 API 認證
- **Azure OpenAI 服務**：提供 Bing Grounding 功能
- **Bing Search 連線**：在 Azure OpenAI 中設定的搜尋連線

### 2. 必要資訊

請準備以下資訊：

- Azure AD 應用程式 ID (Client ID)
- Azure AD 應用程式密碼 (Client Secret)
- Azure AD 租用戶 ID (Tenant ID)
- Bing Search 連線 ID (Connection ID)
- API 基礎 URL (可選，有預設值)

## 設定步驟

### 1. 設定環境變數

在您的 `.env` 檔案中新增以下變數：

```bash
# 搜尋引擎選擇
SEARCH_API=grounding_bing

# Azure AD 認證
GROUNDING_BING_CLIENT_ID=your_azure_client_id
GROUNDING_BING_CLIENT_SECRET=your_azure_client_secret
GROUNDING_BING_TENANT_ID=your_azure_tenant_id

# Bing Search 連線
GROUNDING_BING_CONNECTION_ID=your_bing_connection_id

# API 基礎 URL (可選)
GROUNDING_BING_BASE_URL=http://172.16.128.4:11009/api/projects/searchProject

# 連線紀錄配置（可選）
ENABLE_CONNECTION_LOGGING=true
CONNECTION_LOG_FILE=logs/connection.log
```

### 2. 配置檔案設定

在 `conf.yaml` 檔案中設定搜尋引擎配置：

```yaml
SEARCH_ENGINE:
  engine: grounding_bing
  # Grounding Bing Search 特定配置
  market: zh-tw        # 搜尋市場區域
  set_lang: zh-hant    # 搜尋語言設定
```

### 3. 驗證設定

執行以下命令驗證設定是否正確：

```bash
# 執行範例程式
python examples/grounding_bing_search_example.py
```

## 使用方式

### 1. 在 DeerFlow 中使用

設定完成後，Grounding Bing Search 將自動成為預設的搜尋引擎，在進行背景調查時會使用此引擎。

### 2. 程式化使用

```python
from src.tools.grounding_bing_search import GroundingBingSearchTool

# 建立工具
tool = GroundingBingSearchTool(
    max_results=10,
    market="zh-tw",
    set_lang="zh-hant"
)

# 執行搜尋
results = tool.invoke("您的搜尋查詢")
```

### 3. 直接使用 API

```python
from src.tools.grounding_bing_search import GroundingBingSearchAPIWrapper

# 建立 API 包裝器
api_wrapper = GroundingBingSearchAPIWrapper()

# 執行搜尋
results = api_wrapper.search("聯電 CMOS 技術", max_results=5)
```

### 4. 與連線紀錄整合

Grounding Bing Search 已經整合了連線紀錄功能，會自動記錄所有 API 請求：

```python
from src.utils.network_config import network_config

# 啟用連線紀錄
network_config.enable_connection_logging(True, "logs/grounding_bing.log")

# 執行搜尋（自動記錄連線資訊）
from src.tools.grounding_bing_search import GroundingBingSearchAPIWrapper
api_wrapper = GroundingBingSearchAPIWrapper()
results = api_wrapper.search("聯電 CMOS 技術")

# 停用連線紀錄
network_config.enable_connection_logging(False)
```

## 實作架構

### 1. 核心模組

#### 1.1 API 包裝器 (`src/tools/grounding_bing_search/grounding_bing_search_api_wrapper.py`)
- **GroundingBingSearchConfig**: 配置類別，管理 Azure AD 認證和搜尋參數
- **GroundingBingSearchAPIWrapper**: API 包裝器，處理 Azure OpenAI API 調用
  - 自動權杖管理（包含過期處理）
  - 完整的 API 請求處理
  - 搜尋結果解析和格式化
  - 自動資源清理（Assistant 和 Thread）
  - 整合連線紀錄功能

#### 1.2 LangChain 工具 (`src/tools/grounding_bing_search/grounding_bing_search_tool.py`)
- **GroundingBingSearchTool**: 實作 LangChain 工具介面
  - 支援字串和字典輸入格式
  - 統一的結果格式化
  - 完整的錯誤處理
  - 與現有搜尋工具架構整合

### 2. 配置整合

#### 2.1 搜尋引擎枚舉 (`src/config/tools.py`)
- 新增 `GROUNDING_BING = "grounding_bing"` 選項

#### 2.2 搜尋工具整合 (`src/tools/search.py`)
- 新增 Grounding Bing Search 支援
- 從環境變數讀取配置
- 支援自訂市場區域和語言設定

### 3. 檔案結構

```
src/
├── tools/
│   └── grounding_bing_search/
│       ├── __init__.py
│       ├── grounding_bing_search_api_wrapper.py  # API 包裝器
│       └── grounding_bing_search_tool.py         # LangChain 工具
├── config/
│   └── tools.py                                  # 搜尋引擎配置
└── utils/
    ├── network_config.py                         # 網路配置
    └── http_client.py                            # HTTP 客戶端

tests/
└── unit/
    └── tools/
        └── test_grounding_bing_search.py         # 單元測試

examples/
└── grounding_bing_search_example.py              # 使用範例

docs/
└── grounding_bing_search_complete_guide.md       # 本文件
```

## 技術特點

### 1. 架構設計
- **模組化設計**: 清晰的 API 包裝器和工具分離
- **配置驅動**: 支援環境變數和配置檔案設定
- **錯誤處理**: 完整的異常處理和日誌記錄
- **資源管理**: 自動清理 Azure OpenAI 資源
- **連線紀錄**: 整合完整的 HTTP 請求記錄

### 2. 整合性
- **LangChain 相容**: 完全實作 LangChain 工具介面
- **現有架構**: 無縫整合到現有搜尋引擎架構
- **向後相容**: 不影響現有功能
- **網路配置**: 支援代理伺服器和自訂 User-Agent

### 3. 可配置性
- **多語言支援**: 支援繁體中文、簡體中文、英文等
- **市場區域**: 可自訂搜尋市場區域
- **結果數量**: 可調整搜尋結果數量
- **API 端點**: 可自訂 API 基礎 URL

## 環境變數

| 變數名稱 | 說明 | 必填 | 預設值 |
|---------|------|------|--------|
| `SEARCH_API` | 搜尋引擎選擇 | 是 | `tavily` |
| `GROUNDING_BING_CLIENT_ID` | Azure AD 應用程式 ID | 是 | - |
| `GROUNDING_BING_CLIENT_SECRET` | Azure AD 應用程式密碼 | 是 | - |
| `GROUNDING_BING_TENANT_ID` | Azure AD 租用戶 ID | 是 | - |
| `GROUNDING_BING_CONNECTION_ID` | Bing Search 連線 ID | 是 | - |
| `GROUNDING_BING_BASE_URL` | API 基礎 URL | 否 | `http://172.16.128.4:11009/api/projects/searchProject` |
| `ENABLE_CONNECTION_LOGGING` | 啟用連線紀錄 | 否 | `false` |
| `CONNECTION_LOG_FILE` | 連線紀錄檔案路徑 | 否 | `logs/connection.log` |

## 搜尋結果格式

### 基本搜尋結果

```json
{
  "query": "聯電 CMOS 技術",
  "results": [
    {
      "title": "聯電 CMOS 技術發展歷程",
      "snippet": "聯電在 CMOS 技術領域的發展...",
      "url": "https://example.com/article1",
      "source": "example.com"
    },
    {
      "title": "聯電最新製程技術",
      "snippet": "聯電最新的 CMOS 製程技術...",
      "url": "https://example.com/article2",
      "source": "example.com"
    }
  ],
  "total_results": 2,
  "search_time": 1.5
}
```

### 詳細搜尋結果

```json
{
  "query": "聯電 CMOS 技術",
  "results": [
    {
      "title": "聯電 CMOS 技術發展歷程",
      "snippet": "聯電在 CMOS 技術領域的發展...",
      "url": "https://example.com/article1",
      "source": "example.com",
      "metadata": {
        "published_date": "2024-01-15",
        "author": "技術專家",
        "category": "技術分析"
      }
    }
  ],
  "search_metadata": {
    "market": "zh-tw",
    "language": "zh-hant",
    "max_results": 10,
    "search_time_ms": 1500
  }
}
```

## 故障排除

### 常見問題

1. **認證失敗**
   - 檢查 Azure AD 應用程式 ID、密碼和租用戶 ID 是否正確
   - 確認 Azure AD 應用程式有適當的權限
   - 檢查權杖是否過期

2. **連線錯誤**
   - 檢查網路連線是否正常
   - 確認是否需要設定代理伺服器
   - 查看連線紀錄檔案了解詳細錯誤

3. **搜尋結果為空**
   - 檢查搜尋查詢是否正確
   - 確認市場區域和語言設定
   - 檢查 Bing Search 連線是否正常

4. **API 限制**
   - 檢查 Azure OpenAI 服務配額
   - 確認 API 版本是否支援
   - 查看錯誤訊息中的詳細資訊

### 除錯技巧

1. **啟用連線紀錄**

   ```bash
   # 在 .env 檔案中設定
   ENABLE_CONNECTION_LOGGING=true
   CONNECTION_LOG_FILE=logs/grounding_bing.log
   ```

2. **檢查環境變數**

   ```python
   import os
   print(f"Client ID: {os.getenv('GROUNDING_BING_CLIENT_ID')}")
   print(f"Tenant ID: {os.getenv('GROUNDING_BING_TENANT_ID')}")
   print(f"Connection ID: {os.getenv('GROUNDING_BING_CONNECTION_ID')}")
   ```

3. **測試 API 連線**

   ```python
   from src.tools.grounding_bing_search import GroundingBingSearchAPIWrapper
   
   try:
       api_wrapper = GroundingBingSearchAPIWrapper()
       results = api_wrapper.search("test query", max_results=1)
       print("API 連線成功")
   except Exception as e:
       print(f"API 連線失敗: {e}")
   ```

4. **查看連線紀錄**

   ```bash
   tail -f logs/grounding_bing.log
   ```

## 效能考量

- **權杖快取**: 系統會自動快取 Azure AD 權杖，避免重複請求
- **資源清理**: 自動清理 Assistant 和 Thread 資源，避免資源洩漏
- **連線池**: 使用 HTTP 連線池提高效能
- **錯誤重試**: 自動重試失敗的請求
- **結果快取**: 可考慮實作搜尋結果快取機制

## 安全性注意事項

- **認證資訊**: 確保 Azure AD 認證資訊安全存儲
- **API 金鑰**: 避免在程式碼中硬編碼 API 金鑰
- **網路安全**: 使用 HTTPS 連線確保資料傳輸安全
- **權限最小化**: 只授予必要的 Azure AD 應用程式權限
- **日誌安全**: 連線紀錄會自動移除敏感資訊

## 最佳實踐

1. **環境變數管理**
   - 使用 `.env` 檔案管理敏感資訊
   - 避免將認證資訊提交到版本控制
   - 定期輪換 API 金鑰

2. **錯誤處理**
   - 實作適當的錯誤處理機制
   - 記錄詳細的錯誤資訊
   - 提供用戶友好的錯誤訊息

3. **效能優化**
   - 適當設定搜尋結果數量
   - 使用連線紀錄監控效能
   - 考慮實作快取機制

4. **監控和維護**
   - 定期檢查連線紀錄
   - 監控 API 使用量
   - 及時更新依賴套件

## 相關檔案

- [API 包裝器](../src/tools/grounding_bing_search/grounding_bing_search_api_wrapper.py)
- [LangChain 工具](../src/tools/grounding_bing_search/grounding_bing_search_tool.py)
- [搜尋工具整合](../src/tools/search.py)
- [單元測試](../tests/unit/tools/test_grounding_bing_search.py)
- [使用範例](../examples/grounding_bing_search_example.py)
- [網路配置指南](./network_and_connection_guide.md)

## 更新日誌

- **v1.0.0** - 初始版本
  - 支援 Azure OpenAI Bing Grounding 功能
  - 完整的 API 包裝器和 LangChain 工具
  - 自動權杖管理和資源清理
  - 多語言和市場區域支援
  - 整合連線紀錄功能
  - 完整的錯誤處理和測試覆蓋 