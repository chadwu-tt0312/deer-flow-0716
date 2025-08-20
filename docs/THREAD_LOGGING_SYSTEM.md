# Thread-specific 日誌系統

## 概述

DeerFlow 0716 專案已經整合了完整的 Thread-specific 日誌系統，每個 Thread 都會有獨立的日誌檔案，確保不同對話的日誌不會混雜在一起。系統支援從 `conf.yaml` 配置檔案讀取設定值。

## 主要特性

### 1. Thread-specific 日誌檔案
- 每個 Thread 都有獨立的日誌檔案
- 檔案命名格式：`YYMMDD-{thread_id前8碼}.log`
- 例如：`250820-O1AgycMW.log`

### 2. 主日誌檔案
- 系統級日誌記錄在主日誌檔案中
- 檔案命名格式：`YYMMDD.log`
- 例如：`250820.log`

### 3. 智能日誌過濾
- Thread-specific 的日誌不會出現在主日誌中
- 系統級日誌（如 Thread 生命週期）會保留在主日誌中
- 外部套件的日誌會被適當過濾

### 4. 配置檔案支援
- 支援從 `conf.yaml` 讀取日誌配置
- 可配置日誌級別、控制台輸出、檔案設定等
- 檔案輸出由 `provider` 自動決定（file provider = 檔案輸出，database provider = 資料庫輸出）
- 支援配置覆蓋和預設值

## 配置檔案設定

### conf.yaml 配置範例

```yaml
LOGGING:
  # 提供者選項：file, sqlite://path/to/db.sqlite, postgresql://user:pass@host:port/dbname
  provider: "file"
  
  # 日誌級別設定（適用於主日誌和 Thread 日誌）
  level: "INFO"
  
  # 輸出設定（同時適用於主日誌和 Thread 日誌）
  console_output: true  # 是否輸出到控制台
  
  # 檔案設定（當 provider="file" 時自動啟用檔案輸出）
  file_settings:
    log_dir: "logs"
    max_days: 10
    compress_old_files: true
    
  # 外部套件日誌設定
  external_loggers:
    level: "ERROR"  # 外部套件的日誌級別
    
  # 日誌格式設定
  format:
    main: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    thread: "%(asctime)s - %(levelname)s - %(message)s"
```

### 配置選項說明

| 配置項 | 類型 | 預設值 | 說明 |
|--------|------|--------|------|
| `provider` | string | "file" | 日誌提供者（file/database），決定輸出方式 |
| `level` | string | "INFO" | 日誌級別（同時適用於主日誌和 Thread 日誌） |
| `console_output` | boolean | true | 是否輸出到控制台（同時適用於主日誌和 Thread 日誌） |
| `file_settings.log_dir` | string | "logs" | 日誌檔案目錄（當 provider="file" 時使用） |
| `file_settings.max_days` | integer | 10 | 日誌檔案保留天數 |
| `file_settings.compress_old_files` | boolean | true | 是否壓縮舊日誌檔案 |
| `external_loggers.level` | string | "ERROR" | 外部套件日誌級別 |
| `format.main` | string | 預設格式 | 主日誌格式 |
| `format.thread` | string | 預設格式 | Thread 日誌格式 |

## 使用方法

### 基本設置

```python
from src.logging import (
    setup_deerflow_logging,
    setup_thread_logging,
    set_current_thread_context,
    clear_current_thread_context
)

# 初始化 DeerFlow 日誌系統（自動從 conf.yaml 讀取配置）
main_logger = setup_deerflow_logging()

# 為特定 Thread 創建 logger（自動從 conf.yaml 讀取配置）
thread_logger = setup_thread_logging(thread_id="your_thread_id")
```

### 配置覆蓋

```python
# 使用傳入的參數覆蓋配置檔案設定
main_logger = setup_deerflow_logging(
    debug=True,           # 覆蓋 level 設定
    log_to_file=True,     # 覆蓋 file_output 設定
    log_dir="custom_logs" # 覆蓋 log_dir 設定
)

# Thread logger 配置覆蓋
thread_logger = setup_thread_logging(
    thread_id="thread_id",
    level="DEBUG",         # 覆蓋 thread_logging.level 設定
    console_output=False,  # 覆蓋 thread_logging.console_output 設定
    file_output=True       # 覆蓋 thread_logging.file_output 設定
)
```

### 在 Thread 中使用

```python
# 設置當前 Thread 的 context
set_current_thread_context(thread_id, thread_logger)

# 記錄日誌（會自動寫入對應的 Thread 日誌檔案）
thread_logger.info("開始處理任務")
thread_logger.debug("調試信息")
thread_logger.warning("警告信息")
thread_logger.error("錯誤信息")

# 清理 Thread context
clear_current_thread_context()
```

### 在 Graph Nodes 中使用

```python
def your_node(state: State, config: RunnableConfig):
    # 設定執行緒上下文
    thread_id = config.get("thread_id", "default")
    # 使用新的 Thread-specific 日誌系統（自動從 conf.yaml 讀取配置）
    thread_logger = setup_thread_logging(thread_id)
    set_thread_context(thread_id)

    # 記錄日誌
    thread_logger.info("Node 開始執行")
    
    # ... 執行邏輯 ...
    
    thread_logger.info("Node 執行完成")
```

## 檔案結構

```
logs/
├── 250820.log                    # 主日誌檔案（新格式）
├── 250820-O1AgycMW.log          # Thread O1AgycMW7z1RfoLMAhoeB 的日誌
├── 250820-config_t.log          # Thread config_test_ab1018a4 的日誌
└── 20250820-default.log         # 舊的預設日誌檔案（向後相容）
```

## 環境變數配置

除了 `conf.yaml` 配置檔案，系統也支援環境變數配置：

```bash
# 日誌級別
export LOG_LEVEL=INFO

# 日誌目錄
export LOG_DIR=logs

# 是否啟用 DEBUG 模式
export DEBUG=false

# 是否寫入檔案
export LOG_TO_FILE=true
```

**注意**：環境變數的優先級低於 `conf.yaml` 配置檔案。

## 向後相容性

### 舊的 API 仍然可用

```python
from src.logging import get_logger, set_thread_context

# 舊的用法仍然可以工作
logger = get_logger("your_module")
set_thread_context("thread_id")
logger.info("日誌訊息")
```

### 自動升級

- 當使用 `set_thread_context()` 時，系統會自動創建 Thread-specific logger
- 舊的日誌格式仍然支援
- 新的 Thread-specific 功能會自動啟用
- 配置檔案設定會自動生效

## 清理資源

```python
from src.logging import cleanup_thread_logging, cleanup_all_thread_logging

# 清理特定 Thread 的日誌資源
cleanup_thread_logging("thread_id")

# 清理所有 Thread 的日誌資源
cleanup_all_thread_logging()

# 重置整個日誌系統
from src.logging import reset_logging
reset_logging()
```

## 測試

### 基本功能測試

```bash
python test_config_logging.py
```

測試會驗證：
- 從 `conf.yaml` 讀取配置
- Thread-specific logger 的創建
- 日誌記錄到正確的檔案
- Context 管理
- 資源清理

### 配置覆蓋測試

測試會驗證：
- 傳入參數覆蓋配置檔案設定
- 不同配置組合的日誌行為
- 配置優先級順序

## 故障排除

### 常見問題

1. **配置檔案未生效**
   - 檢查 `conf.yaml` 檔案是否存在
   - 確認 `LOGGING` 區段配置正確
   - 檢查配置檔案語法是否正確

2. **日誌檔案未創建**
   - 檢查 `logs` 目錄是否存在
   - 確認 `file_output: true` 設定
   - 檢查檔案權限

3. **Thread-specific 日誌未啟用**
   - 確認 `thread_logging.enabled: true`
   - 檢查 `setup_thread_logging()` 被正確調用

4. **配置覆蓋不生效**
   - 確認傳入參數的優先級高於配置檔案
   - 檢查參數名稱是否正確

### 調試模式

```python
# 啟用 DEBUG 模式
main_logger = setup_deerflow_logging(debug=True)

# 啟用特定模組的 DEBUG 日誌
import logging
logging.getLogger("src.graph.nodes").setLevel(logging.DEBUG)
```

### 配置驗證

```python
from src.logging.logging_config import _load_logging_config_from_yaml

# 檢查配置是否正確讀取
config = _load_logging_config_from_yaml()
print(f"日誌配置: {config}")
```

## 更新日誌

### 2025-08-20
- 整合完整的 Thread-specific 日誌系統
- 實現智能日誌過濾
- 保持向後相容性
- 支援異步環境
- 自動 stderr 捕獲和重定向

### 2025-08-20 (配置系統更新)
- 支援從 `conf.yaml` 讀取日誌配置
- 新增 Thread-specific 日誌配置選項
- 支援外部套件日誌級別配置
- 支援日誌格式自定義
- 實現配置覆蓋功能
- 保持環境變數配置支援
