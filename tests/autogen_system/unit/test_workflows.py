# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen Workflows 單元測試
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.autogen_system.workflows.prose_workflow import (
    ProseWorkflowManager,
    ProseRequest,
    ProseResult,
    ProseOption,
)
from src.autogen_system.workflows.prompt_enhancer_workflow import (
    PromptEnhancerWorkflowManager,
    PromptEnhancementRequest,
    PromptEnhancementResult,
)
from src.autogen_system.workflows.podcast_workflow import (
    PodcastWorkflowManager,
)
from src.autogen_system.workflows.ppt_workflow import (
    PPTWorkflowManager,
)
from src.config.report_style import ReportStyle


class TestProseWorkflow:
    """ProseWorkflow測試類"""

    @pytest.fixture
    def prose_workflow_manager(self, mock_conversation_manager):
        """創建ProseWorkflowManager實例"""
        return ProseWorkflowManager(mock_conversation_manager)

    @pytest.fixture
    def sample_prose_request(self):
        """創建示例Prose請求"""
        return ProseRequest(
            content="This is a test content for prose processing.",
            option=ProseOption.IMPROVE,
            command=None,
        )

    async def test_prose_workflow_manager_initialization(self, prose_workflow_manager):
        """測試ProseWorkflowManager初始化"""

        assert prose_workflow_manager.conversation_manager is not None
        assert prose_workflow_manager.workflow_controller is not None
        assert len(prose_workflow_manager.prose_prompts) == 6  # 六種選項

    async def test_create_prose_plan(self, prose_workflow_manager, sample_prose_request):
        """測試創建Prose計劃"""

        plan = await prose_workflow_manager._create_prose_plan(sample_prose_request)

        # 驗證計劃基本屬性
        assert plan.id is not None
        assert plan.name is not None
        assert len(plan.steps) == 1  # 單步驟
        assert plan.estimated_duration > 0

        # 驗證步驟屬性
        step = plan.steps[0]
        assert step.id == "prose_improve"
        assert step.name == "改進文本"
        assert step.metadata["option"] == "improve"

    async def test_prose_options(self, prose_workflow_manager):
        """測試所有Prose選項"""

        test_content = "Test content"

        for option in ProseOption:
            request = ProseRequest(
                content=test_content,
                option=option,
                command="test command" if option == ProseOption.ZAP else None,
            )

            plan = await prose_workflow_manager._create_prose_plan(request)

            # 驗證每個選項都能創建有效計劃
            assert len(plan.steps) == 1
            assert plan.steps[0].metadata["option"] == option.value

    async def test_prose_step_executor(self, prose_workflow_manager, sample_prose_request):
        """測試Prose步驟執行器"""

        # 創建模擬步驟
        from src.autogen_system.controllers.workflow_controller import WorkflowStep, StepType

        step = WorkflowStep(
            id="prose_improve",
            name="改進文本",
            step_type=StepType.STYLE_REFINEMENT,
            description="改進文本質量",
            dependencies=[],
            estimated_duration=45,
            metadata={"option": "improve"},
        )

        # 創建狀態
        state = {
            "content": sample_prose_request.content,
            "option": sample_prose_request.option.value,
            "request": sample_prose_request,
        }

        # 模擬CoderAgent響應
        with patch("src.autogen_system.agents.coder_agent.CoderAgent") as MockCoderAgent:
            mock_agent = Mock()
            mock_agent.process_request = AsyncMock(return_value="Improved text")
            MockCoderAgent.return_value = mock_agent

            # 執行步驟
            result_state = await prose_workflow_manager._prose_step_executor(step, state)

            # 驗證結果
            assert result_state["output"] == "Improved text"
            mock_agent.process_request.assert_called_once()

    async def test_process_prose_simple(self, prose_workflow_manager):
        """測試簡化Prose處理接口"""

        # 模擬完整工作流
        with patch.object(prose_workflow_manager, "process_prose") as mock_process:
            mock_result = ProseResult(
                original_content="test",
                processed_content="processed test",
                option_used=ProseOption.IMPROVE,
                processing_details={},
            )
            mock_process.return_value = mock_result

            result = await prose_workflow_manager.process_prose_simple(
                content="test", option="improve"
            )

            assert result == "processed test"

    async def test_prose_error_handling(self, prose_workflow_manager, sample_prose_request):
        """測試Prose錯誤處理"""

        # 模擬工作流控制器錯誤
        with patch.object(
            prose_workflow_manager.workflow_controller, "execute_plan"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Workflow error")

            with pytest.raises(Exception, match="Workflow error"):
                await prose_workflow_manager.process_prose(sample_prose_request)


class TestPromptEnhancerWorkflow:
    """PromptEnhancerWorkflow測試類"""

    @pytest.fixture
    def prompt_enhancer_manager(self, mock_conversation_manager):
        """創建PromptEnhancerWorkflowManager實例"""
        return PromptEnhancerWorkflowManager(mock_conversation_manager)

    @pytest.fixture
    def sample_enhancement_request(self):
        """創建示例提示增強請求"""
        return PromptEnhancementRequest(
            prompt="Write about AI",
            context="For academic purposes",
            report_style=ReportStyle.ACADEMIC,
        )

    async def test_prompt_enhancer_initialization(self, prompt_enhancer_manager):
        """測試PromptEnhancerWorkflowManager初始化"""

        assert prompt_enhancer_manager.conversation_manager is not None
        assert prompt_enhancer_manager.workflow_controller is not None

    async def test_create_enhancement_plan(
        self, prompt_enhancer_manager, sample_enhancement_request
    ):
        """測試創建增強計劃"""

        plan = await prompt_enhancer_manager._create_enhancement_plan(sample_enhancement_request)

        # 驗證計劃基本屬性
        assert plan.id is not None
        assert plan.name == "提示增強工作流"
        assert len(plan.steps) == 3  # 三個步驟：分析、生成、驗證
        assert plan.estimated_duration == 110  # 20 + 60 + 30

    async def test_enhancement_steps(self, prompt_enhancer_manager, sample_enhancement_request):
        """測試增強步驟"""

        plan = await prompt_enhancer_manager._create_enhancement_plan(sample_enhancement_request)

        # 驗證步驟順序和依賴
        step_ids = [step.id for step in plan.steps]
        expected_ids = ["prompt_analysis", "enhancement_generation", "prompt_validation"]
        assert step_ids == expected_ids

        # 驗證依賴關係
        assert plan.steps[0].dependencies == []
        assert plan.steps[1].dependencies == ["prompt_analysis"]
        assert plan.steps[2].dependencies == ["enhancement_generation"]

    async def test_extract_enhanced_prompt(self, prompt_enhancer_manager):
        """測試提取增強提示"""

        # 測試XML格式提取
        xml_response = "<enhanced_prompt>This is enhanced</enhanced_prompt>"
        result = prompt_enhancer_manager._extract_enhanced_prompt(xml_response)
        assert result == "This is enhanced"

        # 測試前綴移除
        prefix_response = "Enhanced Prompt: This is enhanced with prefix"
        result = prompt_enhancer_manager._extract_enhanced_prompt(prefix_response)
        assert result == "This is enhanced with prefix"

        # 測試純文本
        plain_response = "Just plain enhanced text"
        result = prompt_enhancer_manager._extract_enhanced_prompt(plain_response)
        assert result == "Just plain enhanced text"

    async def test_report_style_handling(self, prompt_enhancer_manager):
        """測試報告風格處理"""

        # 測試所有報告風格
        for style in ReportStyle:
            request = PromptEnhancementRequest(prompt="Test prompt", report_style=style)

            plan = await prompt_enhancer_manager._create_enhancement_plan(request)
            assert plan.metadata["report_style"] == style.value

    async def test_enhance_prompt_simple(self, prompt_enhancer_manager):
        """測試簡化提示增強接口"""

        # 模擬完整工作流
        with patch.object(prompt_enhancer_manager, "enhance_prompt") as mock_enhance:
            mock_result = PromptEnhancementResult(
                original_prompt="test",
                enhanced_prompt="enhanced test",
                context_used=None,
                report_style_used=ReportStyle.ACADEMIC,
                enhancement_details={},
            )
            mock_enhance.return_value = mock_result

            result = await prompt_enhancer_manager.enhance_prompt_simple(
                prompt="test", report_style="academic"
            )

            assert result == "enhanced test"

    async def test_error_handling(self, prompt_enhancer_manager, sample_enhancement_request):
        """測試錯誤處理"""

        # 模擬工作流執行錯誤
        with patch.object(
            prompt_enhancer_manager.workflow_controller, "execute_plan"
        ) as mock_execute:
            mock_execute.side_effect = Exception("Enhancement error")

            result = await prompt_enhancer_manager.enhance_prompt(sample_enhancement_request)

            # 應該返回原始提示而不是拋出異常
            assert result.enhanced_prompt == sample_enhancement_request.prompt
            assert "error" in result.enhancement_details


class TestPodcastWorkflow:
    """PodcastWorkflow測試類"""

    @pytest.fixture
    def podcast_workflow_manager(self, mock_conversation_manager):
        """創建PodcastWorkflowManager實例"""
        return PodcastWorkflowManager(mock_conversation_manager)

    async def test_podcast_workflow_initialization(self, podcast_workflow_manager):
        """測試PodcastWorkflowManager初始化"""

        assert podcast_workflow_manager.conversation_manager is not None
        assert podcast_workflow_manager.workflow_controller is not None

    async def test_create_podcast_plan(self, podcast_workflow_manager):
        """測試創建Podcast計劃"""

        request = {
            "topic": "AI in Healthcare",
            "duration": 600,  # 10分鐘
            "style": "interview",
        }

        plan = await podcast_workflow_manager._create_podcast_plan(request)

        # 驗證計劃結構
        assert plan.id is not None
        assert plan.name is not None
        assert len(plan.steps) >= 3  # 至少包含腳本、TTS、混音


class TestPPTWorkflow:
    """PPTWorkflow測試類"""

    @pytest.fixture
    def ppt_workflow_manager(self, mock_conversation_manager):
        """創建PPTWorkflowManager實例"""
        return PPTWorkflowManager(mock_conversation_manager)

    async def test_ppt_workflow_initialization(self, ppt_workflow_manager):
        """測試PPTWorkflowManager初始化"""

        assert ppt_workflow_manager.conversation_manager is not None
        assert ppt_workflow_manager.workflow_controller is not None

    async def test_create_ppt_plan(self, ppt_workflow_manager):
        """測試創建PPT計劃"""

        request = {
            "topic": "Machine Learning Fundamentals",
            "slides_count": 10,
            "style": "academic",
        }

        plan = await ppt_workflow_manager._create_ppt_plan(request)

        # 驗證計劃結構
        assert plan.id is not None
        assert plan.name is not None
        assert len(plan.steps) >= 3  # 至少包含大綱、內容、PPT生成


class TestWorkflowIntegration:
    """工作流集成測試"""

    async def test_workflow_manager_creation(self):
        """測試工作流管理器創建函數"""

        from src.autogen_system.workflows.prose_workflow import create_prose_workflow_manager
        from src.autogen_system.workflows.prompt_enhancer_workflow import (
            create_prompt_enhancer_workflow_manager,
        )

        # 模擬依賴創建
        with patch(
            "src.autogen_system.controllers.conversation_manager.create_conversation_manager"
        ) as mock_create:
            mock_create.return_value = Mock()

            prose_manager = create_prose_workflow_manager()
            assert isinstance(prose_manager, ProseWorkflowManager)

            enhancer_manager = create_prompt_enhancer_workflow_manager()
            assert isinstance(enhancer_manager, PromptEnhancerWorkflowManager)

    async def test_convenience_functions(self):
        """測試便利函數"""

        from src.autogen_system.workflows.prose_workflow import generate_prose_with_autogen
        from src.autogen_system.workflows.prompt_enhancer_workflow import (
            enhance_prompt_with_autogen,
        )

        # 模擬工作流管理器
        with patch(
            "src.autogen_system.workflows.prose_workflow.create_prose_workflow_manager"
        ) as mock_create_prose:
            mock_manager = Mock()
            mock_manager.process_prose_simple = AsyncMock(return_value="Enhanced prose")
            mock_create_prose.return_value = mock_manager

            result = await generate_prose_with_autogen("test content", "improve")
            assert result == "Enhanced prose"

        with patch(
            "src.autogen_system.workflows.prompt_enhancer_workflow.create_prompt_enhancer_workflow_manager"
        ) as mock_create_enhancer:
            mock_manager = Mock()
            mock_manager.enhance_prompt_simple = AsyncMock(return_value="Enhanced prompt")
            mock_create_enhancer.return_value = mock_manager

            result = await enhance_prompt_with_autogen("test prompt")
            assert result == "Enhanced prompt"

    async def test_workflow_error_propagation(self):
        """測試工作流錯誤傳播"""

        from src.autogen_system.workflows.prose_workflow import generate_prose_with_autogen

        # 模擬錯誤情況
        with patch(
            "src.autogen_system.workflows.prose_workflow.create_prose_workflow_manager"
        ) as mock_create:
            mock_manager = Mock()
            mock_manager.process_prose_simple = AsyncMock(side_effect=Exception("Workflow error"))
            mock_create.return_value = mock_manager

            with pytest.raises(Exception, match="Workflow error"):
                await generate_prose_with_autogen("test content", "improve")

    def test_prose_option_enum(self):
        """測試ProseOption枚舉"""

        # 驗證所有預期選項都存在
        expected_options = {"continue", "improve", "shorter", "longer", "fix", "zap"}
        actual_options = {option.value for option in ProseOption}

        assert expected_options == actual_options

    def test_report_style_enum(self):
        """測試ReportStyle枚舉"""

        # 驗證所有預期風格都存在
        expected_styles = {"academic", "popular_science", "news", "social_media"}
        actual_styles = {style.value for style in ReportStyle}

        assert expected_styles == actual_styles

    async def test_concurrent_workflows(self):
        """測試並發工作流執行"""

        from src.autogen_system.workflows.prose_workflow import generate_prose_with_autogen
        from src.autogen_system.workflows.prompt_enhancer_workflow import (
            enhance_prompt_with_autogen,
        )

        # 模擬並發執行
        with patch(
            "src.autogen_system.workflows.prose_workflow.create_prose_workflow_manager"
        ) as mock_prose:
            with patch(
                "src.autogen_system.workflows.prompt_enhancer_workflow.create_prompt_enhancer_workflow_manager"
            ) as mock_enhancer:
                mock_prose_manager = Mock()
                mock_prose_manager.process_prose_simple = AsyncMock(return_value="Prose result")
                mock_prose.return_value = mock_prose_manager

                mock_enhancer_manager = Mock()
                mock_enhancer_manager.enhance_prompt_simple = AsyncMock(
                    return_value="Enhancer result"
                )
                mock_enhancer.return_value = mock_enhancer_manager

                # 並發執行多個工作流
                tasks = [
                    generate_prose_with_autogen("content1", "improve"),
                    generate_prose_with_autogen("content2", "shorter"),
                    enhance_prompt_with_autogen("prompt1"),
                    enhance_prompt_with_autogen("prompt2"),
                ]

                results = await asyncio.gather(*tasks)

                assert len(results) == 4
                assert results[0] == "Prose result"
                assert results[1] == "Prose result"
                assert results[2] == "Enhancer result"
                assert results[3] == "Enhancer result"
