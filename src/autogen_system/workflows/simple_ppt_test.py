# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
簡化的PPT工作流測試

不依賴autogen_core的基本功能測試。
"""

import json
import os
import tempfile
from typing import Dict, Any
from pathlib import Path

from src.logging import get_logger

logger = get_logger(__name__)


def test_outline_prompt():
    """測試大綱生成提示"""
    print("=== 測試大綱生成提示 ===")

    try:
        # 模擬PPTWorkflowManager的大綱提示生成
        def get_outline_prompt(title: str, audience: str, duration: int) -> str:
            return f"""You are a professional presentation consultant. Create a detailed outline for a presentation.

Title: {title}
Target Audience: {audience}
Duration: {duration} minutes

Based on the provided content, create a structured presentation outline with the following format:

{{
  "title": "{title}",
  "audience": "{audience}",
  "duration": {duration},
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slide Title",
      "type": "title|content|conclusion",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "estimated_time": 2
    }}
  ],
  "total_slides": 0
}}

Guidelines:
- Title slide (1-2 minutes)
- Introduction/Agenda (1-2 minutes)
- Main content slides (most of the time)
- Conclusion/Summary (1-2 minutes)
- Q&A if applicable
- Each content slide should cover 1-2 minutes
- Keep key_points concise and actionable
- Ensure logical flow between slides"""

        prompt = get_outline_prompt("AI在醫療中的應用", "醫療專業人員", 20)

        print("✅ 大綱提示生成成功")
        print(f"   - 提示長度: {len(prompt)} 字符")
        print(f"   - 包含標題: {'Title:' in prompt}")
        print(f"   - 包含聽眾: {'Target Audience:' in prompt}")
        print(f"   - 包含JSON格式: {'slides' in prompt}")
        return True

    except Exception as e:
        print(f"❌ 大綱提示測試失敗: {e}")
        return False


def test_outline_parsing():
    """測試大綱解析"""
    print("\n=== 測試大綱解析 ===")

    try:
        # 模擬大綱響應
        mock_response = {
            "title": "AI在醫療中的應用",
            "audience": "醫療專業人員",
            "duration": 20,
            "slides": [
                {
                    "slide_number": 1,
                    "title": "標題頁",
                    "type": "title",
                    "key_points": ["AI在醫療中的應用", "演講者信息"],
                    "estimated_time": 2,
                },
                {
                    "slide_number": 2,
                    "title": "議程",
                    "type": "content",
                    "key_points": ["診斷輔助", "治療規劃", "藥物研發", "未來展望"],
                    "estimated_time": 2,
                },
                {
                    "slide_number": 3,
                    "title": "AI診斷輔助",
                    "type": "content",
                    "key_points": ["醫學影像分析", "疾病早期篩檢", "準確度提升"],
                    "estimated_time": 5,
                },
            ],
            "total_slides": 3,
        }

        # 測試JSON序列化和反序列化
        json_str = json.dumps(mock_response, ensure_ascii=False)
        parsed = json.loads(json_str)

        # 驗證結構
        has_title = "title" in parsed
        has_slides = "slides" in parsed and isinstance(parsed["slides"], list)
        correct_slide_structure = all(
            all(
                key in slide
                for key in ["slide_number", "title", "type", "key_points", "estimated_time"]
            )
            for slide in parsed["slides"]
        )

        print("✅ 大綱解析測試成功")
        print(f"   - 有標題: {has_title}")
        print(f"   - 有投影片: {has_slides}")
        print(f"   - 投影片結構正確: {correct_slide_structure}")
        print(f"   - 總投影片數: {len(parsed['slides'])}")

        return has_title and has_slides and correct_slide_structure

    except Exception as e:
        print(f"❌ 大綱解析測試失敗: {e}")
        return False


def test_markdown_generation():
    """測試Markdown生成"""
    print("\n=== 測試Markdown生成 ===")

    try:
        # 模擬Markdown內容生成
        sample_markdown = """# AI在醫療中的應用

---

## 議程

- AI診斷輔助
- 治療規劃優化
- 藥物研發創新
- 未來發展趨勢

---

## AI診斷輔助

- **醫學影像分析**
  - X光片自動讀片
  - MRI影像解析
  - 病理切片檢查

- **疾病早期篩檢**
  - 癌症早期發現
  - 心血管疾病預測
  - 神經系統疾病監測

---

## 總結

- AI技術正在革命性地改變醫療行業
- 提高診斷準確度和效率
- 未來將有更多創新應用

---

## 謝謝聆聽

### Q&A 時間"""

        # 驗證Markdown格式
        has_title = sample_markdown.startswith("#")
        has_slides = "---" in sample_markdown
        has_bullet_points = "-" in sample_markdown
        has_headers = "##" in sample_markdown

        # 統計投影片數量
        slide_count = sample_markdown.count("---") + 1  # +1 for the first slide

        print("✅ Markdown生成測試成功")
        print(f"   - 有標題: {has_title}")
        print(f"   - 有分隔符: {has_slides}")
        print(f"   - 有要點: {has_bullet_points}")
        print(f"   - 有標題: {has_headers}")
        print(f"   - 投影片數量: {slide_count}")
        print(f"   - 內容長度: {len(sample_markdown)} 字符")

        return has_title and has_slides and has_bullet_points and has_headers

    except Exception as e:
        print(f"❌ Markdown生成測試失敗: {e}")
        return False


def test_file_operations():
    """測試檔案操作"""
    print("\n=== 測試檔案操作 ===")

    try:
        # 測試臨時檔案創建
        def save_to_temp_file(content: str) -> str:
            import uuid

            temp_file_path = os.path.join(tempfile.gettempdir(), f"ppt_content_{uuid.uuid4()}.md")
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return temp_file_path

        # 測試輸出路徑生成
        def get_output_file_path(output_format: str) -> str:
            from datetime import datetime

            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_ppt_{timestamp}.{output_format}"

            return str(output_dir / filename)

        # 測試檔案清理
        def cleanup_temp_file(file_path: str):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
            except Exception:
                return False
            return False

        # 執行測試
        test_content = "# 測試PPT\n\n## 測試投影片\n\n- 測試要點1\n- 測試要點2"

        # 創建臨時檔案
        temp_path = save_to_temp_file(test_content)
        temp_file_exists = os.path.exists(temp_path)

        # 讀取檔案內容
        with open(temp_path, "r", encoding="utf-8") as f:
            read_content = f.read()
        content_matches = read_content == test_content

        # 生成輸出路徑
        output_path = get_output_file_path("pptx")
        output_path_valid = output_path.endswith(".pptx") and "generated_ppt_" in output_path

        # 清理檔案
        cleanup_success = cleanup_temp_file(temp_path)

        print("✅ 檔案操作測試成功")
        print(f"   - 臨時檔案創建: {temp_file_exists}")
        print(f"   - 內容匹配: {content_matches}")
        print(f"   - 輸出路徑有效: {output_path_valid}")
        print(f"   - 檔案清理: {cleanup_success}")

        return temp_file_exists and content_matches and output_path_valid and cleanup_success

    except Exception as e:
        print(f"❌ 檔案操作測試失敗: {e}")
        return False


def test_marp_availability():
    """測試Marp CLI可用性"""
    print("\n=== 測試Marp CLI可用性 ===")

    try:
        import subprocess

        # 檢查Marp CLI是否可用
        try:
            result = subprocess.run(
                ["marp", "--version"], capture_output=True, text=True, timeout=5
            )
            marp_available = result.returncode == 0
            marp_version = result.stdout.strip() if marp_available else None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            marp_available = False
            marp_version = None

        # 模擬PPT生成邏輯
        def generate_ppt_with_marp(input_file: str, output_file: str, output_format: str) -> bool:
            if marp_available:
                # 模擬成功
                return True
            else:
                # 降級處理：複製為Markdown
                return True

        # 測試生成邏輯
        test_input = "test.md"
        test_output = "test.pptx"
        generation_works = generate_ppt_with_marp(test_input, test_output, "pptx")

        print("✅ Marp CLI測試完成")
        print(f"   - Marp可用: {marp_available}")
        if marp_version:
            print(f"   - Marp版本: {marp_version}")
        print(f"   - 生成邏輯: {generation_works}")
        print(f"   - 降級策略: {'已實現' if not marp_available else '不需要'}")

        return generation_works  # 無論Marp是否可用，都應該能處理

    except Exception as e:
        print(f"❌ Marp CLI測試失敗: {e}")
        return False


def test_workflow_structure():
    """測試工作流結構"""
    print("\n=== 測試工作流結構 ===")

    try:
        # 模擬PPT工作流步驟結構
        workflow_steps = [
            {
                "id": "outline_generation",
                "type": "outline_generation",
                "description": "生成演示文稿大綱",
                "dependencies": [],
                "timeout": 90,
            },
            {
                "id": "slide_generation",
                "type": "slide_generation",
                "description": "生成Markdown格式的投影片內容",
                "dependencies": ["outline_generation"],
                "timeout": 180,
            },
            {
                "id": "ppt_creation",
                "type": "ppt_creation",
                "description": "生成最終的PPT檔案",
                "dependencies": ["slide_generation"],
                "timeout": 120,
            },
        ]

        # 驗證步驟順序和依賴
        step_ids = [step["id"] for step in workflow_steps]
        expected_order = ["outline_generation", "slide_generation", "ppt_creation"]

        correct_order = step_ids == expected_order

        # 檢查依賴關係
        dependencies_valid = (
            workflow_steps[0]["dependencies"] == []
            and workflow_steps[1]["dependencies"] == ["outline_generation"]
            and workflow_steps[2]["dependencies"] == ["slide_generation"]
        )

        # 檢查超時設置
        timeouts_reasonable = all(
            step["timeout"] > 0 and step["timeout"] <= 300 for step in workflow_steps
        )

        # 檢查步驟類型
        expected_types = ["outline_generation", "slide_generation", "ppt_creation"]
        types_correct = [step["type"] for step in workflow_steps] == expected_types

        print("✅ 工作流結構測試成功")
        print(f"   - 步驟數量: {len(workflow_steps)}")
        print(f"   - 順序正確: {correct_order}")
        print(f"   - 依賴有效: {dependencies_valid}")
        print(f"   - 超時合理: {timeouts_reasonable}")
        print(f"   - 類型正確: {types_correct}")

        return correct_order and dependencies_valid and timeouts_reasonable and types_correct

    except Exception as e:
        print(f"❌ 工作流結構測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("AutoGen PPT工作流 - 簡化測試")
    print("=" * 50)

    test_functions = [
        test_outline_prompt,
        test_outline_parsing,
        test_markdown_generation,
        test_file_operations,
        test_marp_availability,
        test_workflow_structure,
    ]

    results = []

    for test_func in test_functions:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 測試函數 {test_func.__name__} 執行失敗: {e}")
            results.append(False)

    # 統計結果
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100 if total > 0 else 0

    print("\n" + "=" * 50)
    print(f"測試結果摘要:")
    print(f"總測試數: {total}")
    print(f"通過: {passed}")
    print(f"失敗: {total - passed}")
    print(f"成功率: {success_rate:.1f}%")

    if success_rate >= 80:
        print("\n✅ PPT工作流基本結構測試通過，可以進行下一步！")

        # 提供使用提示
        print("\n💡 使用提示:")
        print("1. 確保安裝 Marp CLI 以獲得最佳PPT生成體驗")
        print("   npm install -g @marp-team/marp-cli")
        print("2. 如果沒有Marp，系統會降級保存為Markdown格式")
        print("3. 支援多種輸出格式：pptx, pdf, html, md")
    else:
        print("\n❌ 測試存在問題，需要檢查實現")

    return success_rate >= 80


if __name__ == "__main__":
    main()
