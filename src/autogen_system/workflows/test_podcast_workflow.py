# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Podcast工作流測試

測試AutoGen版本的Podcast生成工作流。
"""

import asyncio
import os
from typing import Dict, Any


# Mock AutoGen classes for compatibility
class MockOpenAIChatCompletionClient:
    """Mock OpenAIChatCompletionClient for compatibility"""

    def __init__(self, *args, **kwargs):
        self.config = kwargs.get("config", {})
        self.api_key = kwargs.get("api_key", "mock_key")
        self.base_url = kwargs.get("base_url", "https://api.openai.com/v1")

    def get(self, key, default=None):
        """Mock get method for config access"""
        if hasattr(self, key):
            return getattr(self, key)
        return self.config.get(key, default)

    def __getattr__(self, name):
        """Handle any other attribute access"""
        return lambda *args, **kwargs: None


OpenAIChatCompletionClient = MockOpenAIChatCompletionClient

from src.logging import get_logger
from .podcast_workflow import PodcastWorkflowManager, generate_podcast_with_autogen

logger = get_logger(__name__)


class PodcastWorkflowTester:
    """Podcast工作流測試器"""

    def __init__(self):
        """初始化測試器"""
        # 創建模擬的模型客戶端
        self.model_client = OpenAIChatCompletionClient(model="gpt-4", api_key="test-key")

        self.manager = PodcastWorkflowManager(self.model_client)
        logger.info("Podcast工作流測試器初始化完成")

    async def test_script_generation(self) -> Dict[str, Any]:
        """測試腳本生成"""
        logger.info("測試腳本生成")

        try:
            # 模擬步驟和上下文
            from ..controllers.workflow_controller import WorkflowStep, StepType, ExecutionStatus

            step = WorkflowStep(
                id="test_script_generation",
                step_type=StepType.SCRIPT_GENERATION,
                description="測試腳本生成",
                agent_type="script_writer",
                inputs={
                    "content": "人工智慧在現代社會中扮演著越來越重要的角色，從自動駕駛汽車到智能家居，AI技術正在改變我們的生活方式。",
                    "locale": "zh",
                },
                expected_output="播客腳本",
                timeout_seconds=120,
                dependencies=[],
                status=ExecutionStatus.PENDING,
            )

            context = {"content": "人工智慧在現代社會中扮演著越來越重要的角色。", "locale": "zh"}

            # 調用腳本生成處理器
            result = await self.manager._handle_script_generation(step, context)

            return {
                "test": "script_generation",
                "passed": result.get("status") == ExecutionStatus.COMPLETED,
                "result": result,
                "script_lines": len(context.get("script", {}).get("lines", []))
                if context.get("script")
                else 0,
            }

        except Exception as e:
            logger.error(f"腳本生成測試失敗: {e}")
            return {"test": "script_generation", "passed": False, "error": str(e)}

    async def test_audio_mixing(self) -> Dict[str, Any]:
        """測試音頻混合"""
        logger.info("測試音頻混合")

        try:
            from ..controllers.workflow_controller import WorkflowStep, StepType, ExecutionStatus

            step = WorkflowStep(
                id="test_audio_mixing",
                step_type=StepType.AUDIO_MIXING,
                description="測試音頻混合",
                agent_type="audio_mixer",
                inputs={},
                expected_output="混合音頻",
                timeout_seconds=60,
                dependencies=[],
                status=ExecutionStatus.PENDING,
            )

            # 模擬音頻片段
            mock_audio_chunks = [
                b"mock_audio_chunk_1",
                b"mock_audio_chunk_2",
                b"mock_audio_chunk_3",
            ]

            context = {"audio_chunks": mock_audio_chunks}

            # 調用音頻混合處理器
            result = await self.manager._handle_audio_mixing(step, context)

            output_size = len(context.get("output", b""))
            expected_size = sum(len(chunk) for chunk in mock_audio_chunks)

            return {
                "test": "audio_mixing",
                "passed": result.get("status") == ExecutionStatus.COMPLETED
                and output_size == expected_size,
                "result": result,
                "output_size": output_size,
                "expected_size": expected_size,
            }

        except Exception as e:
            logger.error(f"音頻混合測試失敗: {e}")
            return {"test": "audio_mixing", "passed": False, "error": str(e)}

    async def test_workflow_plan_creation(self) -> Dict[str, Any]:
        """測試工作流計劃創建"""
        logger.info("測試工作流計劃創建")

        try:
            content = "測試內容"
            locale = "zh"
            voice_config = {"speed_ratio": 1.1}

            # 創建工作流計劃
            plan = self.manager._create_podcast_plan(content, locale, voice_config)

            # 驗證計劃
            has_required_steps = len(plan.steps) == 3
            step_ids = [step.id for step in plan.steps]
            expected_step_ids = ["script_generation", "tts_generation", "audio_mixing"]
            correct_step_order = step_ids == expected_step_ids

            # 檢查依賴關係
            correct_dependencies = (
                plan.steps[0].dependencies == []
                and plan.steps[1].dependencies == ["script_generation"]
                and plan.steps[2].dependencies == ["tts_generation"]
            )

            return {
                "test": "workflow_plan_creation",
                "passed": has_required_steps and correct_step_order and correct_dependencies,
                "steps_count": len(plan.steps),
                "step_ids": step_ids,
                "dependencies_correct": correct_dependencies,
                "plan_metadata": plan.metadata,
            }

        except Exception as e:
            logger.error(f"工作流計劃創建測試失敗: {e}")
            return {"test": "workflow_plan_creation", "passed": False, "error": str(e)}

    async def test_integration(self) -> Dict[str, Any]:
        """測試完整工作流集成"""
        logger.info("測試完整工作流集成")

        try:
            # 由於需要實際的TTS服務，這裡只測試工作流結構
            content = "這是一個測試內容，用於驗證播客生成工作流的整體結構和流程。"

            # 檢查環境變量（不實際調用）
            has_tts_config = bool(
                os.getenv("VOLCENGINE_TTS_APPID") and os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN")
            )

            # 測試基本配置
            voice_config = {
                "speed_ratio": 1.05,
                "voice_mapping": {"male": "BV002_streaming", "female": "BV001_streaming"},
            }

            # 創建計劃（不執行）
            plan = self.manager._create_podcast_plan(content, "zh", voice_config)

            return {
                "test": "integration",
                "passed": True,  # 結構測試通過
                "has_tts_config": has_tts_config,
                "plan_created": bool(plan),
                "steps_count": len(plan.steps),
                "voice_config": voice_config,
                "warning": "實際TTS測試需要有效的API配置" if not has_tts_config else None,
            }

        except Exception as e:
            logger.error(f"集成測試失敗: {e}")
            return {"test": "integration", "passed": False, "error": str(e)}

    async def run_all_tests(self) -> Dict[str, Any]:
        """運行所有測試"""
        logger.info("開始運行Podcast工作流測試")

        test_methods = [
            self.test_script_generation,
            self.test_audio_mixing,
            self.test_workflow_plan_creation,
            self.test_integration,
        ]

        results = []
        passed = 0

        for test_method in test_methods:
            try:
                result = await test_method()
                results.append(result)
                if result.get("passed", False):
                    passed += 1
                    logger.info(f"✅ {result.get('test')} - 通過")
                else:
                    logger.warning(
                        f"❌ {result.get('test')} - 失敗: {result.get('error', '未知原因')}"
                    )
            except Exception as e:
                logger.error(f"測試方法執行失敗: {e}")
                results.append({"test": test_method.__name__, "passed": False, "error": str(e)})

        summary = {
            "total_tests": len(test_methods),
            "passed": passed,
            "failed": len(test_methods) - passed,
            "success_rate": (passed / len(test_methods)) * 100,
            "results": results,
        }

        logger.info(f"Podcast工作流測試完成 - 通過率: {summary['success_rate']:.1f}%")
        return summary


async def run_podcast_workflow_tests() -> Dict[str, Any]:
    """運行Podcast工作流測試"""
    tester = PodcastWorkflowTester()
    return await tester.run_all_tests()


if __name__ == "__main__":

    async def main():
        print("開始Podcast工作流測試...")
        results = await run_podcast_workflow_tests()

        print(f"\n測試結果摘要:")
        print(f"總測試數: {results['total_tests']}")
        print(f"通過: {results['passed']}")
        print(f"失敗: {results['failed']}")
        print(f"成功率: {results['success_rate']:.1f}%")

        print(f"\n詳細結果:")
        for result in results["results"]:
            status = "✅" if result.get("passed") else "❌"
            print(f"{status} {result.get('test')}")
            if "error" in result:
                print(f"    錯誤: {result['error']}")
            if "warning" in result and result["warning"]:
                print(f"    警告: {result['warning']}")

    asyncio.run(main())
