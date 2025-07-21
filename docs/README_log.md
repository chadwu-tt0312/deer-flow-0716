# DeerFlow Logging System

DeerFlow 日誌系統是一個功能強大的日誌記錄解決方案，支援檔案和資料庫存儲，具有按使用者隔離、自動壓縮等特性。

## 📋 特性

- ✅ **多種存儲方式**：支援檔案、SQLite、PostgreSQL
- ✅ **使用者隔離**：每個 thread_id 獨立的日誌文件
- ✅ **自動維護**：檔案輪轉、壓縮、清理
- ✅ **節點標記**：區分不同模組和功能
- ✅ **執行緒安全**：支援多執行緒環境
- ✅ **上下文管理**：自動追蹤使用者上下文

## 🛠️ 配置

### 基本配置

在 `conf.yaml` 中添加以下配置：

```yaml
LOGGING:
  # 提供者選項：file, sqlite://path/to/db.sqlite, postgresql://user:pass@host:port/dbname
  provider: "file"
  level: "INFO"
  
  file_settings:
    log_dir: "logs"
    max_days: 10
    compress_old_files: true
    
  async_settings:
    batch_size: 100
    flush_interval: 5  # 秒
```

### 檔案模式配置

```yaml
LOGGING:
  provider: "file"
  level: "INFO"
  file_settings:
    log_dir: "logs"          # 日誌目錄
    max_days: 10             # 保留天數
    compress_old_files: true # 壓縮舊文件
```

### SQLite 配置

```yaml
LOGGING:
  provider: "sqlite:///logs/deerflow.db"
  level: "INFO"
```

### PostgreSQL 配置

```yaml
LOGGING:
  provider: "postgresql://username:password@localhost:5432/deerflow_logs"
  level: "INFO"
```

## 🚀 使用方法

### 基本使用

```python
from src.logging import init_logging, get_logger, set_thread_context, LogNode

# 初始化日誌系統
init_logging()

# 取得 logger
logger = get_logger(__name__)

# 設定執行緒上下文
set_thread_context("user_thread_123")

# 記錄日誌
logger.info("處理用戶請求", extra={"node": LogNode.FRONTEND})
logger.error("發生錯誤", extra={"node": LogNode.SYSTEM})
```

### 在 langGraph 節點中使用

```python
from src.logging import get_logger, set_thread_context, LogNode

def planner_node(state: State, config: RunnableConfig):
    # 設定執行緒上下文
    thread_id = config.get("thread_id", "default")
    set_thread_context(thread_id)
    
    # 取得 logger
    logger = get_logger(__name__)
    
    # 記錄日誌
    logger.info("開始生成計劃", extra={"node": LogNode.PLANNER})
    
    # ... 處理邏輯 ...
    
    logger.info("計劃生成完成", extra={"node": LogNode.PLANNER})
```

### 在 API 端點中使用

```python
from src.logging import get_logger, set_thread_context, LogNode

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    # 設定執行緒上下文
    thread_id = request.thread_id
    set_thread_context(thread_id)
    
    # 取得 logger
    logger = get_logger(__name__)
    
    # 記錄 API 呼叫
    logger.info(f"聊天流開始", extra={"node": LogNode.CHAT_STREAM})
    
    # ... 處理邏輯 ...
```

## 📊 日誌格式

### 檔案格式

```
2025-01-17 14:30:25.123 [INFO] [thread:user_123] [node:planner] [src.graph.nodes] 計劃生成完成
2025-01-17 14:30:26.456 [ERROR] [thread:user_456] [node:frontend] [src.server.app] 請求處理失敗
```

### 資料庫格式

| 欄位 | 類型 | 描述 |
|------|------|------|
| id | INTEGER | 主鍵 |
| timestamp | DATETIME | 時間戳 |
| level | VARCHAR(20) | 日誌等級 |
| thread_id | VARCHAR(50) | 執行緒 ID |
| node | VARCHAR(50) | 節點名稱 |
| message | TEXT | 日誌訊息 |
| extra_data | TEXT | 額外資料 (JSON) |

## 🏷️ 節點標記

系統提供了預定義的節點標記：

```python
from src.logging import LogNode

# langGraph 節點
LogNode.PLANNER           # 計劃節點
LogNode.RESEARCHER        # 研究節點
LogNode.CODER            # 編碼節點
LogNode.REPORTER         # 報告節點
LogNode.COORDINATOR      # 協調節點

# 系統節點
LogNode.FRONTEND         # 前端
LogNode.SYSTEM           # 系統

# API 節點
LogNode.CHAT_STREAM      # 聊天流
LogNode.PODCAST          # 播客
LogNode.PPT              # 簡報

# 工具節點
LogNode.SEARCH           # 搜索
LogNode.CRAWL            # 爬蟲
LogNode.TTS              # 語音合成
```

## 📁 檔案組織

### 檔案命名規則

- 通用日誌：`logs/20250117.log`
- 用戶日誌：`logs/20250117-user_123.log`
- 壓縮檔案：`logs/20250117-user_123.log.gz`

### 目錄結構

```
logs/
├── 20250117.log           # 今天的通用日誌
├── 20250117-user_123.log  # 用戶 123 的日誌
├── 20250117-user_456.log  # 用戶 456 的日誌
├── 20250116.log.gz        # 昨天的壓縮日誌
└── 20250115-user_123.log.gz
```

## 🔧 維護和管理

### 自動維護

系統會自動執行以下維護任務：

- **每天凌晨 2 點**：執行檔案輪轉和壓縮
- **過期清理**：刪除超過設定天數的檔案
- **資料庫清理**：刪除過期的資料庫記錄

### 手動維護

```python
from src.logging.logger import get_logger_instance

# 取得日誌實例
logger_instance = get_logger_instance()

# 執行維護任務
logger_instance.run_maintenance()

# 取得統計資訊
stats = logger_instance.get_stats()
print(stats)
```

## 🧪 測試

執行測試腳本：

```bash
python test_logging.py
```

測試會驗證：
- 基本日誌記錄功能
- 執行緒上下文管理
- 節點標記功能
- 錯誤處理
- 性能測試

## 🛡️ 安全性

- **執行緒隔離**：每個 thread_id 的日誌完全分離
- **資料保護**：敏感資料不會意外記錄到錯誤的日誌文件
- **權限控制**：日誌文件具有適當的權限設定

## 📈 效能

- **記憶體效率**：合理的緩衝區大小
- **壓縮存儲**：節省磁碟空間

## 🐛 故障排除

### 常見問題

1. **日誌文件未生成**
   - 檢查 `logs/` 目錄權限
   - 確認 `init_logging()` 已被調用

2. **資料庫連接失敗**
   - 檢查資料庫 URL 格式
   - 確認資料庫服務正在運行

### 調試模式

```python
# 啟用調試模式
init_logging()
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)
```

## 📝 最佳實踐

1. **在每個模組開始時設定執行緒上下文**
2. **使用適當的節點標記**
3. **避免記錄敏感資訊**
4. **定期檢查日誌文件大小**
5. **合理設定保留期限**

## 🔗 相關文檔

- [DeerFlow 主要文檔](../../README_log.md)
- [配置指南](../../docs/configuration_guide.md)
- [API 文檔](../../docs/api.md)
