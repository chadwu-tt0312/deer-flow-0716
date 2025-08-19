# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen PPT 工作流使用範例

展示如何使用AutoGen系統生成PowerPoint演示文稿。
"""

import asyncio
import os
from pathlib import Path

# Mock OpenAIChatCompletionClient for compatibility
OpenAIChatCompletionClient = type("OpenAIChatCompletionClient", (), {})

from src.logging import get_logger
from ..workflows.ppt_workflow import PPTWorkflowManager, generate_ppt_with_autogen

logger = get_logger(__name__)


async def example_basic_ppt_generation():
    """基本PPT生成範例"""
    print("=== 基本PPT生成範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4", api_key=os.getenv("OPENAI_API_KEY", "your-api-key")
    )

    # 示例內容
    content = """
    雲端運算正在改變企業的IT基礎設施。雲端服務提供了彈性、可擴展性和成本效益，
    讓企業能夠專注於核心業務而不是技術維護。
    
    主要的雲端服務模式包括：
    1. IaaS（基礎設施即服務）- 提供虛擬化的計算資源
    2. PaaS（平台即服務）- 提供開發和部署環境
    3. SaaS（軟體即服務）- 提供完整的應用程序
    
    企業採用雲端運算的好處包括：
    - 降低IT成本
    - 提高業務靈活性
    - 增強數據安全性
    - 支援遠程工作
    - 加速創新
    
    然而，企業在雲端遷移過程中也面臨挑戰，包括數據安全、合規性要求、
    技術整合和員工培訓等問題。成功的雲端策略需要仔細規劃和漸進式實施。
    """

    try:
        print("開始生成PPT...")

        # 使用便利函數生成PPT
        result = await generate_ppt_with_autogen(
            content=content,
            model_client=model_client,
            title="企業雲端運算策略",
            audience="IT管理人員和決策者",
            duration=15,
            style="professional",
            output_format="pptx",
        )

        if result["success"]:
            print("✅ PPT生成成功！")
            print(f"   - 執行時間: {result.get('execution_time', 0):.2f} 秒")
            print(f"   - 完成步驟: {result.get('steps_completed', 0)}")

            # 檢查生成的檔案
            file_path = result.get("generated_file_path")
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"   - 檔案路徑: {file_path}")
                print(f"   - 檔案大小: {file_size} bytes")

            # 顯示大綱預覽
            outline = result.get("outline")
            if outline and outline.get("slides"):
                print(f"\n演示文稿大綱:")
                print(f"   - 標題: {outline.get('title', 'N/A')}")
                print(f"   - 聽眾: {outline.get('audience', 'N/A')}")
                print(f"   - 時長: {outline.get('duration', 'N/A')} 分鐘")
                print(f"   - 投影片數量: {len(outline['slides'])}")

                for i, slide in enumerate(outline["slides"][:3]):  # 只顯示前3張
                    slide_num = slide.get("slide_number", i + 1)
                    slide_title = slide.get("title", f"投影片 {slide_num}")
                    slide_type = slide.get("type", "content")
                    print(f"     {slide_num}. {slide_title} ({slide_type})")

                if len(outline["slides"]) > 3:
                    print(f"     ... (還有 {len(outline['slides']) - 3} 張投影片)")

            # 顯示Markdown內容預覽
            markdown = result.get("markdown_content")
            if markdown:
                lines = markdown.split("\n")
                preview_lines = lines[:10]  # 前10行
                print(f"\nMarkdown內容預覽:")
                for line in preview_lines:
                    if line.strip():
                        print(f"   {line}")

                if len(lines) > 10:
                    print(f"   ... (還有 {len(lines) - 10} 行)")
        else:
            print(f"❌ PPT生成失敗: {result.get('error')}")

    except Exception as e:
        print(f"❌ 範例執行失敗: {e}")


async def example_advanced_ppt_generation():
    """進階PPT生成範例"""
    print("\n=== 進階PPT生成範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4", api_key=os.getenv("OPENAI_API_KEY", "your-api-key")
    )

    # 創建PPT工作流管理器
    manager = PPTWorkflowManager(model_client)

    # 複雜內容示例
    content = """
    人工智慧在教育領域的應用正在重塑傳統的教學模式。AI技術為個性化學習、
    智能評估和教學輔助提供了新的可能性。
    
    主要應用領域：
    
    1. 個性化學習系統
    - 根據學生的學習進度和能力調整教學內容
    - 提供個性化的學習路徑和資源推薦
    - 即時反饋和進度追蹤
    
    2. 智能導師系統
    - 24/7可用的虛擬教學助手
    - 自然語言處理支援多語言互動
    - 解答學生疑問和提供學習指導
    
    3. 自動化評估
    - 智能批改作業和考試
    - 語音和寫作能力評估
    - 學習成效分析和預測
    
    4. 內容創建和課程設計
    - 自動生成教學材料
    - 課程內容優化建議
    - 多媒體教學資源製作
    
    實施挑戰：
    - 數據隱私和安全保護
    - 技術基礎設施建設
    - 教師培訓和技能提升
    - 成本效益平衡
    - 教育公平性考量
    
    未來發展趨勢：
    - 更智能的學習分析
    - 沈浸式學習體驗（VR/AR）
    - 跨平台學習生態系統
    - 終身學習支援
    """

    try:
        print("開始進階PPT生成...")

        result = await manager.generate_ppt(
            content=content,
            title="AI在教育領域的創新應用",
            audience="教育工作者和技術決策者",
            duration=25,
            style="academic",
            output_format="pdf",  # 生成PDF格式
        )

        if result["success"]:
            print("✅ 進階PPT生成成功！")
            print(f"   - 執行時間: {result.get('execution_time', 0):.2f} 秒")
            print(f"   - 完成步驟: {result.get('steps_completed', 0)}")
            print(f"   - 生成時間: {result.get('generated_at')}")

            # 分析大綱結構
            outline = result.get("outline")
            if outline and outline.get("slides"):
                slides = outline["slides"]

                # 統計投影片類型
                slide_types = {}
                total_time = 0

                for slide in slides:
                    slide_type = slide.get("type", "content")
                    slide_types[slide_type] = slide_types.get(slide_type, 0) + 1
                    total_time += slide.get("estimated_time", 0)

                print(f"\n演示文稿結構分析:")
                print(f"   - 總投影片: {len(slides)}")
                print(f"   - 預估總時長: {total_time} 分鐘")
                print(f"   - 投影片類型分布:")
                for slide_type, count in slide_types.items():
                    print(f"     * {slide_type}: {count} 張")

                # 顯示詳細大綱
                print(f"\n詳細大綱:")
                for slide in slides:
                    slide_num = slide.get("slide_number", 0)
                    slide_title = slide.get("title", "未命名")
                    slide_time = slide.get("estimated_time", 0)
                    key_points = slide.get("key_points", [])

                    print(f"   {slide_num}. {slide_title} ({slide_time}分鐘)")
                    for point in key_points[:2]:  # 只顯示前兩個要點
                        print(f"      - {point}")
                    if len(key_points) > 2:
                        print(f"      - ... (還有 {len(key_points) - 2} 個要點)")

            # 檢查生成的檔案
            file_path = result.get("generated_file_path")
            if file_path:
                print(f"\n檔案資訊:")
                print(f"   - 路徑: {file_path}")
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"   - 大小: {file_size} bytes")
                    print(f"   - 格式: {Path(file_path).suffix}")
                else:
                    print(f"   - 狀態: 檔案不存在（可能是模擬模式）")
        else:
            print(f"❌ 進階PPT生成失敗: {result.get('error')}")

    except Exception as e:
        print(f"❌ 進階範例執行失敗: {e}")


async def example_multiple_formats():
    """多格式輸出範例"""
    print("\n=== 多格式輸出範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4", api_key=os.getenv("OPENAI_API_KEY", "your-api-key")
    )

    manager = PPTWorkflowManager(model_client)

    # 簡短內容示例
    content = """
    數位轉型是企業在數位時代保持競爭力的關鍵策略。它不僅涉及技術升級，
    更是組織文化和業務流程的全面變革。
    
    核心要素包括：
    1. 技術基礎設施現代化
    2. 數據驅動決策
    3. 客戶體驗優化
    4. 員工數位技能提升
    5. 商業模式創新
    
    成功的數位轉型需要高層承諾、跨部門協作和持續的文化變革。
    """

    formats_to_test = [
        ("pptx", "PowerPoint格式"),
        ("pdf", "PDF格式"),
        ("html", "HTML格式"),
        ("md", "Markdown格式"),
    ]

    print("測試不同輸出格式...")

    for output_format, format_name in formats_to_test:
        try:
            print(f"\n正在生成 {format_name}...")

            result = await manager.generate_ppt(
                content=content,
                title="數位轉型策略指南",
                audience="企業管理層",
                duration=10,
                style="business",
                output_format=output_format,
            )

            if result["success"]:
                file_path = result.get("generated_file_path", "")
                execution_time = result.get("execution_time", 0)

                print(f"   ✅ {format_name} 生成成功")
                print(f"      - 執行時間: {execution_time:.2f} 秒")
                print(f"      - 檔案路徑: {file_path}")

                if file_path and os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"      - 檔案大小: {file_size} bytes")
            else:
                print(f"   ❌ {format_name} 生成失敗: {result.get('error')}")

        except Exception as e:
            print(f"   ❌ {format_name} 生成異常: {e}")

    print("\n格式支援說明:")
    print("   - PPTX: 需要Marp CLI支援，否則降級為Markdown")
    print("   - PDF: 需要Marp CLI支援，否則降級為Markdown")
    print("   - HTML: 需要Marp CLI支援，否則降級為Markdown")
    print("   - MD: 原生支援，無需額外工具")


async def example_workflow_customization():
    """工作流自定義範例"""
    print("\n=== 工作流自定義範例 ===")

    # 創建模型客戶端
    model_client = OpenAIChatCompletionClient(
        model="gpt-4", api_key=os.getenv("OPENAI_API_KEY", "your-api-key")
    )

    manager = PPTWorkflowManager(model_client)

    # 檢查Marp CLI狀態
    import subprocess

    try:
        result = subprocess.run(["marp", "--version"], capture_output=True, text=True, timeout=5)
        marp_available = result.returncode == 0
        marp_version = result.stdout.strip() if marp_available else None
    except:
        marp_available = False
        marp_version = None

    print(f"Marp CLI 狀態: {'✅ 已安裝' if marp_available else '❌ 未安裝'}")
    if marp_version:
        print(f"   版本: {marp_version}")

    if not marp_available:
        print("   提示: 安裝Marp CLI以獲得完整功能")
        print("   npm install -g @marp-team/marp-cli")
        print()

    # 測試工作流計劃創建
    try:
        print("測試工作流計劃創建...")

        plan = manager._create_ppt_plan(
            content="測試內容",
            title="測試演示",
            audience="測試聽眾",
            duration=10,
            style="modern",
            output_format="pptx",
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

        # 測試提示生成
        outline_prompt = manager._get_outline_prompt("測試標題", "測試聽眾", 15)
        slide_prompt = manager._get_slide_prompt("professional")

        print(f"提示生成測試:")
        print(f"   - 大綱提示長度: {len(outline_prompt)} 字符")
        print(f"   - 投影片提示長度: {len(slide_prompt)} 字符")

    except Exception as e:
        print(f"❌ 自定義範例失敗: {e}")


async def main():
    """主函數"""
    print("AutoGen PPT 工作流使用範例")
    print("=" * 50)

    # 檢查必要的環境變量
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠️  警告: 未設置 OPENAI_API_KEY，將使用測試密鑰")
        print("   實際使用時請設置有效的OpenAI API密鑰")
        print()

    try:
        # 運行所有範例
        await example_basic_ppt_generation()
        await example_advanced_ppt_generation()
        await example_multiple_formats()
        await example_workflow_customization()

        print("\n" + "=" * 50)
        print("✅ 所有PPT工作流範例執行完成")

        print("\n📚 使用指南:")
        print("1. 基本生成: 使用便利函數快速生成PPT")
        print("2. 進階生成: 使用管理器進行詳細配置")
        print("3. 多格式支援: 支援PPTX、PDF、HTML、Markdown")
        print("4. 工作流自定義: 了解內部工作流結構")
        print("5. Marp CLI: 安裝以獲得完整的PPT生成功能")

    except Exception as e:
        print(f"\n❌ 範例執行失敗: {e}")


if __name__ == "__main__":
    # 運行範例
    asyncio.run(main())
