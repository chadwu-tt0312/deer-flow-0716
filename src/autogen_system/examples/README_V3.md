# AutoGen SelectorGroupChat 範例程式

這個範例程式展示如何使用 AutoGen 的 SelectorGroupChat 實現多智能體協作工作流程，取代原有的 LangGraph 架構。

## 🎯 功能特色

- **SelectorGroupChat**: 使用 AutoGen 原生的 SelectorGroupChat 實現智能體協作
- **自訂選擇器**: 實現 `selectorFunc()` 參考原有 LangGraph 的 `continue_to_running_research_team()` 邏輯
- **五個 Agent V3**: 全新設計的智能體類別，使用 AutoGen 原生架構
- **訊息框架**: 使用 AutoGen 的 message 機制取代 State 狀態管理
- **工具整合**: 整合所有現有工具（web_search, crawl_tool, python_repl 等）
- **LLM 對應**: 根據 AGENT_LLM_MAP 使用不同的 LLM（basic/reasoning）

## 📁 檔案結構

```
src/autogen_system/
├── examples/
│   ├── README.md                          # 本說明文件
│   ├── selector_group_chat_example.py     # 主要範例程式
│   └── run_example.py                     # 執行腳本
├── agents/
│   └── agents_v3.py                       # V3 版本智能體實現
├── controllers/
│   └── message_framework.py               # 訊息框架定義
└── tools/
    └── tools_integration.py               # 工具整合模組
```

## 🚀 快速開始

### 1. 環境設定

確保已設定必要的環境變數：

```bash
# Azure OpenAI 配置
export AZURE_OPENAI_ENDPOINT="your_endpoint"
export BASIC_MODEL__API_KEY="your_basic_model_key"
export REASONING_MODEL__API_KEY="your_reasoning_model_key"

# 其他可選配置
export AZURE_DEPLOYMENT_NAME_4_1_MINI="gpt-4o-mini"
export AZURE_DEPLOYMENT_NAME_4_1="gpt-4o"
export BASIC_MODEL__API_VERSION="2024-08-01-preview"
```

### 2. 配置檔案

確保 `conf_autogen.yaml` 存在並包含 V3 智能體配置：

```yaml
# V3 版本智能體配置 (AutoGen SelectorGroupChat)
agents:
  coordinator_v3:
    name: "CoordinatorAgentV3"
    role: "coordinator"
    system_message: "你是協調者智能體..."
    llm_config_override:
      temperature: 0.3
      max_tokens: 2000
  # ... 其他 V3 智能體配置
```

### 3. 執行範例

#### 方法 1: 從專案根目錄執行（推薦）

```bash
# 測試設置是否正確
python test_selector_setup.py

# 執行範例程式
python run_selector_example.py
```

#### 方法 2: 使用模組內執行腳本

```bash
cd src/autogen_system/examples
python run_example.py
```

#### 方法 3: 直接執行主程式

```bash
# 從專案根目錄
python -m src.autogen_system.examples.selector_group_chat_example

# 或從範例目錄
cd src/autogen_system/examples
python selector_group_chat_example.py
```

#### 方法 4: 在 Python 中使用

```python
import asyncio
from src.autogen_system.examples.selector_group_chat_example import run_workflow_example

# 定義任務
task = """
請研究人工智慧在教育領域的最新應用，包括：
1. 搜尋相關的最新研究論文和技術報告
2. 分析主要的應用場景和技術特點
3. 整理相關數據並進行簡單的統計分析
4. 生成一份詳細的研究報告
"""

# 執行工作流程
asyncio.run(run_workflow_example(task))
```

> **注意**: 所有核心模組已重新組織到相應的目錄中，導入路徑會自動處理。

## 🤖 智能體架構

### CoordinatorAgentV3 (協調者)
- **LLM**: Basic Model
- **職責**: 分析任務需求，制定工作流程策略
- **工具**: MCP 管理工具

### PlannerAgentV3 (規劃者)
- **LLM**: Basic Model
- **職責**: 制定詳細執行計劃，分解任務步驟
- **工具**: 無特定工具

### ResearcherAgentV3 (研究者)
- **LLM**: Basic Model
- **職責**: 網路搜尋和資訊收集
- **工具**: web_search, crawl_website, local_search

### CoderAgentV3 (程式設計師)
- **LLM**: Reasoning Model
- **職責**: 程式碼執行和數據分析
- **工具**: python_repl, 各種 Python 套件

### ReporterAgentV3 (報告者)
- **LLM**: Reasoning Model
- **職責**: 整理資訊，生成最終報告
- **工具**: 無特定工具

## 🔄 工作流程

1. **CoordinatorAgentV3**: 分析任務需求
2. **PlannerAgentV3**: 制定執行計劃
3. **循環執行**:
   - **ResearcherAgentV3**: 執行研究步驟
   - **CoderAgentV3**: 執行程式碼步驟
   - **PlannerAgentV3**: 檢查進度，決定下一步
4. **ReporterAgentV3**: 生成最終報告
5. **結束**: 當 ReporterAgentV3 標示 "WORKFLOW_COMPLETE" 時結束

## 📨 訊息框架

使用結構化的 JSON 訊息在 Agent 間傳遞資訊：

### 協調訊息
```json
{
  "message_type": "coordination",
  "agent_name": "CoordinatorAgentV3",
  "data": {
    "task_analysis": "任務分析結果",
    "workflow_strategy": "工作流程策略",
    "coordination_complete": true
  }
}
```

### 計劃訊息
```json
{
  "message_type": "plan",
  "agent_name": "PlannerAgentV3",
  "data": {
    "steps": [...],
    "original_task": "原始任務",
    "analysis": "分析結果",
    "total_steps": 3,
    "completed_steps": []
  }
}
```

### 研究結果訊息
```json
{
  "message_type": "research_result",
  "agent_name": "ResearcherAgentV3",
  "data": {
    "step_id": "step_1",
    "search_results": [...],
    "summary": "研究摘要",
    "sources": [...],
    "research_complete": true
  }
}
```

## 🔧 選擇器邏輯

`selectorFunc()` 基於以下邏輯決定下一個發言的智能體：

1. **初始階段**: CoordinatorAgentV3 → PlannerAgentV3
2. **計劃階段**: 
   - 無計劃 → 保持 PlannerAgentV3
   - 有計劃 → 根據步驟類型選擇 ResearcherAgentV3 或 CoderAgentV3
3. **執行階段**: 
   - 研究完成 → 回到 PlannerAgentV3 檢查進度
   - 程式碼完成 → 回到 PlannerAgentV3 檢查進度
4. **完成階段**: 所有步驟完成 → ReporterAgentV3
5. **結束階段**: 報告完成 → 結束工作流程

## 🛠️ 自訂和擴展

### 添加新的智能體

1. 在 `src/autogen_system/agents/agents_v3.py` 中創建新的智能體類別
2. 在 `conf_autogen.yaml` 中添加配置
3. 在 `src/config/agents.py` 中添加 LLM 映射
4. 在 `selectorFunc()` 中添加選擇邏輯

### 添加新的工具

1. 在 `src/autogen_system/tools/tools_integration.py` 中註冊新工具
2. 在智能體的 `get_tools_for_agent()` 中分配給相應智能體

### 自訂訊息類型

1. 在 `src/autogen_system/controllers/message_framework.py` 中定義新的訊息類型
2. 在 `parse_workflow_message()` 中添加解析邏輯

## 🐛 故障排除

### 快速診斷

首先執行設置測試腳本：

```bash
python test_selector_setup.py
```

這個腳本會檢查所有必要的設置並提供詳細的診斷資訊。

### 常見問題

1. **相對導入錯誤**
   ```
   ImportError: attempted relative import with no known parent package
   ```
   解決：使用專案根目錄的執行腳本 `python run_selector_example.py`

2. **環境變數未設定**
   ```
   ❌ 請設定 AZURE_OPENAI_ENDPOINT 環境變數
   ```
   解決：設定所有必要的環境變數（參考 test_selector_setup.py 的輸出）

3. **配置檔案不存在**
   ```
   ❌ 配置檔案不存在: conf_autogen.yaml
   ```
   解決：確保配置檔案存在於專案根目錄

4. **工具初始化失敗**
   ```
   ❌ 工具初始化失敗: ...
   ```
   解決：檢查工具依賴和權限設定

5. **智能體創建失敗**
   ```
   ❌ 智能體創建失敗: ...
   ```
   解決：檢查 LLM 配置和 API 金鑰

6. **AutoGen 依賴缺失**
   ```
   ModuleNotFoundError: No module named 'autogen_agentchat'
   ```
   解決：安裝 AutoGen 依賴
   ```bash
   pip install autogen-agentchat autogen-core autogen-ext
   ```

### 除錯模式

設定環境變數啟用詳細日誌：

```bash
export LOG_LEVEL=DEBUG
python run_selector_example.py
```

### 執行順序

1. `python test_selector_setup.py` - 檢查設置
2. `python run_selector_example.py` - 執行範例
3. 查看 `logs/` 目錄中的日誌檔案

## 📊 效能監控

工作流程執行過程中會產生詳細的日誌，位於 `logs/` 目錄：

- `YYYYMMDD.log`: 主要執行日誌
- `YYYYMMDD-http.log`: HTTP 請求日誌（如有）

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request 來改進這個範例程式！

## 📄 授權

Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
SPDX-License-Identifier: MIT
