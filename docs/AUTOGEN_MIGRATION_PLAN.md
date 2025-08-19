# DeerFlow AutoGen 架構遷移計劃

## 文件資訊

- **版本**: 1.0
- **建立日期**: 2025-08-14

## 摘要

本文件描述將 DeerFlow 系統從 LangGraph 框架遷移至 Microsoft AutoGen 框架的完整計劃。遷移採用漸進式策略，確保系統穩定性和API相容性。

## 變更動機

### 當前問題

1. **維護成本**: LangGraph 生態系統相對較新，社群支援有限
2. **學習曲線**: 複雜的圖狀工作流程增加開發難度
3. **企業支援**: AutoGen 有 Microsoft 官方長期支援保證
4. **開發效率**: AutoGen 的對話式架構更直觀易懂

### 預期效益

1. **更好的企業支援**: Microsoft 官方維護和長期承諾
2. **開發效率提升**: 更直觀的多智能體對話模式
3. **社群活躍度**: 更大的開發者社群和豐富的範例
4. **整合能力**: 與 Microsoft 生態系統更好的整合

## 技術架構變更

### 核心架構對比

#### 當前架構 (LangGraph)

```text
StateGraph → Nodes → Conditional Edges → State Management
```

- **狀態驅動**: 基於 MessagesState 的狀態管理
- **圖狀工作流**: 複雜的節點和邊定義
- **條件分支**: 豐富的條件邊支援
- **檢查點**: 內建的記憶體和持久化

#### 目標架構 (AutoGen)

```text
GroupChat → Agents → ConversationFlow → MessagePassing
```

- **對話驅動**: 基於消息傳遞的智能體互動
- **群組管理**: GroupChat 和 ConversableAgent
- **流程控制**: WorkflowController 補強複雜邏輯
- **狀態共享**: SharedMemory 和 ConversationHistory

### 智能體映射

| LangGraph 節點 | AutoGen 智能體 | 角色轉換 |
|---|---|---|
| coordinator_node | CoordinatorAgent | UserProxyAgent + 工作流控制 |
| planner_node | PlannerAgent | AssistantAgent + 計劃生成 |
| researcher_node | ResearcherAgent | AssistantAgent + 搜尋工具 |
| coder_node | CoderAgent | AssistantAgent + 程式碼執行 |
| reporter_node | ReporterAgent | AssistantAgent + 報告生成 |
| human_feedback_node | HumanProxyAgent | UserProxyAgent + 人機互動 |

## 實施計劃

### 階段1: 環境準備與設計 (3天)

#### 1.1 依賴管理更新 (0.5天)

**目標**: 更新專案依賴，引入 AutoGen

**變更內容**:

```toml
# pyproject.toml 新增
"pyautogen>=0.2.0",
"autogen-agentchat>=0.2.0",

# 暫時保留 (漸進式遷移)
"langgraph>=0.3.5",  # 將逐步移除
```

**交付成果**:
- 更新的 `pyproject.toml`
- 環境相容性驗證

#### 1.2 目錄結構建立 (0.5天)

**目標**: 建立 AutoGen 模組結構

**新目錄結構**:

```
src/
├── autogen_system/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── coordinator_agent.py
│   │   ├── planner_agent.py
│   │   ├── researcher_agent.py
│   │   ├── coder_agent.py
│   │   └── reporter_agent.py
│   ├── conversations/
│   │   ├── __init__.py
│   │   ├── research_workflow.py
│   │   ├── podcast_workflow.py
│   │   └── ppt_workflow.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── tool_adapter.py
│   │   ├── search_tools.py
│   │   └── code_tools.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── agent_config.py
│   │   └── workflow_config.py
│   └── controllers/
│       ├── __init__.py
│       └── workflow_controller.py
```

#### 1.3 配置系統設計 (1天)

**目標**: 設計 AutoGen 配置管理系統

**核心組件**:

```python
# src/autogen_system/config/agent_config.py
@dataclass
class AgentConfig:
    name: str
    role: str
    llm_config: Dict[str, Any]
    tools: List[str]
    max_consecutive_auto_reply: int = 10

# src/autogen_system/config/workflow_config.py
@dataclass
class WorkflowConfig:
    agents: List[AgentConfig]
    conversation_pattern: str
    max_rounds: int = 50
    human_input_mode: str = "NEVER"
```

#### 1.4 WorkflowController基礎架構 (1天)

**目標**: 實現工作流控制器來處理複雜邏輯

**核心功能**:

```python
class WorkflowController:
    def __init__(self, agents: Dict[str, ConversableAgent]):
        self.agents = agents
        self.conversation_history = []
        self.shared_memory = {}
    
    async def route_message(self, sender: str, message: str) -> str:
        """實現複雜的路由邏輯"""
        pass
    
    def check_completion_condition(self) -> bool:
        """檢查工作流完成條件"""
        pass
```

### 階段2: 核心智能體實現 (5天)

#### 2.1 基礎智能體類別 (1天)

**目標**: 實現智能體基礎類別和工廠模式

```python
class BaseResearchAgent(ConversableAgent):
    def __init__(self, name: str, role: str, tools: List, llm_config: Dict):
        super().__init__(
            name=name,
            llm_config=llm_config,
            code_execution_config=False,
            human_input_mode="NEVER"
        )
        self.role = role
        self.tools = tools
        self.register_function_mappings()
```

#### 2.2-2.5 各智能體實現 (4天)

每個智能體將根據原有的 LangGraph 節點邏輯重新實現：

- **CoordinatorAgent**: 負責接收用戶輸入，判斷是否需要啟動研究流程
- **PlannerAgent**: 生成研究計劃，處理計劃迭代
- **ResearcherAgent**: 執行網路搜尋和資訊收集
- **CoderAgent**: 處理程式碼相關任務
- **ReporterAgent**: 生成最終報告

### 階段3: 工具集成與適配 (4天)

#### 3.1 工具適配器 (1天)

**目標**: 建立 LangChain 工具到 AutoGen 的轉換器

```python
class ToolAdapter:
    @staticmethod
    def langchain_to_autogen(langchain_tool) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": langchain_tool.name,
                "description": langchain_tool.description,
                "parameters": langchain_tool.args_schema.schema(),
                "implementation": langchain_tool._run
            }
        }
```

#### 3.2-3.4 具體工具遷移 (3天)

- **搜尋工具**: Tavily, Brave Search 等
- **程式碼執行**: Python REPL 整合
- **MCP連接器**: 重新實現 MCP 協議支援

### 階段4: 對話流程實現 (3天)

#### 4.1 主要研究工作流 (1.5天)

**目標**: 實現核心研究對話流程

```python
class ResearchWorkflow:
    async def run(self, query: str) -> Dict:
        # 初始化對話
        coordinator_response = await self.coordinator.initiate_chat(
            recipient=self.planner,
            message=f"Research request: {query}"
        )
        
        # 處理計劃生成和執行
        while not self.is_complete():
            await self.process_next_step()
        
        return self.generate_final_report()
```

#### 4.2 人機互動處理 (1天)

**目標**: 保持現有的計劃審查流程

```python
class HumanFeedbackHandler:
    async def review_plan(self, plan: str) -> str:
        if self.auto_accepted:
            return "[ACCEPTED]"
        
        # 實現互動邏輯
        feedback = await self.get_human_input(plan)
        return feedback
```

#### 4.3 API相容性層 (0.5天)

**目標**: 確保現有API保持相容

```python
# 保持原有的API介面
async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
):
    # 內部轉換為 AutoGen 呼叫
    workflow = ResearchWorkflow()
    return await workflow.run(user_input)
```

### 階段5: 特殊工作流遷移 (4天)

#### 5.1-5.3 各工作流遷移

- **Podcast**: 腳本生成 → TTS → 音訊混合
- **PPT**: 內容組織 → 簡報生成
- **Prose/PromptEnhancer**: 文字處理工作流

### 階段6: 測試與優化 (3天)

#### 6.1 測試實施 (1.5天)

- 單元測試覆蓋率 > 80%
- 集成測試驗證完整工作流
- API相容性測試

#### 6.2 效能優化 (1天)

- 對話效率優化
- 記憶體使用優化
- 錯誤處理強化

#### 6.3 文件與部署 (0.5天)

- 更新開發文件
- 部署指南更新
- 遷移指南編寫

## 風險評估與緩解

### 主要風險

#### 1. 複雜工作流控制

- **風險**: AutoGen 的線性對話模式難以處理複雜分支邏輯
- **緩解措施**:
    - 實現 WorkflowController 提供額外控制層
    - 使用狀態機模式處理複雜流程
    - 分階段驗證功能等價性

#### 2. 效能下降

- **風險**: 對話式架構可能影響執行效率
- **緩解措施**:
    - 效能基準測試
    - 並行處理優化
    - 快取機制實現

#### 3. 功能缺失

- **風險**: 某些 LangGraph 功能無法完全移植
- **緩解措施**:
    - 詳細功能對比分析
    - 替代方案設計
    - 漸進式遷移確保回退能力

### 回退計劃

- 保持 LangGraph 系統並行運行
- 功能切換開關實現
- 快速回退機制準備

## 成功指標

### 功能指標

- [ ] 所有現有API保持相容
- [ ] 核心研究工作流正常運行
- [ ] 特殊工作流功能完整
- [ ] 人機互動流程無變化

### 效能指標

- [ ] 回應時間不超過原系統120%
- [ ] 記憶體使用量控制在合理範圍
- [ ] 錯誤率不超過1%

### 品質指標

- [ ] 測試覆蓋率 > 80%
- [ ] 程式碼審查通過率 100%
- [ ] 文件完整性 100%

## 後續維護

### 依賴管理

- 定期更新 AutoGen 版本
- 監控 Microsoft 官方更新
- 維護工具適配器相容性

### 優化計劃

- 持續效能監控
- 使用者回饋收集
- 功能改進迭代

## 結論

- 本遷移計劃採用漸進式策略，確保系統穩定性的同時實現架構現代化。透過詳細的階段規劃和風險控制，預期能在22個工作天內完成完整遷移，並為未來的功能擴展奠定更好的基礎。
- 一個工作天 ~= Cursor 1~5 次問答
