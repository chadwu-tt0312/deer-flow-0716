# CoordinatorAgent + LedgerOrchestrator 遷移計劃

## 概述

本文檔詳細描述如何將現有的 `CoordinatorAgent` 和 `LedgerOrchestrator` 修改為符合 AutoGen 框架的實現，並參考 `coordinator_node()` 的功能模式。

## 目標

讓使用 AutoGen 框架的 `CoordinatorAgent` + `LedgerOrchestrator` 具備與 LangGraph `coordinator_node()` 類似的訊息處理和流程控制能力。

## 分析結果

### coordinator_node() 核心功能
1. **線程上下文管理** - 從 RunnableConfig 獲取 thread_id，設置線程特定日誌
2. **配置和提示處理** - 提取 Configuration，應用動態提示模板
3. **工具綁定和 LLM 調用** - 綁定 handoff_to_planner 工具，處理工具調用
4. **智能決策邏輯** - 基於工具調用結果決定下一步行動
5. **狀態更新和流程控制** - 返回 Command 對象更新狀態
6. **背景調查決策** - 根據配置決定是否啟動背景調查

### AutoGen 框架模式
1. **LLM 調用** - 使用 `ChatCompletionClient.create()`
2. **工具處理** - 檢查 `FunctionCall` 類型的回應
3. **消息格式** - SystemMessage, UserMessage, AssistantMessage
4. **基礎結構** - 繼承 `BaseWorker`，實現 `_generate_reply()`

### 現有系統差距
| 功能領域 | coordinator_node() | 現有 AutoGen 系統 | 需要修改 |
|----------|-------------------|------------------|----------|
| 線程管理 | ✅ 完整 | ❌ 缺失 | 需要添加 |
| 配置處理 | ✅ RunnableConfig | ❌ 自定義配置 | 需要適配 |
| 提示模板 | ✅ 動態模板 | ⚠️ 靜態消息 | 需要改進 |
| 工具處理 | ✅ LLM 工具綁定 | ❌ 手動模擬 | 需要實現 |
| 決策邏輯 | ✅ 智能決策 | ⚠️ 規則簡化 | 需要升級 |
| 狀態管理 | ✅ Command 對象 | ⚠️ 字典返回 | 需要標準化 |
| 流程控制 | ✅ 明確指向 | ⚠️ 字符串決策 | 需要改進 |

## 修改計劃

### 階段一：CoordinatorAgent 核心重構

#### 任務 1: 重構 CoordinatorAgent 基礎架構
**目標**: 使 CoordinatorAgent 符合 AutoGen BaseWorker 模式

**具體修改**:
```python
# 修改繼承結構
class CoordinatorAgent(BaseWorker):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        description: str = DEFAULT_DESCRIPTION,
        system_messages: List[SystemMessage] = DEFAULT_SYSTEM_MESSAGES,
    ):
        super().__init__(description)
        self._model_client = model_client
        self._system_messages = system_messages
        self._chat_history: List[LLMMessage] = []

    async def _generate_reply(self, cancellation_token: CancellationToken) -> Tuple[bool, UserContent]:
        # 實現核心邏輯
        pass
```

**檔案位置**: `src/autogen_system/agents/coordinator_agent.py`

#### 任務 2: 實現 AutoGen 風格的 LLM 調用
**目標**: 替換手動 LLM 調用為 AutoGen 標準模式

**具體修改**:
```python
async def _call_llm_with_tools(self, user_input: str) -> Any:
    # 準備消息
    messages = self._system_messages + self._chat_history + [
        UserMessage(content=user_input, source="user")
    ]
    
    # 調用 LLM
    response = await self._model_client.create(
        messages=messages,
        tools=[HANDOFF_TO_PLANNER_TOOL],
        extra_create_args={"tool_choice": "auto"},
        cancellation_token=cancellation_token
    )
    
    return response
```

#### 任務 3: 實現真正的工具綁定
**目標**: 實現 handoff_to_planner 工具的正確綁定和處理

**具體修改**:
```python
# 定義工具
HANDOFF_TO_PLANNER_TOOL = {
    "type": "function",
    "function": {
        "name": "handoff_to_planner",
        "description": "Handoff to planner agent to do plan.",
        "parameters": {
            "type": "object",
            "properties": {
                "research_topic": {
                    "type": "string",
                    "description": "The topic of the research task to be handed off."
                },
                "locale": {
                    "type": "string", 
                    "description": "The user's detected language locale (e.g., en-US, zh-CN)."
                }
            },
            "required": ["research_topic", "locale"]
        }
    }
}

# 處理工具調用
def _process_tool_calls(self, response) -> Dict[str, Any]:
    if isinstance(response.content, list):
        for function_call in response.content:
            if isinstance(function_call, FunctionCall):
                if function_call.name == "handoff_to_planner":
                    args = json.loads(function_call.arguments)
                    return {
                        "action": "handoff_to_planner",
                        "research_topic": args.get("research_topic"),
                        "locale": args.get("locale"),
                        "goto": "planner"
                    }
    return {"action": "direct_response", "goto": None}
```

### 階段二：整合線程管理和動態提示

#### 任務 4: 整合線程管理和日誌系統
**目標**: 添加線程 ID 獲取和線程特定日誌

**具體修改**:
```python
def _get_thread_id_from_context(self, cancellation_token: CancellationToken) -> str:
    """從 cancellation_token 或其他上下文獲取線程 ID"""
    # 實現線程 ID 提取邏輯
    return "default_thread"

def _setup_thread_logging(self, thread_id: str):
    """設置線程特定的日誌"""
    from src.logging import setup_thread_logging, set_thread_context
    thread_logger = setup_thread_logging(thread_id)
    set_thread_context(thread_id)
    return thread_logger
```

#### 任務 5: 實現動態提示模板支持
**目標**: 整合 apply_prompt_template() 功能

**具體修改**:
```python
def _apply_dynamic_template(self, state: Dict[str, Any]) -> List[SystemMessage]:
    """應用動態提示模板"""
    from src.prompts.template import apply_prompt_template
    
    # 應用 coordinator.md 模板
    messages = apply_prompt_template("coordinator", state)
    
    # 轉換為 AutoGen 格式
    system_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            system_messages.append(SystemMessage(content=msg["content"]))
    
    return system_messages
```

### 階段三：LedgerOrchestrator 升級

#### 任務 6: 升級 LedgerOrchestrator 支持 AutoGen 消息格式
**目標**: 適配 AutoGen 消息類型和 BaseWorker 交互

**具體修改**:
```python
def _convert_to_autogen_messages(self, conversation_history: List[Dict]) -> List[LLMMessage]:
    """轉換對話歷史為 AutoGen 消息格式"""
    messages = []
    for msg in conversation_history:
        content = msg["content"]
        sender = msg["sender"]
        
        if sender == "user":
            messages.append(UserMessage(content=content, source="user"))
        elif sender in self.agents:
            messages.append(AssistantMessage(content=content, source=sender))
        else:
            messages.append(SystemMessage(content=content))
    
    return messages

async def _call_agent_with_autogen(self, agent: BaseWorker, instruction: str) -> str:
    """使用 AutoGen 方式調用代理"""
    # 添加指令到聊天歷史
    user_message = UserMessage(content=instruction, source="orchestrator")
    
    # 調用代理的 _generate_reply 方法
    request_halt, response = await agent._generate_reply(cancellation_token=None)
    
    return response
```

#### 任務 7: 實現類似 LangGraph Command 的流程控制
**目標**: 標準化狀態更新和流程控制

**具體修改**:
```python
@dataclass
class WorkflowCommand:
    """類似 LangGraph Command 的流程控制對象"""
    update: Dict[str, Any] = field(default_factory=dict)
    goto: Optional[str] = None
    terminate: bool = False

class LedgerOrchestrator:
    async def select_next_agent(self) -> Optional[WorkflowCommand]:
        """選擇下一個智能體並返回流程控制命令"""
        ledger_entry = await self.update_ledger()
        
        if ledger_entry.is_request_satisfied:
            return WorkflowCommand(terminate=True)
        
        # 檢查背景調查決策
        if self._should_enable_background_investigation():
            return WorkflowCommand(
                update={
                    "locale": ledger_entry.locale,
                    "research_topic": ledger_entry.research_topic,
                },
                goto="background_investigator"
            )
        
        return WorkflowCommand(
            update={
                "locale": ledger_entry.locale,
                "research_topic": ledger_entry.research_topic,
                "instruction": ledger_entry.instruction_or_question,
            },
            goto=ledger_entry.next_speaker
        )
```

#### 任務 8: 添加背景調查決策邏輯
**目標**: 實現條件性工作流分支

**具體修改**:
```python
def _should_enable_background_investigation(self) -> bool:
    """檢查是否應啟用背景調查"""
    # 從配置或狀態檢查
    return self.config.get("enable_background_investigation", False)

def _determine_next_step(self, tool_call_result: Dict[str, Any]) -> str:
    """基於工具調用結果決定下一步"""
    if tool_call_result.get("action") == "handoff_to_planner":
        if self._should_enable_background_investigation():
            return "background_investigator"
        else:
            return "planner"
    return "__end__"
```

### 階段四：整合測試和優化

#### 任務 9: 整合測試和功能驗證
**目標**: 確保修改後的系統正常工作

**測試項目**:
1. CoordinatorAgent 的工具調用功能
2. LedgerOrchestrator 的代理選擇邏輯
3. 線程管理和日誌系統
4. 動態提示模板應用
5. 背景調查決策流程
6. 與現有系統的兼容性

## 技術適配細節

### 1. 消息格式轉換
```python
# 從現有格式轉換
def convert_message_format(old_message: Dict) -> LLMMessage:
    role = old_message["role"]
    content = old_message["content"]
    
    if role == "system":
        return SystemMessage(content=content)
    elif role == "user":
        return UserMessage(content=content, source="user")
    elif role == "assistant":
        return AssistantMessage(content=content, source="assistant")
```

### 2. LLM 客戶端適配
```python
# 適配現有 LLM 到 ChatCompletionClient
def create_chat_completion_client(llm_type: str) -> ChatCompletionClient:
    """將現有 LLM 包裝為 ChatCompletionClient"""
    from src.llms.llm import get_llm_by_type
    base_llm = get_llm_by_type(llm_type)
    
    # 創建適配器
    return ChatCompletionClientAdapter(base_llm)
```

### 3. 配置系統整合
```python
# 整合現有配置系統
def extract_configuration_from_context(context: Any) -> Configuration:
    """從上下文提取配置信息"""
    # 實現配置提取邏輯
    return Configuration.from_runnable_config(context)
```

## 實施順序

1. **階段一 → 任務 1-3**: CoordinatorAgent 核心重構（優先）
2. **階段二 → 任務 4-5**: 線程和提示模板整合
3. **階段三 → 任務 6-8**: LedgerOrchestrator 升級
4. **階段四 → 任務 9**: 整合測試和驗證

## 預期效果

完成後，AutoGen 系統將具備：
- 與 coordinator_node() 相同的智能決策能力
- 正確的工具綁定和調用處理
- 完整的線程管理和日誌支持
- 動態提示模板應用
- 標準化的流程控制機制
- 背景調查決策邏輯

## 風險和注意事項

1. **兼容性**: 確保不破壞現有功能
2. **性能**: AutoGen 調用可能有不同的性能特徵
3. **錯誤處理**: 需要完善的異常處理機制
4. **測試覆蓋**: 每個階段都需要充分測試

## 後續維護

- 定期檢查 AutoGen 框架更新
- 監控性能和穩定性
- 根據使用情況調整配置
- 持續優化決策邏輯
