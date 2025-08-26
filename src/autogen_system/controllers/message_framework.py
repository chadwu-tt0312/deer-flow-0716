# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 訊息框架

定義 Agent 間的訊息傳遞格式，取代原有的 State 狀態管理系統。
使用 AutoGen 原生的訊息機制來實現工作流程狀態的傳遞和管理。
"""

import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from src.logging import get_logger

logger = get_logger(__name__)


class MessageType(str, Enum):
    """訊息類型枚舉"""

    COORDINATION = "coordination"
    PLAN = "plan"
    RESEARCH_RESULT = "research_result"
    CODE_EXECUTION = "code_execution"
    REPORT = "report"
    ERROR = "error"
    STATUS_UPDATE = "status_update"


class StepType(str, Enum):
    """步驟類型枚舉（對應原有的 LangGraph 節點）"""

    RESEARCH = "research"
    PROCESSING = "processing"
    CODING = "coding"
    ANALYSIS = "analysis"
    REPORTING = "reporting"


class StepStatus(str, Enum):
    """步驟狀態枚舉"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """工作流程步驟"""

    id: str
    step_type: StepType
    description: str
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    dependencies: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

    def mark_completed(self, result: Dict[str, Any]):
        """標記步驟完成"""
        self.status = StepStatus.COMPLETED
        self.result = result

    def mark_failed(self, error: str):
        """標記步驟失敗"""
        self.status = StepStatus.FAILED
        self.error_message = error


@dataclass
class ResearchWorkflowMessage:
    """研究工作流程訊息基類"""

    message_type: MessageType
    timestamp: str
    agent_name: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_json(self) -> str:
        """轉換為 JSON 字串"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ResearchWorkflowMessage":
        """從 JSON 字串創建實例"""
        data = json.loads(json_str)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return asdict(self)


@dataclass
class PlanMessage(ResearchWorkflowMessage):
    """計劃訊息"""

    def __init__(
        self,
        agent_name: str,
        steps: List[WorkflowStep],
        original_task: str,
        analysis: str = "",
        **kwargs,
    ):
        data = {
            "steps": [asdict(step) for step in steps],
            "original_task": original_task,
            "analysis": analysis,
            "total_steps": len(steps),
            "completed_steps": [],
        }
        super().__init__(
            message_type=MessageType.PLAN,
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            data=data,
            **kwargs,
        )

    def get_steps(self) -> List[WorkflowStep]:
        """獲取步驟列表"""
        return [WorkflowStep(**step_data) for step_data in self.data["steps"]]

    def get_next_step(self) -> Optional[WorkflowStep]:
        """獲取下一個待執行的步驟"""
        completed = set(self.data.get("completed_steps", []))
        for step_data in self.data["steps"]:
            if step_data["id"] not in completed and step_data["status"] == StepStatus.PENDING:
                return WorkflowStep(**step_data)
        return None

    def mark_step_completed(self, step_id: str, result: Dict[str, Any]):
        """標記步驟完成"""
        completed_steps = self.data.get("completed_steps", [])
        if step_id not in completed_steps:
            completed_steps.append(step_id)
            self.data["completed_steps"] = completed_steps

        # 更新步驟狀態
        for step_data in self.data["steps"]:
            if step_data["id"] == step_id:
                step_data["status"] = StepStatus.COMPLETED
                step_data["result"] = result
                break


@dataclass
class ResearchResultMessage(ResearchWorkflowMessage):
    """研究結果訊息"""

    def __init__(
        self,
        agent_name: str,
        step_id: str,
        search_results: List[Dict[str, Any]],
        summary: str,
        sources: List[str] = None,
        **kwargs,
    ):
        data = {
            "step_id": step_id,
            "search_results": search_results,
            "summary": summary,
            "sources": sources or [],
            "result_count": len(search_results),
            "research_complete": True,
        }
        super().__init__(
            message_type=MessageType.RESEARCH_RESULT,
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            data=data,
            **kwargs,
        )


@dataclass
class CodeExecutionMessage(ResearchWorkflowMessage):
    """程式碼執行訊息"""

    def __init__(
        self,
        agent_name: str,
        step_id: str,
        code: str,
        execution_result: str,
        success: bool,
        output_files: List[str] = None,
        **kwargs,
    ):
        data = {
            "step_id": step_id,
            "code": code,
            "execution_result": execution_result,
            "success": success,
            "output_files": output_files or [],
            "execution_complete": True,
        }
        super().__init__(
            message_type=MessageType.CODE_EXECUTION,
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            data=data,
            **kwargs,
        )


@dataclass
class ReportMessage(ResearchWorkflowMessage):
    """報告訊息"""

    def __init__(
        self,
        agent_name: str,
        final_report: str,
        source_data: List[Dict[str, Any]],
        report_sections: Dict[str, str] = None,
        **kwargs,
    ):
        data = {
            "final_report": final_report,
            "source_data": source_data,
            "report_sections": report_sections or {},
            "workflow_complete": True,
            "report_length": len(final_report),
        }
        super().__init__(
            message_type=MessageType.REPORT,
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            data=data,
            **kwargs,
        )


def create_coordination_message(
    agent_name: str, task_analysis: str, workflow_strategy: str, **kwargs
) -> ResearchWorkflowMessage:
    """創建協調訊息"""
    data = {
        "task_analysis": task_analysis,
        "workflow_strategy": workflow_strategy,
        "coordination_complete": True,
    }
    return ResearchWorkflowMessage(
        message_type=MessageType.COORDINATION,
        timestamp=datetime.now().isoformat(),
        agent_name=agent_name,
        data=data,
        **kwargs,
    )


def create_error_message(
    agent_name: str, error: str, step_id: str = None, **kwargs
) -> ResearchWorkflowMessage:
    """創建錯誤訊息"""
    data = {"error": error, "step_id": step_id, "error_timestamp": datetime.now().isoformat()}
    return ResearchWorkflowMessage(
        message_type=MessageType.ERROR,
        timestamp=datetime.now().isoformat(),
        agent_name=agent_name,
        data=data,
        **kwargs,
    )


def create_status_update_message(
    agent_name: str, status: str, progress: Dict[str, Any] = None, **kwargs
) -> ResearchWorkflowMessage:
    """創建狀態更新訊息"""
    data = {"status": status, "progress": progress or {}, "update_time": datetime.now().isoformat()}
    return ResearchWorkflowMessage(
        message_type=MessageType.STATUS_UPDATE,
        timestamp=datetime.now().isoformat(),
        agent_name=agent_name,
        data=data,
        **kwargs,
    )


def parse_workflow_message(content: str) -> Optional[ResearchWorkflowMessage]:
    """
    解析工作流程訊息

    從 Agent 的回應內容中提取結構化的工作流程訊息。

    Args:
        content: Agent 的回應內容

    Returns:
        ResearchWorkflowMessage: 解析後的訊息對象，如果解析失敗則返回 None
    """
    try:
        # 查找 JSON 標記的訊息
        json_start = content.find("```json")
        json_end = content.find("```", json_start + 7)
        logger.info(f"content: {content}")

        if json_start != -1 and json_end != -1:
            json_content = content[json_start + 7 : json_end].strip()
            message_data = json.loads(json_content)
            logger.info(f"message_data: {message_data}")

            # 根據訊息類型創建相應的對象
            msg_type = message_data.get("message_type")
            logger.info(f"msg_type: {msg_type}")

            if msg_type == MessageType.PLAN:
                # 重建步驟對象
                steps_data = message_data["data"]["steps"]
                steps = [WorkflowStep(**step) for step in steps_data]
                return PlanMessage(
                    agent_name=message_data["agent_name"],
                    steps=steps,
                    original_task=message_data["data"]["original_task"],
                    analysis=message_data["data"].get("analysis", ""),
                    metadata=message_data.get("metadata", {}),
                )

            elif msg_type == MessageType.RESEARCH_RESULT:
                return ResearchResultMessage(
                    agent_name=message_data["agent_name"],
                    step_id=message_data["data"]["step_id"],
                    search_results=message_data["data"]["search_results"],
                    summary=message_data["data"]["summary"],
                    sources=message_data["data"].get("sources", []),
                    metadata=message_data.get("metadata", {}),
                )

            elif msg_type == MessageType.CODE_EXECUTION:
                return CodeExecutionMessage(
                    agent_name=message_data["agent_name"],
                    step_id=message_data["data"]["step_id"],
                    code=message_data["data"]["code"],
                    execution_result=message_data["data"]["execution_result"],
                    success=message_data["data"]["success"],
                    output_files=message_data["data"].get("output_files", []),
                    metadata=message_data.get("metadata", {}),
                )

            elif msg_type == MessageType.REPORT:
                return ReportMessage(
                    agent_name=message_data["agent_name"],
                    final_report=message_data["data"]["final_report"],
                    source_data=message_data["data"]["source_data"],
                    report_sections=message_data["data"].get("report_sections", {}),
                    metadata=message_data.get("metadata", {}),
                )

            else:
                # 通用訊息類型
                return ResearchWorkflowMessage(**message_data)

        return None

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"解析工作流程訊息失敗: {e}")
        return None


def extract_workflow_info(content: str) -> Dict[str, Any]:
    """
    從內容中提取工作流程資訊

    Args:
        content: 要分析的內容

    Returns:
        Dict[str, Any]: 提取的工作流程資訊
    """
    info = {
        "has_plan": "plan" in content.lower() or "步驟" in content,
        "has_research": "research" in content.lower() or "搜尋" in content or "研究" in content,
        "has_code": "code" in content.lower() or "程式" in content or "```python" in content,
        "has_report": "report" in content.lower() or "報告" in content,
        "mentions_completion": "complete" in content.lower() or "完成" in content,
        "mentions_error": "error" in content.lower() or "錯誤" in content or "失敗" in content,
    }

    return info


def format_message_for_display(message: ResearchWorkflowMessage) -> str:
    """
    格式化訊息以供顯示

    Args:
        message: 要格式化的訊息

    Returns:
        str: 格式化後的字串
    """
    formatted = f"📨 {message.message_type.value.upper()} - {message.agent_name}\n"
    formatted += f"⏰ 時間: {message.timestamp}\n"

    if message.message_type == MessageType.PLAN:
        steps_count = len(message.data.get("steps", []))
        completed_count = len(message.data.get("completed_steps", []))
        formatted += f"📋 計劃: {completed_count}/{steps_count} 步驟完成\n"

    elif message.message_type == MessageType.RESEARCH_RESULT:
        result_count = message.data.get("result_count", 0)
        formatted += f"🔍 研究結果: {result_count} 項結果\n"

    elif message.message_type == MessageType.CODE_EXECUTION:
        success = message.data.get("success", False)
        status = "✅ 成功" if success else "❌ 失敗"
        formatted += f"💻 程式碼執行: {status}\n"

    elif message.message_type == MessageType.REPORT:
        report_length = message.data.get("report_length", 0)
        formatted += f"📄 報告: {report_length} 個字符\n"

    return formatted
