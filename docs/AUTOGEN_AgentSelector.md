# AutoGen 智能體選擇器

這個模組提供了重構後的智能體選擇器系統，用於 AutoGen SelectorGroupChat 中決定下一個發言的智能體。

## 主要特性

### 🔧 模組化設計
- 將原始的 `selector_func` 重構為類別導向的設計
- 提供清晰的介面和可擴展的架構
- 支援多種選擇策略

### 📊 智能體管理
- 基於工作流程階段的智能選擇
- 支援負載平衡和使用統計
- 提供詳細的除錯資訊

### 🎯 易於使用
- 保持與原始 `selector_func` 相同的介面
- 提供工廠函數快速創建選擇器
- 支援多種配置選項

## 快速開始

### 基本使用

```python
from src.autogen_system.workflow import AgentSelector

# 創建基本選擇器
selector = AgentSelector(enable_debug=True)

# 在 SelectorGroupChat 中使用
def selector_func(messages):
    return selector.select_next_agent(messages)
```

### 使用工廠函數

```python
from src.autogen_system.workflow import create_selector_function

# 創建基本選擇器函數
selector_func = create_selector_function("basic", max_turns=50)

# 創建進階選擇器函數
advanced_selector = create_selector_function("advanced", max_turns=100)
```

### 在 SelectorGroupChat 中使用

```python
from autogen_agentchat.teams import SelectorGroupChat
from src.autogen_system.workflow import create_selector_function

# 創建選擇器
selector_func = create_selector_function("basic", enable_debug=True)

# 創建 SelectorGroupChat
team = SelectorGroupChat(
    participants=agent_list,
    model_client=model_client,
    termination_condition=termination,
    selector_func=selector_func,
    max_turns=50,
)
```

## 選擇器類型

### AgentSelector (基本版本)
- 基於工作流程階段的選擇邏輯
- 支援訊息解析和上下文分析
- 提供詳細的日誌記錄

### AdvancedAgentSelector (進階版本)
- 繼承基本選擇器的所有功能
- 新增負載平衡機制
- 提供使用統計和分析功能

## 工作流程階段

選擇器根據以下階段進行決策：

1. **初始化階段 (INITIALIZATION)**: 使用者輸入 → 協調者
2. **協調階段 (COORDINATION)**: 協調者分析 → 規劃者
3. **規劃階段 (PLANNING)**: 規劃者制定計劃 → 執行者
4. **執行階段 (EXECUTION)**: 研究者/程式設計師執行任務
5. **報告階段 (REPORTING)**: 報告者生成最終報告
6. **完成階段 (COMPLETED)**: 工作流程結束

## 智能體角色

- **CoordinatorAgentV3**: 協調者，負責任務分析
- **PlannerAgentV3**: 規劃者，制定執行計劃
- **ResearcherAgentV3**: 研究者，執行搜尋和研究任務
- **CoderAgentV3**: 程式設計師，執行程式碼和數據處理
- **ReporterAgentV3**: 報告者，生成最終報告

## 配置選項

### AgentSelector 參數
- `max_turns`: 最大輪次數（預設：50）
- `enable_debug`: 啟用除錯模式（預設：True）
- `max_plan_iterations`: 最大計劃迭代次數（預設：1）
- `max_step_num`: 計劃中的最大步驟數（預設：3）
- `max_search_results`: 最大搜尋結果數（預設：3）
- `auto_accepted_plan`: 是否自動接受計劃（預設：True）
- `enable_background_investigation`: 是否啟用背景調查（預設：True）

### 工廠函數參數
- `selector_type`: 選擇器類型（"basic" 或 "advanced"）
- `max_turns`: 最大輪次數
- `enable_debug`: 啟用除錯模式
- `max_plan_iterations`: 最大計劃迭代次數
- `max_step_num`: 計劃中的最大步驟數
- `max_search_results`: 最大搜尋結果數
- `auto_accepted_plan`: 是否自動接受計劃
- `enable_background_investigation`: 是否啟用背景調查

## 範例程式碼

查看 `examples/selector_usage_example.py` 了解詳細的使用範例。

## 遷移指南

### 從原始 selector_func 遷移

原始程式碼：
```python
def selector_func(messages):
    # 大量的條件判斷邏輯
    if not messages:
        return "CoordinatorAgentV3"
    # ... 更多邏輯
```

重構後：
```python
from src.autogen_system.workflow import create_selector_function

# 方法1：使用工廠函數
selector_func = create_selector_function("basic")

# 方法2：直接使用類別
from src.autogen_system.workflow import AgentSelector

selector = AgentSelector()
def selector_func(messages):
    return selector.select_next_agent(messages)
```

### 優勢

1. **更清晰的程式碼結構**: 邏輯分離到不同的方法中
2. **更好的可維護性**: 易於修改和擴展選擇邏輯
3. **更強的可測試性**: 每個方法都可以獨立測試
4. **更豐富的功能**: 支援統計、負載平衡等進階功能
5. **向後兼容**: 保持原始介面不變

## 除錯和監控

選擇器提供詳細的日誌記錄：

```python
# 啟用除錯模式
selector = AgentSelector(enable_debug=True)

# 檢視使用統計（僅進階版本）
advanced_selector = AdvancedAgentSelector()
stats = advanced_selector.get_usage_statistics()
print(f"使用統計: {stats}")
```

## 自訂擴展

您可以繼承 `AgentSelector` 來創建自訂的選擇邏輯：

```python
class CustomAgentSelector(AgentSelector):
    def _select_based_on_context(self, context):
        # 實現您的自訂邏輯
        if self.custom_condition(context):
            return "CustomAgentV3"
        return super()._select_based_on_context(context)
    
    def custom_condition(self, context):
        # 您的自訂條件
        return False
```

## 注意事項

1. 確保所有智能體名稱與 `AgentName` 枚舉一致
2. 訊息格式需要符合 `message_framework` 的規範
3. 終止條件應該包含 "WORKFLOW_COMPLETE" 或 "TERMINATE"
4. 建議啟用除錯模式以便追蹤選擇邏輯
