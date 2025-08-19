# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen系統測試配置

提供測試夾具和通用測試工具。
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional

# 測試用的模擬類別


class MockModelClient:
    """模擬模型客戶端"""

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or ["Mock response"]
        self.call_count = 0

    async def complete(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """模擬完成請求"""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response


class MockTool:
    """模擬工具"""

    def __init__(self, name: str, result: Any = "Mock tool result"):
        self.name = name
        self.result = result
        self.call_count = 0

    async def __call__(self, **kwargs) -> Any:
        """模擬工具調用"""
        self.call_count += 1
        return self.result


class MockWorkflowController:
    """模擬工作流控制器"""

    def __init__(self):
        self.executed_plans = []

    async def execute_plan(self, plan, initial_state, executor_func):
        """模擬執行計劃"""
        self.executed_plans.append(plan)
        # 簡單的模擬執行
        state = initial_state.copy()
        for step in plan.steps:
            state = await executor_func(step, state)
        state["status"] = "completed"
        state["execution_time"] = 1.0
        return state


class MockConversationManager:
    """模擬對話管理器"""

    def __init__(self):
        self.model_client = MockModelClient()
        self.tools = [MockTool("search"), MockTool("code_execution")]
        self.conversations = []

    async def start_conversation(self, agents, initial_message):
        """模擬開始對話"""
        conversation_id = f"conv_{len(self.conversations)}"
        self.conversations.append(
            {
                "id": conversation_id,
                "agents": agents,
                "initial_message": initial_message,
                "messages": [],
            }
        )
        return conversation_id


# 測試夾具


@pytest.fixture
def mock_model_client():
    """提供模擬模型客戶端"""
    return MockModelClient()


@pytest.fixture
def mock_tools():
    """提供模擬工具列表"""
    return [
        MockTool("search", "Search result"),
        MockTool("code_execution", "Code execution result"),
        MockTool("crawl", "Crawl result"),
    ]


@pytest.fixture
def mock_workflow_controller():
    """提供模擬工作流控制器"""
    return MockWorkflowController()


@pytest.fixture
def mock_conversation_manager():
    """提供模擬對話管理器"""
    return MockConversationManager()


@pytest.fixture
def temp_config_file():
    """提供臨時配置文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config_content = """
models:
  default:
    type: "openai"
    model: "gpt-4"
    api_key: "test-key"

agents:
  coordinator:
    model: "default"
    tools: ["search", "code_execution"]
  
  researcher:
    model: "default"
    tools: ["search", "crawl"]

tools:
  search:
    type: "tavily"
    config:
      api_key: "test-key"
  
  code_execution:
    type: "python_repl"
    config:
      timeout: 30
"""
        f.write(config_content)
        f.flush()
        yield f.name

    # 清理
    os.unlink(f.name)


@pytest.fixture
def mock_env_vars():
    """提供模擬環境變數"""
    env_vars = {
        "OPENAI_API_KEY": "test-openai-key",
        "TAVILY_API_KEY": "test-tavily-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
async def event_loop():
    """提供事件循環"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_workflow_plan():
    """提供示例工作流計劃"""
    from src.autogen_system.controllers.workflow_controller import (
        WorkflowPlan,
        WorkflowStep,
        StepType,
        ExecutionStatus,
    )

    steps = [
        WorkflowStep(
            id="step1",
            name="初始化",
            step_type=StepType.RESEARCH,
            description="初始化工作流",
            agent_type="researcher",
            inputs={"topic": "test topic"},
            dependencies=[],
            estimated_duration=10,
        ),
        WorkflowStep(
            id="step2",
            name="處理",
            step_type=StepType.PROCESSING,
            description="處理數據",
            agent_type="processor",
            inputs={"data": "test data"},
            dependencies=["step1"],
            estimated_duration=30,
        ),
    ]

    return WorkflowPlan(
        id="test_plan",
        name="測試計劃",
        description="測試用的工作流計劃",
        steps=steps,
        estimated_duration=40,
    )


@pytest.fixture
def sample_prose_request():
    """提供示例Prose請求"""
    from src.autogen_system.workflows.prose_workflow import ProseRequest, ProseOption

    return ProseRequest(
        content="This is a test content for prose processing.",
        option=ProseOption.IMPROVE,
        command=None,
    )


@pytest.fixture
def sample_prompt_enhancement_request():
    """提供示例提示增強請求"""
    from src.autogen_system.workflows.prompt_enhancer_workflow import PromptEnhancementRequest
    from src.config.report_style import ReportStyle

    return PromptEnhancementRequest(
        prompt="Write about AI", context="For academic purposes", report_style=ReportStyle.ACADEMIC
    )


# 測試實用工具


def assert_workflow_plan_valid(plan):
    """驗證工作流計劃的有效性"""
    assert plan.id is not None
    assert plan.name is not None
    assert len(plan.steps) > 0
    assert plan.estimated_duration > 0

    for step in plan.steps:
        assert step.id is not None
        assert step.name is not None
        assert step.step_type is not None
        assert step.estimated_duration > 0


def assert_agent_response_valid(response):
    """驗證代理響應的有效性"""
    assert response is not None
    assert isinstance(response, str)
    assert len(response.strip()) > 0


def create_mock_message(content: str, sender: str = "user") -> Dict[str, Any]:
    """創建模擬消息"""
    return {
        "content": content,
        "sender": sender,
        "timestamp": "2025-01-01T00:00:00Z",
    }


# 測試數據


@pytest.fixture
def sample_test_data():
    """提供示例測試數據"""
    return {
        "prompts": [
            "Write about artificial intelligence",
            "Explain climate change",
            "Create a marketing plan",
        ],
        "prose_contents": [
            "The weather today is sunny.",
            "AI is transforming industries.",
            "Climate change affects everyone.",
        ],
        "search_queries": [
            "latest AI developments",
            "renewable energy trends",
            "market analysis techniques",
        ],
    }


# 性能測試夾具


@pytest.fixture
def performance_monitor():
    """提供性能監控器"""
    import time

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.measurements = {}

        def start(self):
            self.start_time = time.time()

        def end(self):
            self.end_time = time.time()
            return self.duration

        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

        def measure(self, name: str):
            """上下文管理器用於測量特定操作"""

            class Measurement:
                def __init__(self, monitor, name):
                    self.monitor = monitor
                    self.name = name

                def __enter__(self):
                    self.start_time = time.time()
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    end_time = time.time()
                    self.monitor.measurements[self.name] = end_time - self.start_time

            return Measurement(self, name)

    return PerformanceMonitor()


# 錯誤模擬夾具


@pytest.fixture
def error_simulator():
    """提供錯誤模擬器"""

    class ErrorSimulator:
        def __init__(self):
            self.should_fail = False
            self.failure_count = 0
            self.max_failures = 1

        def enable_failures(self, max_failures: int = 1):
            """啟用失敗模擬"""
            self.should_fail = True
            self.max_failures = max_failures
            self.failure_count = 0

        def disable_failures(self):
            """禁用失敗模擬"""
            self.should_fail = False

        def check_and_fail(self, exception_class=Exception, message="Simulated failure"):
            """檢查並可能拋出異常"""
            if self.should_fail and self.failure_count < self.max_failures:
                self.failure_count += 1
                raise exception_class(message)

    return ErrorSimulator()


@pytest.fixture
def mock_config():
    """提供模擬 AgentConfig"""
    from src.autogen_system.config.agent_config import AgentConfig, AgentRole

    return AgentConfig(
        name="test_agent",
        role=AgentRole.RESEARCHER,
        system_message="You are a test agent",
        max_consecutive_auto_reply=5,
    )
