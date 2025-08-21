# 統一 API 架構

## 概述

DeerFlow 現在採用統一的 API 架構，讓 AutoGen 與 LangGraph 系統使用相同的 API 路徑，實現無縫的系統切換。

## 架構設計

### 核心原則

1. **單一 API 端點**: 兩個系統共享相同的 API 路徑
2. **動態系統選擇**: 根據環境變數自動選擇使用的系統
3. **無前端修改**: 前端代碼無需任何變更
4. **資源效率**: 兩個系統不會同時運行

### 系統架構圖

```
┌─────────────────┐    ┌──────────────────┐
│   前端應用      │    │   環境變數       │
│                 │    │                  │
│  /api/chat/*    │    │USE_AUTOGEN_SYSTEM│
└─────────┬───────┘    └─────────┬────────┘
          │                      │
          │                      ▼
          │              ┌─────────────────┐
          │              │   系統切換器    │
          │              │                 │
          │              │ SystemSwitcher  │
          │              └─────────┬───────┘
          │                        │
          ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   統一 API      │    │   系統選擇      │
│   路由層        │    │                 │
│                 │    │ AutoGen 或      │
│ app.py          │    │ LangGraph       │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          │                      ▼
          │              ┌─────────────────┐
          │              │   系統執行      │
          │              │                 │
          │              │ 根據選擇執行    │
          │              │ 對應的系統      │
          └──────────────┼─────────────────┼─────────────┐
                         │                 │             │
                         ▼                ▼            │
              ┌─────────────────┐ ┌─────────────────┐    │
              │   AutoGen       │ │   LangGraph     │    │
              │   系統          │ │   系統          │    │
              │                 │ │                 │    │
              │ - 智能體管理    │ │ - 圖工作流      │    │
              │ - 對話協調      │ │ - 節點執行      │    │
              │ - 工具整合      │ │ - 狀態管理      │    │
              └─────────────────┘ └─────────────────┘    │
                                                         │
                         ┌───────────────────────────────┘
                         │
                         ▼
              ┌─────────────────┐
              │   統一響應      │
              │   格式          │
              │                 │
              │ SSE 事件流      │
              │ JSON 響應       │
              └─────────────────┘
```

## 實現細節

### 1. 系統切換器

`SystemSwitcher` 類負責管理系統選擇：

```python
class SystemSwitcher:
    def __init__(self, default_system: SystemType = SystemType.AUTOGEN):
        self.default_system = default_system
        self.current_system = self._detect_system()
    
    def _detect_system(self) -> SystemType:
        env_system = os.getenv("USE_AUTOGEN_SYSTEM", "true").lower()
        if env_system in ["true", "1", "yes", "on"]:
            return SystemType.AUTOGEN
        elif env_system in ["false", "0", "no", "off"]:
            return SystemType.LANGGRAPH
        else:
            return self.default_system
```

### 2. 統一 API 路由

在 `src/server/app.py` 中實現統一的聊天端點：

```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """統一的聊天流式端點"""
    current_system = get_current_system_type()
    
    if current_system == "autogen":
        autogen_system = get_autogen_system()
        if autogen_system:
            return await autogen_system(request)
        else:
            # 回退到 LangGraph
            current_system = "langgraph"
    
    if current_system == "langgraph":
        return StreamingResponse(
            _astream_workflow_generator(...),
            media_type="text/event-stream",
        )
```

### 3. 延遲導入機制

為了解決循環導入問題，使用延遲導入：

```python
def get_current_system_type():
    """獲取當前系統類型，避免循環導入"""
    try:
        switcher = get_system_switcher()
        if switcher:
            system_enum = switcher.get_current_system()
            return system_enum.value if hasattr(system_enum, "value") else str(system_enum)
        else:
            # 直接檢查環境變數
            env_system = os.getenv("USE_AUTOGEN_SYSTEM", "true").lower()
            if env_system in ["true", "1", "yes", "on"]:
                return "autogen"
            else:
                return "langgraph"
    except Exception as e:
        logger.warning(f"無法獲取系統類型: {e}")
        return "langgraph"
```

## 系統切換流程

### 1. 啟動時檢測

1. 讀取環境變數 `USE_AUTOGEN_SYSTEM`
2. 初始化對應的系統組件
3. 設置當前活動系統

### 2. 請求處理

1. 接收 API 請求
2. 調用 `get_current_system_type()` 獲取當前系統
3. 根據系統類型路由到對應的處理邏輯
4. 返回統一的響應格式

### 3. 錯誤處理

1. 如果 AutoGen 系統不可用，自動回退到 LangGraph
2. 記錄系統切換和錯誤信息
3. 提供統一的錯誤響應格式

## API 端點

### 統一端點

- **聊天流**: `POST /api/chat/stream` - 根據系統設定自動路由
- **系統狀態**: `GET /api/system/status` - 返回當前系統狀態
- **工作流調用**: `POST /api/system/workflow` - 系統特定的工作流執行
- **相容性測試**: `GET /api/system/compatibility` - 測試系統相容性

### 系統特定端點

- **TTS**: `POST /api/tts` - 文字轉語音
- **Podcast**: `POST /api/podcast/generate` - 播客生成
- **PPT**: `POST /api/ppt/generate` - PPT 生成
- **Prose**: `POST /api/prose/generate` - 文章生成
- **Prompt**: `POST /api/prompt/enhance` - 提示詞增強

## 配置管理

### 環境變數

```bash
# 系統選擇
USE_AUTOGEN_SYSTEM=true  # 或 false

# API 配置
NEXT_PUBLIC_API_URL=http://localhost:8001/api/
```

### 配置文件

- `conf_autogen.yaml` - AutoGen 系統配置
- `conf.yaml` - LangGraph 系統配置

## 優勢

1. **無縫切換**: 兩個系統使用相同的 API 接口
2. **資源效率**: 避免同時運行兩個系統
3. **維護簡化**: 統一的 API 管理
4. **向後相容**: 前端無需任何修改
5. **靈活配置**: 通過環境變數輕鬆切換

## 使用場景

### 開發階段

- 使用 LangGraph 進行快速原型開發
- 使用 AutoGen 進行複雜對話測試

### 生產環境

- 根據性能需求選擇合適的系統
- 根據功能需求選擇對應的系統

### 測試驗證

- 在兩個系統間切換進行功能驗證
- 比較兩個系統的性能表現

## 故障排除

### 常見問題

1. **循環導入錯誤**: 使用延遲導入機制解決
2. **系統不可用**: 自動回退到備用系統
3. **配置錯誤**: 檢查環境變數和配置文件

### 調試方法

1. 檢查服務器日誌
2. 使用 `/api/system/status` 端點檢查系統狀態
3. 驗證環境變數設定

## 未來改進

1. **熱切換**: 支持運行時動態切換系統
2. **性能監控**: 添加系統性能指標
3. **自動回退**: 智能故障檢測和自動回退
4. **配置驗證**: 啟動時驗證系統配置
