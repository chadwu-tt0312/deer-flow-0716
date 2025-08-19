#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen PromptEnhancer工作流使用示例

演示如何使用新的AutoGen-based PromptEnhancer工作流進行提示增強。
"""

import asyncio
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.autogen_system.workflows.prompt_enhancer_workflow import (
    create_prompt_enhancer_workflow_manager,
    enhance_prompt_with_autogen,
    PromptEnhancementRequest,
)
from src.config.report_style import ReportStyle


async def example_basic_prompt_enhancement():
    """基本提示增強示例"""
    print("=== 基本提示增強示例 ===")

    # 測試不同的基本提示
    basic_prompts = [
        "Write about AI",
        "Explain climate change",
        "Create a marketing plan",
        "Analyze data trends",
        "Design a user interface",
    ]

    for prompt in basic_prompts:
        try:
            print(f"\n原始提示: {prompt}")

            enhanced = await enhance_prompt_with_autogen(prompt=prompt, report_style="academic")

            print(f"增強結果: {enhanced[:150]}{'...' if len(enhanced) > 150 else ''}")
            print("-" * 50)

        except Exception as e:
            print(f"增強失敗: {e}")


async def example_different_report_styles():
    """不同報告風格示例"""
    print("\n=== 不同報告風格示例 ===")

    test_prompt = "Discuss the impact of renewable energy"

    styles = [
        ("academic", "學術風格"),
        ("popular_science", "科普風格"),
        ("news", "新聞風格"),
        ("social_media", "社交媒體風格"),
    ]

    for style, description in styles:
        try:
            print(f"\n{description} ({style}):")
            print(f"原始提示: {test_prompt}")

            enhanced = await enhance_prompt_with_autogen(prompt=test_prompt, report_style=style)

            print(f"增強結果: {enhanced[:200]}{'...' if len(enhanced) > 200 else ''}")
            print("-" * 60)

        except Exception as e:
            print(f"增強失敗: {e}")


async def example_context_aware_enhancement():
    """上下文感知增強示例"""
    print("\n=== 上下文感知增強示例 ===")

    enhancement_cases = [
        {
            "prompt": "Write a tutorial",
            "context": "For beginner programmers learning Python",
            "style": "popular_science",
        },
        {
            "prompt": "Analyze market trends",
            "context": "For quarterly business report to stakeholders",
            "style": "academic",
        },
        {
            "prompt": "Create social content",
            "context": "For technology company's LinkedIn page",
            "style": "social_media",
        },
        {
            "prompt": "Report breaking news",
            "context": "About new scientific discovery",
            "style": "news",
        },
    ]

    for case in enhancement_cases:
        try:
            print(f"\n任務場景:")
            print(f"  原始提示: {case['prompt']}")
            print(f"  上下文: {case['context']}")
            print(f"  目標風格: {case['style']}")

            enhanced = await enhance_prompt_with_autogen(
                prompt=case["prompt"], context=case["context"], report_style=case["style"]
            )

            print(f"增強結果: {enhanced[:250]}{'...' if len(enhanced) > 250 else ''}")
            print("-" * 60)

        except Exception as e:
            print(f"增強失敗: {e}")


async def example_advanced_workflow():
    """高級工作流示例"""
    print("\n=== 高級工作流示例 ===")

    # 創建工作流管理器
    workflow_manager = create_prompt_enhancer_workflow_manager()

    # 創建複雜的增強請求
    request = PromptEnhancementRequest(
        prompt="Create an educational content",
        context="For university-level computer science students studying machine learning algorithms",
        report_style=ReportStyle.ACADEMIC,
    )

    try:
        # 執行完整工作流
        result = await workflow_manager.enhance_prompt(request)

        print(f"原始提示: {result.original_prompt}")
        print(f"上下文: {result.context_used}")
        print(f"目標風格: {result.report_style_used.value}")
        print(f"增強結果: {result.enhanced_prompt}")
        print(f"處理詳情: {result.enhancement_details}")

    except Exception as e:
        print(f"工作流執行失敗: {e}")


async def example_prompt_quality_improvement():
    """提示質量改進示例"""
    print("\n=== 提示質量改進示例 ===")

    # 從模糊到具體的提示改進
    problematic_prompts = [
        {
            "prompt": "Help me",
            "context": "Need assistance with data analysis project",
            "issue": "過於模糊",
        },
        {
            "prompt": "Write something good",
            "context": "Blog post about sustainable technology",
            "issue": "缺乏具體性",
        },
        {
            "prompt": "Make it better",
            "context": "Improve user onboarding experience",
            "issue": "沒有明確目標",
        },
        {
            "prompt": "Do research",
            "context": "Market analysis for new product launch",
            "issue": "缺乏結構化指導",
        },
    ]

    for case in problematic_prompts:
        try:
            print(f"\n問題提示分析:")
            print(f"  原始提示: '{case['prompt']}'")
            print(f"  問題: {case['issue']}")
            print(f"  上下文: {case['context']}")

            enhanced = await enhance_prompt_with_autogen(
                prompt=case["prompt"], context=case["context"], report_style="academic"
            )

            print(f"改進結果: {enhanced}")
            print("-" * 60)

        except Exception as e:
            print(f"改進失敗: {e}")


async def example_batch_enhancement():
    """批量增強示例"""
    print("\n=== 批量增強示例 ===")

    # 批量處理多個提示
    prompts_batch = [
        ("Summarize this document", "news"),
        ("Create a presentation", "academic"),
        ("Write a blog post", "popular_science"),
        ("Post on social media", "social_media"),
        ("Generate a report", "academic"),
    ]

    workflow_manager = create_prompt_enhancer_workflow_manager()

    print("批量處理結果:")

    for i, (prompt, style) in enumerate(prompts_batch, 1):
        try:
            print(f"\n提示 {i}: {prompt} ({style})")

            enhanced = await workflow_manager.enhance_prompt_simple(
                prompt=prompt, report_style=style
            )

            print(f"增強結果: {enhanced[:120]}{'...' if len(enhanced) > 120 else ''}")

        except Exception as e:
            print(f"處理失敗: {e}")


async def example_iterative_enhancement():
    """迭代式增強示例"""
    print("\n=== 迭代式增強示例 ===")

    # 模擬迭代改進過程
    initial_prompt = "Teach programming"

    iterations = [
        {"context": "For beginners", "style": "popular_science", "goal": "增加目標群體信息"},
        {
            "context": "For beginners who want to learn Python for data analysis",
            "style": "popular_science",
            "goal": "具體化學習目標",
        },
        {
            "context": "For beginners who want to learn Python for data analysis, including hands-on projects",
            "style": "academic",
            "goal": "添加實踐要素並提升學術嚴謹性",
        },
    ]

    current_prompt = initial_prompt

    print(f"初始提示: {current_prompt}")

    for i, iteration in enumerate(iterations, 1):
        try:
            print(f"\n迭代 {i}: {iteration['goal']}")
            print(f"  當前提示: {current_prompt}")
            print(f"  添加上下文: {iteration['context']}")
            print(f"  目標風格: {iteration['style']}")

            enhanced = await enhance_prompt_with_autogen(
                prompt=current_prompt, context=iteration["context"], report_style=iteration["style"]
            )

            current_prompt = enhanced
            print(f"  增強結果: {enhanced}")
            print("-" * 60)

        except Exception as e:
            print(f"迭代失敗: {e}")


async def main():
    """主函數 - 運行所有示例"""
    print("AutoGen PromptEnhancer工作流示例演示\n")
    print("這些示例展示如何使用新的AutoGen-based PromptEnhancer工作流。")
    print("注意：這些是演示性示例，實際部署時需要配置真實的模型客戶端。\n")

    try:
        # 運行所有示例
        await example_basic_prompt_enhancement()
        await example_different_report_styles()
        await example_context_aware_enhancement()
        await example_advanced_workflow()
        await example_prompt_quality_improvement()
        await example_batch_enhancement()
        await example_iterative_enhancement()

        print("\n=== 所有示例執行完成 ===")
        print("PromptEnhancer工作流已成功遷移到AutoGen架構！")

    except Exception as e:
        print(f"示例執行出錯: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 運行示例
    asyncio.run(main())
