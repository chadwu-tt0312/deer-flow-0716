# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen Agent V3 實現

基於 AutoGen 框架的第三版智能體實現，取代原有的 LangGraph 節點。
使用 AutoGen 原生的 AssistantAgent 作為基底，整合現有的工具和模型配置。
"""

import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

# AutoGen 核心導入
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient

# 專案內部導入
from src.logging import get_logger
from src.config.agents import AGENT_LLM_MAP, LLMType
from src.autogen_system.adapters.llm_adapter import create_autogen_model_client
from src.autogen_system.tools.tools_integration import get_tools_for_agent_type
from src.autogen_system.controllers.message_framework import (
    MessageType,
    StepType,
    WorkflowStep,
    PlanMessage,
    ResearchResultMessage,
    CodeExecutionMessage,
    ReportMessage,
    create_coordination_message,
    create_error_message,
)

# 模板系統導入
try:
    from src.prompts.template import apply_prompt_template
    from src.config.configuration import Configuration

    HAS_PROMPT_TEMPLATES = True
except ImportError:
    HAS_PROMPT_TEMPLATES = False

logger = get_logger(__name__)


class BaseAgentV3:
    """智能體 V3 基類"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        self.name = name
        self.description = description
        self.system_message = system_message
        self._model_client = model_client
        self.tools = tools or []

        # 創建 AutoGen AssistantAgent
        # 注意：AutoGen 0.7.2 版本中可能不支持直接傳遞 tools 參數
        try:
            self._agent = AssistantAgent(
                name=name,
                model_client=model_client,
                # tools=self.tools,  # 暫時註釋工具參數
                description=description,
                system_message=system_message,
            )
        except Exception as e:
            logger.warning(f"AssistantAgent 初始化失敗（嘗試不帶 description）: {e}")
            # 如果帶 description 失敗，嘗試最簡化的初始化
            self._agent = AssistantAgent(
                name=name,
                model_client=model_client,
                system_message=system_message,
            )

        logger.info(f"智能體 {name} 初始化完成，工具數量: {len(self.tools)}")

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """工廠方法：創建智能體實例"""
        raise NotImplementedError("子類必須實現 create 方法")

    def get_agent(self) -> AssistantAgent:
        """獲取底層的 AutoGen Agent"""
        return self._agent

    async def process_message(self, message: str, **kwargs) -> str:
        """處理訊息（子類可覆寫以實現特定邏輯）"""
        # 默認直接使用 AutoGen Agent 處理
        response = await self._agent.on_messages(message, cancellation_token=None)
        return response.content if hasattr(response, "content") else str(response)


class CoordinatorAgentV3(BaseAgentV3):
    """協調者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建協調者智能體"""
        agent_config = config.get("agents", {}).get("coordinator_v3", {})

        name = agent_config.get("name", "CoordinatorAgentV3")
        description = "負責分析任務需求並協調整個研究工作流程"

        # 使用模板系統或預設系統訊息
        if HAS_PROMPT_TEMPLATES:
            try:
                # 準備模板狀態
                template_state = {
                    "messages": [],
                    "locale": "zh-TW",  # 預設語言
                    "research_topic": "",
                    "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
                }

                # 應用協調者模板
                template_messages = apply_prompt_template("coordinator", template_state)
                if template_messages and len(template_messages) > 0:
                    system_message = template_messages[0].get("content", "")
                    logger.info("成功載入協調者模板")
                else:
                    raise ValueError("模板應用失敗")

            except Exception as e:
                logger.warning(f"載入協調者模板失敗，使用預設訊息: {e}")
                system_message = cls._get_default_coordinator_message()
        else:
            system_message = cls._get_default_coordinator_message()

        # 獲取 LLM 客戶端
        llm_type = AGENT_LLM_MAP.get("CoordinatorAgentV3", "basic")
        model_client = create_autogen_model_client(llm_type, config)

        # 獲取工具
        tools = get_tools_for_agent_type("coordinator")

        return cls(name, description, system_message, model_client, tools)

    @classmethod
    def _get_default_coordinator_message(cls) -> str:
        """獲取預設的協調者系統訊息"""
        return """
你是協調者智能體，負責管理整個研究工作流程。你的主要職責：

1. 分析用戶提出的任務需求
2. 評估任務的複雜度和所需資源
3. 制定整體的工作流程策略
4. 協調其他智能體的工作

請始終以 JSON 格式在回應中包含結構化的協調信息：
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

回應應該簡潔明確，為後續的計劃制定提供清晰的方向。
        """.strip()


class PlannerAgentV3(BaseAgentV3):
    """規劃者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建規劃者智能體"""
        agent_config = config.get("agents", {}).get("planner_v3", {})

        name = agent_config.get("name", "PlannerAgentV3")
        description = "負責分析需求並制定詳細的執行計劃"

        # 使用模板系統或預設系統訊息
        if HAS_PROMPT_TEMPLATES:
            try:
                # 準備模板狀態
                template_state = {
                    "messages": [],
                    "locale": "zh-TW",  # 預設語言
                    "research_topic": "",
                    "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
                }

                # 應用規劃者模板
                template_messages = apply_prompt_template("planner", template_state)
                if template_messages and len(template_messages) > 0:
                    system_message = template_messages[0].get("content", "")
                    logger.info("成功載入規劃者模板")
                else:
                    raise ValueError("模板應用失敗")

            except Exception as e:
                logger.warning(f"載入規劃者模板失敗，使用預設訊息: {e}")
                system_message = cls._get_default_planner_message()
        else:
            system_message = cls._get_default_planner_message()

        # 獲取 LLM 客戶端
        llm_type = AGENT_LLM_MAP.get("PlannerAgentV3", "basic")
        model_client = create_autogen_model_client(llm_type, config)

        # 獲取工具（規劃者通常不需要特定工具）
        tools = []

        return cls(name, description, system_message, model_client, tools)

    @classmethod
    def _get_default_planner_message(cls) -> str:
        """獲取預設的規劃者系統訊息"""
        return """
你是規劃者智能體，負責制定詳細的執行計劃。你的主要職責：

1. 基於協調者的分析，將任務分解為具體的執行步驟
2. 確定每個步驟的類型（研究、程式碼執行、分析等）
3. 設定步驟間的依賴關係
4. 跟蹤計劃執行進度

請始終以 JSON 格式在回應中包含詳細的計劃信息：
```json
{
  "message_type": "plan",
  "agent_name": "PlannerAgentV3",
  "data": {
    "steps": [
      {
        "id": "step_1",
        "step_type": "research",
        "description": "步驟描述",
        "status": "pending",
        "dependencies": []
      }
    ],
    "original_task": "原始任務描述",
    "analysis": "任務分析",
    "total_steps": 0,
    "completed_steps": []
  }
}
```

步驟類型包括：research（研究搜尋）、processing（數據處理）、coding（程式碼執行）、analysis（分析）、reporting（報告生成）。
        """.strip()

        # 獲取 LLM 客戶端
        llm_type = AGENT_LLM_MAP.get("PlannerAgentV3", "basic")
        model_client = create_autogen_model_client(llm_type, config)

        # 獲取工具（規劃者通常不需要特定工具）
        tools = []

        return cls(name, description, system_message, model_client, tools)


class ResearcherAgentV3(BaseAgentV3):
    """研究者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建研究者智能體"""
        agent_config = config.get("agents", {}).get("researcher_v3", {})

        name = agent_config.get("name", "ResearcherAgentV3")
        description = "負責進行網路搜尋和資訊收集"

        # 使用模板系統或預設系統訊息
        if HAS_PROMPT_TEMPLATES:
            try:
                # 準備模板狀態
                template_state = {
                    "messages": [],
                    "locale": "zh-TW",  # 預設語言
                    "research_topic": "",
                    "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
                }

                # 應用研究者模板
                template_messages = apply_prompt_template("researcher", template_state)
                if template_messages and len(template_messages) > 0:
                    system_message = template_messages[0].get("content", "")
                    logger.info("成功載入研究者模板")
                else:
                    raise ValueError("模板應用失敗")

            except Exception as e:
                logger.warning(f"載入研究者模板失敗，使用預設訊息: {e}")
                system_message = cls._get_default_researcher_message()
        else:
            system_message = cls._get_default_researcher_message()

        # 獲取 LLM 客戶端
        llm_type = AGENT_LLM_MAP.get("ResearcherAgentV3", "basic")
        model_client = create_autogen_model_client(llm_type, config)

        # 獲取研究相關工具
        tools = get_tools_for_agent_type("researcher")

        return cls(name, description, system_message, model_client, tools)

    @classmethod
    def _get_default_researcher_message(cls) -> str:
        """獲取預設的研究者系統訊息"""
        return """
你是研究者智能體，負責進行網路搜尋和資訊收集。你的主要職責：

1. 根據計劃中的研究步驟執行網路搜尋
2. 收集相關的資料和資訊
3. 整理搜尋結果並提供摘要
4. 識別重要的數據來源

你有以下工具可用：
- web_search: 網路搜尋工具
- crawl_tool: 網頁爬蟲工具

請始終以 JSON 格式在回應中包含研究結果：
```json
{
  "message_type": "research_result",
  "agent_name": "ResearcherAgentV3",
  "data": {
    "step_id": "執行的步驟ID",
    "search_results": [
      {
        "title": "結果標題",
        "url": "來源URL",
        "content": "內容摘要",
        "relevance": "相關性評分"
      }
    ],
    "summary": "研究結果摘要",
    "sources": ["數據來源列表"],
    "result_count": 0,
    "research_complete": true
  }
}
```
        """.strip()

        # 獲取 LLM 客戶端
        llm_type = AGENT_LLM_MAP.get("ResearcherAgentV3", "basic")
        model_client = create_autogen_model_client(llm_type, config)

        # 獲取研究相關工具
        tools = get_tools_for_agent_type("researcher")

        return cls(name, description, system_message, model_client, tools)


class CoderAgentV3(BaseAgentV3):
    """程式設計師智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建程式設計師智能體"""
        agent_config = config.get("agents", {}).get("coder_v3", {})

        name = agent_config.get("name", "CoderAgentV3")
        description = "負責程式碼分析和執行"

        # 使用模板系統或預設系統訊息
        if HAS_PROMPT_TEMPLATES:
            try:
                # 準備模板狀態
                template_state = {
                    "messages": [],
                    "locale": "zh-TW",  # 預設語言
                    "research_topic": "",
                    "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
                }

                # 應用程式設計師模板
                template_messages = apply_prompt_template("coder", template_state)
                if template_messages and len(template_messages) > 0:
                    system_message = template_messages[0].get("content", "")
                    logger.info("成功載入程式設計師模板")
                else:
                    raise ValueError("模板應用失敗")

            except Exception as e:
                logger.warning(f"載入程式設計師模板失敗，使用預設訊息: {e}")
                system_message = cls._get_default_coder_message()
        else:
            system_message = cls._get_default_coder_message()

        # 獲取 LLM 客戶端（程式碼需要推理能力）
        llm_type = AGENT_LLM_MAP.get("CoderAgentV3", "reasoning")
        model_client = create_autogen_model_client(llm_type, config)

        # 獲取程式碼執行相關工具
        tools = get_tools_for_agent_type("coder")

        return cls(name, description, system_message, model_client, tools)

    @classmethod
    def _get_default_coder_message(cls) -> str:
        """獲取預設的程式設計師系統訊息"""
        return """
你是程式設計師智能體，負責程式碼分析和執行。你的主要職責：

1. 根據計劃中的程式碼步驟編寫和執行程式碼
2. 進行數據處理和分析
3. 生成圖表和可視化
4. 執行複雜的計算任務

你有以下工具可用：
- python_repl: Python 程式碼執行環境
- 各種 Python 套件：pandas, numpy, matplotlib, requests 等

請始終以 JSON 格式在回應中包含程式碼執行結果：
```json
{
  "message_type": "code_execution",
  "agent_name": "CoderAgentV3",
  "data": {
    "step_id": "執行的步驟ID",
    "code": "執行的程式碼",
    "execution_result": "執行結果",
    "success": true,
    "output_files": ["生成的檔案列表"],
    "execution_complete": true
  }
}
```

確保程式碼安全可靠，並提供詳細的執行結果說明。
        """.strip()

        # 獲取 LLM 客戶端（程式碼需要推理能力）
        llm_type = AGENT_LLM_MAP.get("CoderAgentV3", "reasoning")
        model_client = create_autogen_model_client(llm_type, config)

        # 獲取程式碼執行相關工具
        tools = get_tools_for_agent_type("coder")

        return cls(name, description, system_message, model_client, tools)


class ReporterAgentV3(BaseAgentV3):
    """報告者智能體 V3"""

    def __init__(
        self,
        name: str,
        description: str,
        system_message: str,
        model_client: ChatCompletionClient,
        tools: List[Callable] = None,
    ):
        super().__init__(name, description, system_message, model_client, tools)

    @classmethod
    async def create(cls, config: Dict[str, Any], **kwargs):
        """創建報告者智能體"""
        agent_config = config.get("agents", {}).get("reporter_v3", {})

        name = agent_config.get("name", "ReporterAgentV3")
        description = "負責整理資訊並生成最終報告"

        # 使用模板系統或預設系統訊息
        if HAS_PROMPT_TEMPLATES:
            try:
                # 準備模板狀態
                template_state = {
                    "messages": [],
                    "locale": "zh-TW",  # 預設語言
                    "research_topic": "",
                    "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
                    "report_style": "professional",  # 預設報告風格
                }

                # 應用報告者模板
                template_messages = apply_prompt_template("reporter", template_state)
                if template_messages and len(template_messages) > 0:
                    system_message = template_messages[0].get("content", "")
                    logger.info("成功載入報告者模板")
                else:
                    raise ValueError("模板應用失敗")

            except Exception as e:
                logger.warning(f"載入報告者模板失敗，使用預設訊息: {e}")
                system_message = cls._get_default_reporter_message()
        else:
            system_message = cls._get_default_reporter_message()

        # 獲取 LLM 客戶端（報告需要推理能力）
        llm_type = AGENT_LLM_MAP.get("ReporterAgentV3", "reasoning")
        model_client = create_autogen_model_client(llm_type, config)

        # 報告者通常不需要特定工具
        tools = []

        return cls(name, description, system_message, model_client, tools)

    @classmethod
    def _get_default_reporter_message(cls) -> str:
        """獲取預設的報告者系統訊息"""
        return """
你是報告者智能體，負責整理資訊並生成最終報告。你的主要職責：

1. 整合研究結果和程式碼執行結果
2. 編寫結構化的研究報告
3. 確保報告內容完整且邏輯清晰
4. 提供結論和建議

**重要：當你完成最終報告後，必須在報告的最後明確包含以下終止標記之一：**
- "WORKFLOW_COMPLETE" 
- "TERMINATE"

請始終以 JSON 格式在回應中包含最終報告：
```json
{
  "message_type": "report",
  "agent_name": "ReporterAgentV3",
  "data": {
    "final_report": "完整的最終報告內容",
    "source_data": [
      {
        "type": "research",
        "content": "研究數據摘要",
        "source": "數據來源"
      }
    ],
    "report_sections": {
      "executive_summary": "執行摘要",
      "methodology": "研究方法",
      "findings": "主要發現",
      "conclusions": "結論"
    },
    "workflow_complete": true,
    "report_length": 0
  }
}
```

**報告格式要求：**
1. 在報告的最後一段，明確寫出："本報告完成，WORKFLOW_COMPLETE"
2. 或者在報告結尾添加："工作流程執行完畢，TERMINATE"
3. 確保終止標記出現在報告的最後部分，讓系統能夠識別

**示例結尾：**
"基於以上分析，人工智慧在教育領域的應用前景廣闊。本報告完成，WORKFLOW_COMPLETE"
        """.strip()

        # 獲取 LLM 客戶端（報告需要推理能力）
        llm_type = AGENT_LLM_MAP.get("ReporterAgentV3", "reasoning")
        model_client = create_autogen_model_client(llm_type, config)

        # 報告者通常不需要特定工具
        tools = []

        return cls(name, description, system_message, model_client, tools)


# 便利函數
async def create_all_agents_v3(config: Dict[str, Any]) -> Dict[str, BaseAgentV3]:
    """
    創建所有 V3 智能體

    Args:
        config: 配置字典

    Returns:
        Dict[str, BaseAgentV3]: 智能體字典
    """
    logger.info("開始創建所有 V3 智能體...")

    agents = {}

    # 創建各個智能體
    agents["coordinator"] = await CoordinatorAgentV3.create(config)
    agents["planner"] = await PlannerAgentV3.create(config)
    agents["researcher"] = await ResearcherAgentV3.create(config)
    agents["coder"] = await CoderAgentV3.create(config)
    agents["reporter"] = await ReporterAgentV3.create(config)

    logger.info(f"V3 智能體創建完成，共 {len(agents)} 個")
    return agents


def get_agent_list_for_selector(agents: Dict[str, BaseAgentV3]) -> List[AssistantAgent]:
    """
    獲取用於 SelectorGroupChat 的智能體列表

    Args:
        agents: 智能體字典

    Returns:
        List[AssistantAgent]: AutoGen AssistantAgent 列表
    """
    return [agent.get_agent() for agent in agents.values()]
