# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen Podcast 工作流使用範例

展示如何使用AutoGen系統生成播客音頻。
"""

import asyncio
import os
from pathlib import Path

# Mock OpenAIChatCompletionClient for compatibility
OpenAIChatCompletionClient = type("OpenAIChatCompletionClient", (), {})

from src.logging import get_logger
from ..workflows.podcast_workflow import PodcastWorkflowManager, generate_podcast_with_autogen

logger = get_logger(__name__)


async def example_basic_podcast_generation():
    """基本播客生成範例"""
    print("=== 基本播客生成範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4", api_key=os.getenv("OPENAI_API_KEY", "your-api-key")
    )

    # 示例內容
    content = """
    人工智慧（AI）正在改變我們的世界。從智能手機的語音助手到自動駕駛汽車，
    AI技術已經滲透到我們生活的各個方面。在醫療領域，AI幫助醫生更準確地診斷疾病；
    在教育領域，AI為學生提供個性化的學習體驗；在商業領域，AI優化了供應鏈管理和客戶服務。
    
    然而，AI的發展也帶來了一些挑戰。就業市場可能會受到衝擊，隱私和安全問題需要仔細考慮，
    演算法的公平性也是一個重要議題。因此，我們需要在推進AI技術發展的同時，
    也要確保它能夠造福全人類。
    """

    try:
        print("開始生成播客...")

        # 使用便利函數生成播客
        result = await generate_podcast_with_autogen(
            content=content,
            model_client=model_client,
            locale="zh",
            voice_config={
                "speed_ratio": 1.05,
                "volume_ratio": 1.0,
                "voice_mapping": {"male": "BV002_streaming", "female": "BV001_streaming"},
            },
        )

        if result["success"]:
            print("✅ 播客生成成功！")
            print(f"   - 執行時間: {result.get('execution_time', 0):.2f} 秒")
            print(f"   - 腳本行數: {len(result.get('script', {}).get('lines', []))}")
            print(f"   - 音頻大小: {len(result.get('output', b''))} bytes")

            # 保存音頻（如果有的話）
            if result.get("output"):
                output_path = Path("output/example_podcast.mp3")
                output_path.parent.mkdir(exist_ok=True)

                with open(output_path, "wb") as f:
                    f.write(result["output"])

                print(f"   - 音頻已保存到: {output_path}")

            # 顯示腳本預覽
            script = result.get("script")
            if script and script.get("lines"):
                print(f"\n腳本預覽:")
                for i, line in enumerate(script["lines"][:4]):  # 只顯示前4行
                    speaker = "👨‍💼" if line["speaker"] == "male" else "👩‍💼"
                    print(f"   {speaker} {line['paragraph']}")

                if len(script["lines"]) > 4:
                    print(f"   ... (還有 {len(script['lines']) - 4} 行)")
        else:
            print(f"❌ 播客生成失敗: {result.get('error')}")

    except Exception as e:
        print(f"❌ 範例執行失敗: {e}")


async def example_advanced_podcast_generation():
    """進階播客生成範例"""
    print("\n=== 進階播客生成範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4", api_key=os.getenv("OPENAI_API_KEY", "your-api-key")
    )

    # 創建播客工作流管理器
    manager = PodcastWorkflowManager(model_client)

    # 複雜內容示例
    content = """
    區塊鏈技術是近年來最具革命性的技術之一。它最初作為比特幣的底層技術而聞名，
    但現在已經擴展到金融、供應鏈、醫療記錄等多個領域。
    
    區塊鏈的核心特點包括去中心化、不可篡改性和透明度。每個交易都被記錄在一個區塊中，
    這些區塊通過密碼學方式連接形成鏈條。一旦資料被記錄，就無法被更改或刪除。
    
    在金融領域，區塊鏈使得點對點交易成為可能，無需傳統銀行作為中介。
    在供應鏈管理中，它提供了從原料到最終產品的完整可追溯性。
    在醫療領域，它可以安全地儲存和共享患者數據。
    
    儘管區塊鏈有巨大潛力，但也面臨著擴展性、能耗和監管等挑戰。
    未來，隨著技術的不斷改進，我們期待看到更多創新應用的出現。
    """

    # 進階語音配置
    advanced_voice_config = {
        "speed_ratio": 1.0,  # 稍慢一點，便於理解技術內容
        "volume_ratio": 1.1,  # 稍微大聲一點
        "pitch_ratio": 1.0,
        "voice_mapping": {
            "male": "BV002_streaming",  # 男性聲音
            "female": "BV001_streaming",  # 女性聲音
        },
    }

    try:
        print("開始進階播客生成...")

        result = await manager.generate_podcast(
            content=content, locale="zh", voice_config=advanced_voice_config
        )

        if result["success"]:
            print("✅ 進階播客生成成功！")
            print(f"   - 執行時間: {result.get('execution_time', 0):.2f} 秒")
            print(f"   - 完成步驟: {result.get('steps_completed', 0)}")
            print(f"   - 生成時間: {result.get('generated_at')}")

            # 分析腳本結構
            script = result.get("script")
            if script and script.get("lines"):
                male_lines = sum(1 for line in script["lines"] if line["speaker"] == "male")
                female_lines = sum(1 for line in script["lines"] if line["speaker"] == "female")

                print(f"\n腳本分析:")
                print(f"   - 總行數: {len(script['lines'])}")
                print(f"   - 男主持人: {male_lines} 行")
                print(f"   - 女主持人: {female_lines} 行")
                print(f"   - 語言: {script.get('locale', 'unknown')}")

                # 顯示對話流程
                print(f"\n對話流程預覽:")
                for i, line in enumerate(script["lines"][:6]):
                    speaker_icon = "👨‍💼" if line["speaker"] == "male" else "👩‍💼"
                    content_preview = (
                        line["paragraph"][:80] + "..."
                        if len(line["paragraph"]) > 80
                        else line["paragraph"]
                    )
                    print(f"   {i + 1}. {speaker_icon} {content_preview}")

            # 保存結果
            if result.get("output"):
                output_path = Path("output/advanced_podcast.mp3")
                output_path.parent.mkdir(exist_ok=True)

                with open(output_path, "wb") as f:
                    f.write(result["output"])

                print(f"\n   - 高級播客已保存到: {output_path}")
        else:
            print(f"❌ 進階播客生成失敗: {result.get('error')}")

    except Exception as e:
        print(f"❌ 進階範例執行失敗: {e}")


async def example_podcast_workflow_customization():
    """播客工作流自定義範例"""
    print("\n=== 播客工作流自定義範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4", api_key=os.getenv("OPENAI_API_KEY", "your-api-key")
    )

    manager = PodcastWorkflowManager(model_client)

    # 檢查TTS配置
    has_tts_config = bool(
        os.getenv("VOLCENGINE_TTS_APPID") and os.getenv("VOLCENGINE_TTS_ACCESS_TOKEN")
    )

    print(f"TTS配置狀態: {'✅ 已配置' if has_tts_config else '❌ 未配置'}")

    if not has_tts_config:
        print("提示: 需要配置以下環境變量才能進行實際的TTS生成:")
        print("  - VOLCENGINE_TTS_APPID")
        print("  - VOLCENGINE_TTS_ACCESS_TOKEN")
        print("  - VOLCENGINE_TTS_CLUSTER (可選，默認為 'volcano_tts')")
        print()

    # 創建自定義配置
    custom_content = "這是一個測試內容，用於展示播客工作流的自定義功能。"

    # 測試工作流計劃創建
    try:
        print("測試工作流計劃創建...")

        plan = manager._create_podcast_plan(
            content=custom_content, locale="zh", voice_config={"speed_ratio": 1.2}
        )

        print("✅ 工作流計劃創建成功！")
        print(f"   - 計劃ID: {plan.plan_id}")
        print(f"   - 計劃名稱: {plan.name}")
        print(f"   - 步驟數量: {len(plan.steps)}")

        print(f"\n步驟詳情:")
        for i, step in enumerate(plan.steps, 1):
            print(f"   {i}. {step.id}")
            print(f"      - 類型: {step.step_type.value}")
            print(f"      - 描述: {step.description}")
            print(f"      - 智能體: {step.agent_type}")
            print(f"      - 超時: {step.timeout_seconds}秒")
            print(f"      - 依賴: {step.dependencies}")
            print()

        # 測試聲音配置
        voice_types = manager._get_voice_type(
            "male", {"voice_mapping": {"male": "custom_male_voice"}}
        )
        print(f"自定義聲音類型測試: {voice_types}")

    except Exception as e:
        print(f"❌ 自定義範例失敗: {e}")


async def main():
    """主函數"""
    print("AutoGen Podcast 工作流使用範例")
    print("=" * 50)

    # 檢查必要的環境變量
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠️  警告: 未設置 OPENAI_API_KEY，將使用測試密鑰")
        print("   實際使用時請設置有效的OpenAI API密鑰")
        print()

    try:
        # 運行所有範例
        await example_basic_podcast_generation()
        await example_advanced_podcast_generation()
        await example_podcast_workflow_customization()

        print("\n" + "=" * 50)
        print("✅ 所有Podcast工作流範例執行完成")

        print("\n📚 使用指南:")
        print("1. 基本生成: 使用便利函數快速生成播客")
        print("2. 進階生成: 使用管理器進行高級配置")
        print("3. 工作流自定義: 了解內部工作流結構")
        print("4. TTS配置: 確保語音服務正確設置")

    except Exception as e:
        print(f"\n❌ 範例執行失敗: {e}")


if __name__ == "__main__":
    # 運行範例
    asyncio.run(main())
