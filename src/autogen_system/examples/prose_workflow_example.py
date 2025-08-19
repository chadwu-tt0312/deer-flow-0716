#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen Prose工作流使用示例

演示如何使用新的AutoGen-based Prose工作流進行文本處理。
"""

import asyncio
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.autogen_system.workflows.prose_workflow import (
    create_prose_workflow_manager,
    generate_prose_with_autogen,
    ProseOption,
    ProseRequest,
)


async def example_basic_prose_processing():
    """基本Prose處理示例"""
    print("=== 基本Prose處理示例 ===")

    # 測試內容
    original_text = """
    Artificial Intelligence has revolutionized many industries in recent years. 
    From healthcare to finance, AI is transforming how we work and live.
    """

    # 測試不同的處理選項
    options = [
        ("continue", "繼續寫作"),
        ("improve", "改進文本"),
        ("shorter", "精簡文本"),
        ("longer", "擴展文本"),
        ("fix", "修正文本"),
    ]

    for option, description in options:
        try:
            print(f"\n{description} ({option}):")
            print(f"原始文本: {original_text.strip()}")

            result = await generate_prose_with_autogen(content=original_text.strip(), option=option)

            print(f"處理結果: {result}")
            print("-" * 50)

        except Exception as e:
            print(f"處理失敗: {e}")


async def example_zap_command():
    """ZAP自定義命令示例"""
    print("\n=== ZAP自定義命令示例 ===")

    original_text = "The weather today is sunny and warm."
    custom_commands = [
        "Make it sound more poetic",
        "Write it as a haiku",
        "Make it funny",
        "Write it in a formal tone",
    ]

    for command in custom_commands:
        try:
            print(f"\n自定義命令: {command}")
            print(f"原始文本: {original_text}")

            result = await generate_prose_with_autogen(
                content=original_text, option="zap", command=command
            )

            print(f"處理結果: {result}")
            print("-" * 50)

        except Exception as e:
            print(f"處理失敗: {e}")


async def example_advanced_prose_workflow():
    """高級Prose工作流示例"""
    print("\n=== 高級Prose工作流示例 ===")

    # 創建工作流管理器
    workflow_manager = create_prose_workflow_manager()

    # 創建複雜的處理請求
    request = ProseRequest(
        content="Machine learning is a subset of artificial intelligence.",
        option=ProseOption.IMPROVE,
    )

    try:
        # 執行完整工作流
        result = await workflow_manager.process_prose(request)

        print(f"原始內容: {result.original_content}")
        print(f"處理結果: {result.processed_content}")
        print(f"使用選項: {result.option_used.value}")
        print(f"處理詳情: {result.processing_details}")

    except Exception as e:
        print(f"工作流執行失敗: {e}")


async def example_batch_processing():
    """批量處理示例"""
    print("\n=== 批量處理示例 ===")

    # 多個文本需要處理
    texts_to_process = [
        "Python is a programming language.",
        "Data science involves analyzing data.",
        "Cloud computing enables scalable applications.",
        "Cybersecurity protects digital assets.",
    ]

    # 批量改進文本
    workflow_manager = create_prose_workflow_manager()

    for i, text in enumerate(texts_to_process, 1):
        try:
            print(f"\n處理文本 {i}:")
            print(f"原始: {text}")

            result = await workflow_manager.process_prose_simple(
                content=text, option=ProseOption.IMPROVE
            )

            print(f"改進: {result}")

        except Exception as e:
            print(f"處理失敗: {e}")


async def example_interactive_prose():
    """互動式Prose處理示例"""
    print("\n=== 互動式Prose處理示例 ===")

    # 模擬用戶互動
    user_inputs = [
        {
            "content": "AI will change the world.",
            "option": "longer",
            "description": "擴展這個簡短的陳述",
        },
        {
            "content": "This is a very long and verbose sentence that contains many unnecessary words and could be simplified significantly to convey the same meaning more efficiently.",
            "option": "shorter",
            "description": "精簡這個冗長的句子",
        },
        {
            "content": "The quck brown fox jumps over the lazy dog.",
            "option": "fix",
            "description": "修正拼寫錯誤",
        },
    ]

    for input_data in user_inputs:
        try:
            print(f"\n任務: {input_data['description']}")
            print(f"原始: {input_data['content']}")

            result = await generate_prose_with_autogen(
                content=input_data["content"], option=input_data["option"]
            )

            print(f"結果: {result}")
            print("-" * 50)

        except Exception as e:
            print(f"處理失敗: {e}")


async def main():
    """主函數 - 運行所有示例"""
    print("AutoGen Prose工作流示例演示\n")
    print("這些示例展示如何使用新的AutoGen-based Prose工作流。")
    print("注意：這些是演示性示例，實際部署時需要配置真實的模型客戶端。\n")

    try:
        # 運行所有示例
        await example_basic_prose_processing()
        await example_zap_command()
        await example_advanced_prose_workflow()
        await example_batch_processing()
        await example_interactive_prose()

        print("\n=== 所有示例執行完成 ===")
        print("Prose工作流已成功遷移到AutoGen架構！")

    except Exception as e:
        print(f"示例執行出錯: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 運行示例
    asyncio.run(main())
