# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
系統切換器

提供 LangGraph 和 AutoGen 系統之間的動態切換功能。
"""

import os
import asyncio
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime


# 使用實際的 AutoGen 類別
from autogen_core.models import ChatCompletionClient

from src.deerflow_logging import get_logger
from src.config.report_style import ReportStyle
from src.rag.retriever import Resource

logger = get_logger(__name__)


class SystemType(Enum):
    """系統類型"""

    LANGGRAPH = "langgraph"
    AUTOGEN = "autogen"


class SystemSwitcher:
    """
    系統切換器

    動態選擇使用 LangGraph 或 AutoGen 系統執行工作流。
    """

    def __init__(self, default_system: SystemType = SystemType.AUTOGEN):
        """
        初始化系統切換器

        Args:
            default_system: 預設系統類型
        """
        self.default_system = default_system
        self.current_system = self._detect_system()
        self.performance_stats = {
            SystemType.LANGGRAPH: {"count": 0, "total_time": 0, "errors": 0},
            SystemType.AUTOGEN: {"count": 0, "total_time": 0, "errors": 0},
        }

        logger.info(f"系統切換器初始化完成，當前系統: {self.current_system.value}")

    def _detect_system(self) -> SystemType:
        """檢測應使用的系統"""
        # 檢查環境變數
        env_system = os.getenv("USE_AUTOGEN_SYSTEM", "true").lower()

        if env_system in ["true", "1", "yes", "on"]:
            return SystemType.AUTOGEN
        elif env_system in ["false", "0", "no", "off"]:
            return SystemType.LANGGRAPH
        else:
            return self.default_system

    def get_current_system(self) -> SystemType:
        """獲取當前系統類型"""
        return self.current_system

    def switch_system(self, system_type: SystemType):
        """切換系統"""
        old_system = self.current_system
        self.current_system = system_type
        logger.info(f"系統已切換: {old_system.value} -> {system_type.value}")

    async def run_workflow(
        self,
        user_input: str,
        workflow_type: str = "research",
        model_client: Optional[ChatCompletionClient] = None,
        force_system: Optional[SystemType] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        執行工作流（自動選擇系統）

        Args:
            user_input: 用戶輸入
            workflow_type: 工作流類型
            model_client: 模型客戶端
            force_system: 強制使用的系統類型
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        # 決定使用的系統
        system_to_use = force_system or self.current_system

        start_time = datetime.now()

        try:
            if system_to_use == SystemType.AUTOGEN:
                result = await self._run_autogen_workflow(
                    user_input, workflow_type, model_client, **kwargs
                )
            else:
                result = await self._run_langgraph_workflow(
                    user_input, workflow_type, model_client, **kwargs
                )

            # 記錄成功統計
            execution_time = (datetime.now() - start_time).total_seconds()
            self.performance_stats[system_to_use]["count"] += 1
            self.performance_stats[system_to_use]["total_time"] += execution_time

            # 添加系統標識
            result["system_used"] = system_to_use.value
            result["execution_time"] = execution_time

            return result

        except Exception as e:
            # 記錄錯誤統計
            self.performance_stats[system_to_use]["errors"] += 1

            logger.error(f"{system_to_use.value} 系統執行失敗: {e}")

            # 如果不是強制指定系統，嘗試回退到另一個系統
            if not force_system and system_to_use != self.default_system:
                logger.info(f"嘗試回退到 {self.default_system.value} 系統")
                return await self.run_workflow(
                    user_input,
                    workflow_type,
                    model_client,
                    force_system=self.default_system,
                    **kwargs,
                )

            # 回傳錯誤結果
            return {
                "success": False,
                "error": str(e),
                "system_used": system_to_use.value,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "user_input": user_input,
                "timestamp": datetime.now().isoformat(),
            }

    async def _run_autogen_workflow(
        self,
        user_input: str,
        workflow_type: str,
        model_client: Optional[ChatCompletionClient],
        **kwargs,
    ) -> Dict[str, Any]:
        """執行 AutoGen 工作流"""
        logger.info(f"使用 AutoGen 系統執行 {workflow_type} 工作流")

        if workflow_type == "research":
            from src.autogen_system.compatibility.api_adapter import run_agent_workflow_async

            return await run_agent_workflow_async(
                user_input=user_input, model_client=model_client, **kwargs
            )
        elif workflow_type == "podcast":
            from src.autogen_system.workflows.podcast_workflow import PodcastWorkflowManager

            manager = PodcastWorkflowManager(model_client)
            await manager.initialize()
            return await manager.run_podcast_workflow(user_input, **kwargs)
        elif workflow_type == "ppt":
            from src.autogen_system.workflows.ppt_workflow import PPTWorkflowManager

            manager = PPTWorkflowManager(model_client)
            await manager.initialize()
            return await manager.run_ppt_workflow(user_input, **kwargs)
        elif workflow_type == "prose":
            from src.autogen_system.workflows.prose_workflow import ProseWorkflowManager

            manager = ProseWorkflowManager(model_client)
            await manager.initialize()
            return await manager.run_prose_workflow(user_input, **kwargs)
        elif workflow_type == "prompt_enhancer":
            from src.autogen_system.workflows.prompt_enhancer_workflow import (
                PromptEnhancerWorkflowManager,
            )

            manager = PromptEnhancerWorkflowManager(model_client)
            await manager.initialize()
            return await manager.run_prompt_enhancer_workflow(user_input, **kwargs)
        else:
            raise ValueError(f"不支援的 AutoGen 工作流類型: {workflow_type}")

    async def _run_langgraph_workflow(
        self,
        user_input: str,
        workflow_type: str,
        model_client: Optional[ChatCompletionClient],
        **kwargs,
    ) -> Dict[str, Any]:
        """執行 LangGraph 工作流"""
        logger.info(f"使用 LangGraph 系統執行 {workflow_type} 工作流")

        try:
            # 嘗試匯入 LangGraph 系統
            if workflow_type == "research":
                from src.workflow import run_agent_workflow_async

                return await run_agent_workflow_async(user_input=user_input, **kwargs)
            else:
                # 其他工作流可能需要不同的匯入路徑
                raise NotImplementedError(f"LangGraph {workflow_type} 工作流尚未實現")

        except ImportError as e:
            logger.error(f"LangGraph 系統不可用: {e}")
            raise Exception("LangGraph 系統不可用，請安裝相關依賴或切換到 AutoGen 系統")

    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取效能統計"""
        stats = {}

        for system_type, data in self.performance_stats.items():
            count = data["count"]
            total_time = data["total_time"]
            errors = data["errors"]

            stats[system_type.value] = {
                "execution_count": count,
                "total_execution_time": total_time,
                "average_execution_time": total_time / count if count > 0 else 0,
                "error_count": errors,
                "success_rate": (count - errors) / count * 100 if count > 0 else 0,
            }

        return {
            "current_system": self.current_system.value,
            "statistics": stats,
            "timestamp": datetime.now().isoformat(),
        }

    def recommend_system(self) -> SystemType:
        """根據效能統計推薦系統"""
        autogen_stats = self.performance_stats[SystemType.AUTOGEN]
        langgraph_stats = self.performance_stats[SystemType.LANGGRAPH]

        # 如果任一系統執行次數太少，推薦預設系統
        if autogen_stats["count"] < 5 and langgraph_stats["count"] < 5:
            return self.default_system

        # 計算效能指標
        autogen_success_rate = (
            (autogen_stats["count"] - autogen_stats["errors"]) / autogen_stats["count"]
            if autogen_stats["count"] > 0
            else 0
        )
        langgraph_success_rate = (
            (langgraph_stats["count"] - langgraph_stats["errors"]) / langgraph_stats["count"]
            if langgraph_stats["count"] > 0
            else 0
        )

        autogen_avg_time = (
            autogen_stats["total_time"] / autogen_stats["count"]
            if autogen_stats["count"] > 0
            else float("inf")
        )
        langgraph_avg_time = (
            langgraph_stats["total_time"] / langgraph_stats["count"]
            if langgraph_stats["count"] > 0
            else float("inf")
        )

        # 優先考慮成功率，其次考慮執行時間
        if autogen_success_rate > langgraph_success_rate:
            return SystemType.AUTOGEN
        elif langgraph_success_rate > autogen_success_rate:
            return SystemType.LANGGRAPH
        else:
            # 成功率相同時，選擇更快的系統
            return (
                SystemType.AUTOGEN
                if autogen_avg_time < langgraph_avg_time
                else SystemType.LANGGRAPH
            )

    def set_environment_system(self, system_type: SystemType):
        """設置環境變數來控制系統選擇"""
        os.environ["USE_AUTOGEN_SYSTEM"] = "true" if system_type == SystemType.AUTOGEN else "false"
        self.current_system = system_type
        logger.info(f"環境系統設定為: {system_type.value}")

    async def health_check(self) -> Dict[str, Any]:
        """系統健康檢查"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "current_system": self.current_system.value,
            "systems": {},
        }

        # 檢查 AutoGen 系統
        try:
            from src.autogen_system.compatibility.api_adapter import run_agent_workflow_async

            # 簡單測試
            test_result = await asyncio.wait_for(
                run_agent_workflow_async(
                    user_input="健康檢查測試", auto_accepted_plan=True, max_step_num=1
                ),
                timeout=30,
            )
            health_status["systems"]["autogen"] = {
                "available": True,
                "status": "healthy",
                "test_success": test_result.get("success", False),
            }
        except Exception as e:
            health_status["systems"]["autogen"] = {
                "available": False,
                "status": "error",
                "error": str(e),
            }

        # 檢查 LangGraph 系統
        try:
            from src.workflow import run_agent_workflow_async as langgraph_workflow

            # 簡單測試
            test_result = await asyncio.wait_for(
                langgraph_workflow(
                    user_input="健康檢查測試", auto_accepted_plan=True, max_step_num=1
                ),
                timeout=30,
            )
            health_status["systems"]["langgraph"] = {
                "available": True,
                "status": "healthy",
                "test_success": test_result.get("success", False),
            }
        except Exception as e:
            health_status["systems"]["langgraph"] = {
                "available": False,
                "status": "error",
                "error": str(e),
            }

        return health_status


# 全域切換器實例
global_system_switcher = SystemSwitcher()


# 便利函數
async def run_workflow_with_auto_switch(
    user_input: str,
    workflow_type: str = "research",
    model_client: Optional[ChatCompletionClient] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    使用自動系統切換執行工作流

    Args:
        user_input: 用戶輸入
        workflow_type: 工作流類型
        model_client: 模型客戶端
        **kwargs: 其他參數

    Returns:
        Dict[str, Any]: 執行結果
    """
    return await global_system_switcher.run_workflow(
        user_input, workflow_type, model_client, **kwargs
    )


def get_current_system() -> str:
    """獲取當前使用的系統"""
    return global_system_switcher.get_current_system().value


def switch_to_autogen():
    """切換到 AutoGen 系統"""
    global_system_switcher.switch_system(SystemType.AUTOGEN)
    global_system_switcher.set_environment_system(SystemType.AUTOGEN)


def switch_to_langgraph():
    """切換到 LangGraph 系統"""
    global_system_switcher.switch_system(SystemType.LANGGRAPH)
    global_system_switcher.set_environment_system(SystemType.LANGGRAPH)


async def system_health_check() -> Dict[str, Any]:
    """執行系統健康檢查"""
    return await global_system_switcher.health_check()


def get_system_performance_stats() -> Dict[str, Any]:
    """獲取系統效能統計"""
    return global_system_switcher.get_performance_stats()
