# LangGraph 到 AutoGen 遷移指南

## 版本資訊
- **建立日期**: 2025-08-14
- **版本**: 1.0
- **適用範圍**: DeerFlow 系統完整遷移

## 切換準備檢查清單

### ✅ 系統準備狀況
- [x] AutoGen 依賴已安裝 (`pyautogen>=0.4.0`, `autogen-agentchat>=0.4.0`)
- [x] 所有智能體已實現 (Coordinator, Planner, Researcher, Coder, Reporter)
- [x] 工作流控制器已就緒
- [x] API 相容性層已完成
- [x] 工具適配器已實現
- [x] 測試框架已建立

## 切換步驟

### 第一階段：環境設定 (5 分鐘)

#### 1. 確認依賴安裝
```bash
# 檢查 AutoGen 版本
python -c "import autogen; print(autogen.__version__)"
python -c "import autogen_agentchat; print(autogen_agentchat.__version__)"
```

#### 2. 準備配置檔案
```bash
# 複製配置範例
cp conf_autogen.yaml.example conf_autogen.yaml

# 根據需要調整配置
# 特別注意 LLM 設定和 API 金鑰
```

### 第二階段：API 切換 (2 分鐘)

#### 方式一：直接使用 AutoGen API (推薦)
```python
from src.autogen_system.compatibility.api_adapter import run_agent_workflow_async

# 替換原有的 LangGraph 調用
result = await run_agent_workflow_async(
    user_input="研究人工智慧的發展趨勢",
    debug=False,
    max_plan_iterations=1,
    max_step_num=3,
    enable_background_investigation=True,
    auto_accepted_plan=True,
    report_style=ReportStyle.ACADEMIC
)
```

#### 方式二：使用相容性層 (無縫切換)
```python
from src.autogen_system.compatibility.langgraph_compatibility import create_langgraph_compatible_graph

# 創建相容的圖對象
graph = create_langgraph_compatible_graph(model_client)

# 使用原有的 LangGraph API
result = await graph.ainvoke({
    "messages": [{"role": "user", "content": "研究主題"}]
})
```

### 第三階段：工作流切換

#### 1. 研究工作流
```python
# 舊的 LangGraph 方式
from src.graph.builder import create_research_graph
graph = create_research_graph()

# 新的 AutoGen 方式
from src.autogen_system.workflows.research_workflow import ResearchWorkflowManager
workflow_manager = ResearchWorkflowManager(model_client)
await workflow_manager.initialize()
```

#### 2. 特殊工作流 (Podcast, PPT, Prose, PromptEnhancer)
```python
# 統一的 AutoGen 工作流調用
from src.autogen_system.workflows.podcast_workflow import PodcastWorkflowManager
from src.autogen_system.workflows.ppt_workflow import PPTWorkflowManager
from src.autogen_system.workflows.prose_workflow import ProseWorkflowManager
from src.autogen_system.workflows.prompt_enhancer_workflow import PromptEnhancerWorkflowManager

# 使用方式保持一致
podcast_manager = PodcastWorkflowManager(model_client)
result = await podcast_manager.run_podcast_workflow(script_content)
```

### 第四階段：伺服器應用程式切換

#### 1. FastAPI 應用程式
在 `src/server/app.py` 中切換端點實現：

```python
# 修改主要端點
@app.post("/api/research")
async def research_endpoint(request: ResearchRequest):
    # 舊方式
    # result = await langgraph_research_workflow(request.query)
    
    # 新方式
    from src.autogen_system.compatibility.api_adapter import run_agent_workflow_async
    result = await run_agent_workflow_async(
        user_input=request.query,
        debug=request.debug,
        auto_accepted_plan=request.auto_accept_plan,
        report_style=request.report_style
    )
    return result
```

#### 2. 流式回應
```python
@app.post("/api/research/stream")
async def research_stream_endpoint(request: ResearchRequest):
    from src.autogen_system.compatibility.langgraph_compatibility import create_langgraph_compatible_graph
    
    graph = create_langgraph_compatible_graph(model_client)
    
    async def event_generator():
        async for event in graph.astream(
            {"messages": [{"role": "user", "content": request.query}]},
            config={"thread_id": request.thread_id}
        ):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/plain")
```

## 系統差異對照

### 1. 架構差異

| 特性 | LangGraph | AutoGen |
|------|-----------|---------|
| 控制模式 | 狀態圖驅動 | 對話驅動 |
| 智能體互動 | 節點間傳遞 | 群組對話 |
| 條件分支 | 條件邊 | WorkflowController |
| 狀態管理 | MessagesState | ConversationHistory + SharedMemory |
| 工具調用 | 直接綁定 | 工具適配器 |

### 2. API 對照表

| LangGraph API | AutoGen 等效方法 |
|---------------|------------------|
| `graph.ainvoke()` | `run_agent_workflow_async()` |
| `graph.astream()` | LangGraph 相容性層 |
| `MessagesState` | ConversationHistory |
| `Annotation` | SharedMemory |
| `tools.bind()` | ToolAdapter.adapt() |

### 3. 配置對照

```yaml
# LangGraph 配置
langgraph:
  checkpointer: "memory"
  threads: true
  
# AutoGen 配置  
autogen:
  group_chat:
    max_round: 50
  agent_defaults:
    max_consecutive_auto_reply: 10
```

## 效能考量

### 1. 記憶體使用
- **LangGraph**: 狀態持久化佔用較多記憶體
- **AutoGen**: 對話歷史管理更精簡

### 2. 執行速度
- **LangGraph**: 圖遍歷有額外開銷
- **AutoGen**: 直接對話較快速

### 3. 可擴展性
- **LangGraph**: 圖結構限制較多
- **AutoGen**: 智能體數量更彈性

## 回退機制

如需回退到 LangGraph，保留以下設定：

### 1. 保留 LangGraph 依賴
```toml
# pyproject.toml 中保留
"langgraph>=0.3.5"  # 暫時保留以備回退
```

### 2. 環境變數切換
```python
# 在 .env 中設定
USE_AUTOGEN_SYSTEM=true  # 設為 false 回退到 LangGraph
```

### 3. 程式碼切換開關
```python
import os

if os.getenv("USE_AUTOGEN_SYSTEM", "true").lower() == "true":
    from src.autogen_system.compatibility.api_adapter import run_agent_workflow_async as workflow_func
else:
    from src.workflow import run_agent_workflow_async as workflow_func
```

## 常見問題解決

### 1. 匯入錯誤
```bash
# 如果出現 AutoGen 匯入錯誤
pip install --upgrade pyautogen autogen-agentchat autogen-ext[openai]
```

### 2. 配置錯誤
```python
# 檢查配置檔案
from src.autogen_system.config.config_loader import load_autogen_config
config = load_autogen_config()
print(config)
```

### 3. 效能問題
```python
# 啟用偵錯模式檢查
result = await run_agent_workflow_async(
    user_input="測試查詢",
    debug=True  # 啟用詳細日誌
)
```

## 驗證測試

### 1. 基本功能測試
```python
# 測試基本研究功能
async def test_basic_research():
    result = await run_agent_workflow_async(
        user_input="什麼是機器學習？",
        auto_accepted_plan=True
    )
    assert result["success"] == True
    assert "final_report" in result
```

### 2. 工作流測試
```python
# 測試所有工作流
test_workflows = [
    ("research", "研究人工智慧"),
    ("podcast", "生成關於科技的播客"),
    ("ppt", "製作簡報：數位轉型"),
    ("prose", "撰寫技術文章"),
]

for workflow_type, query in test_workflows:
    result = await test_workflow(workflow_type, query)
    assert result["success"] == True
```

### 3. 效能基準測試
```python
import time

async def benchmark_performance():
    start_time = time.time()
    result = await run_agent_workflow_async("測試查詢")
    end_time = time.time()
    
    execution_time = end_time - start_time
    print(f"執行時間: {execution_time:.2f} 秒")
    
    # 與 LangGraph 基準比較
    assert execution_time < langgraph_baseline * 1.2  # 不超過 20% 額外時間
```

## 最佳實踐

### 1. 漸進式遷移
- 先在測試環境完整驗證
- 按工作流類型分批遷移
- 保持監控和日誌記錄

### 2. 配置管理
- 使用環境變數控制切換
- 準備回退配置
- 備份重要設定

### 3. 監控指標
- 回應時間
- 成功率
- 錯誤率
- 記憶體使用量

## 技術支援

如遇到問題，請檢查：
1. 日誌檔案：`logs/autogen.log`
2. 配置設定：`conf_autogen.yaml`
3. 測試結果：執行 `python -m pytest tests/autogen_system/`

---

**切換完成後，請驗證所有核心功能正常運作，並持續監控系統效能。**
