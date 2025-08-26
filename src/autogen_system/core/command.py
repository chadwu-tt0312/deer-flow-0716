# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen 版本的 Command 流程控制系統

模擬 LangGraph 的 Command 模式，提供類似的流程控制功能。
"""

from typing import Dict, Any, Optional, Union, Literal, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AutoGenCommand:
    """
    AutoGen 版本的 Command 對象

    模擬 LangGraph 的 Command 功能，用於控制工作流的下一步行動。
    """

    # 狀態更新
    update: Dict[str, Any]

    # 下一個目標（類似 LangGraph 的 goto）
    goto: Union[str, Literal["__end__"]]

    # 額外的元數據
    metadata: Optional[Dict[str, Any]] = None

    # 創建時間
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "update": self.update,
            "goto": self.goto,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutoGenCommand":
        """從字典創建 Command"""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])

        return cls(
            update=data.get("update", {}),
            goto=data.get("goto", "__end__"),
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
        )

    def is_terminal(self) -> bool:
        """檢查是否為終止命令"""
        return self.goto == "__end__"


class CommandHandler:
    """
    Command 處理器

    負責處理 AutoGenCommand 並更新工作流狀態。
    """

    def __init__(self):
        self.state: Dict[str, Any] = {}
        self.command_history: List[AutoGenCommand] = []

    def process_command(self, command: AutoGenCommand) -> Dict[str, Any]:
        """
        處理 Command 並更新狀態

        Args:
            command: 要處理的 Command

        Returns:
            更新後的狀態
        """
        # 記錄命令歷史
        self.command_history.append(command)

        # 更新狀態
        self.state.update(command.update)

        # 添加流程控制信息
        self.state["_last_goto"] = command.goto
        self.state["_last_command_time"] = command.timestamp

        return self.state.copy()

    def get_next_target(self) -> Optional[str]:
        """獲取下一個目標"""
        if self.command_history:
            last_command = self.command_history[-1]
            return last_command.goto
        return None

    def is_workflow_complete(self) -> bool:
        """檢查工作流是否完成"""
        if self.command_history:
            last_command = self.command_history[-1]
            return last_command.is_terminal()
        return False

    def clear_history(self):
        """清除命令歷史"""
        self.command_history.clear()
        self.state.clear()


def create_handoff_command(
    research_topic: str,
    locale: str,
    goto: str = "planner",
    enable_background_investigation: bool = False,
    additional_updates: Optional[Dict[str, Any]] = None,
) -> AutoGenCommand:
    """
    創建 handoff 命令（類似 coordinator_node 的返回）

    Args:
        research_topic: 研究主題
        locale: 語言設置
        goto: 下一個目標
        enable_background_investigation: 是否啟用背景調查
        additional_updates: 額外的狀態更新

    Returns:
        AutoGenCommand 對象
    """
    update = {
        "locale": locale,
        "research_topic": research_topic,
    }

    # 添加額外更新
    if additional_updates:
        update.update(additional_updates)

    # 背景調查邏輯
    if enable_background_investigation and goto == "planner":
        goto = "background_investigator"

    return AutoGenCommand(
        update=update,
        goto=goto,
        metadata={
            "action": "handoff_to_planner",
            "enable_background_investigation": enable_background_investigation,
        },
    )


def create_completion_command(
    final_message: str = "任務已完成", additional_updates: Optional[Dict[str, Any]] = None
) -> AutoGenCommand:
    """
    創建完成命令

    Args:
        final_message: 最終消息
        additional_updates: 額外的狀態更新

    Returns:
        AutoGenCommand 對象
    """
    update = {"final_message": final_message, "completed": True}

    if additional_updates:
        update.update(additional_updates)

    return AutoGenCommand(
        update=update,
        goto="__end__",
        metadata={"action": "complete", "completion_reason": "task_finished"},
    )


def parse_flow_control_to_command(flow_control_info: Dict[str, Any]) -> AutoGenCommand:
    """
    將流程控制信息轉換為 Command

    Args:
        flow_control_info: 從 CoordinatorAgentV2 提取的流程控制信息

    Returns:
        AutoGenCommand 對象
    """
    action = flow_control_info.get("action", "")
    goto = flow_control_info.get("goto", "__end__")
    research_topic = flow_control_info.get("research_topic", "")
    locale = flow_control_info.get("locale", "en-US")

    if action == "handoff_to_planner":
        return create_handoff_command(
            research_topic=research_topic,
            locale=locale,
            goto=goto,
            enable_background_investigation=flow_control_info.get(
                "enable_background_investigation", False
            ),
        )
    elif action == "complete" or goto == "__end__":
        return create_completion_command(
            final_message=flow_control_info.get("final_message", "任務已完成")
        )
    else:
        # 通用命令
        return AutoGenCommand(
            update={
                "locale": locale,
                "research_topic": research_topic,
                **{k: v for k, v in flow_control_info.items() if k not in ["action", "goto"]},
            },
            goto=goto,
            metadata={"action": action, "original_flow_control": flow_control_info},
        )
