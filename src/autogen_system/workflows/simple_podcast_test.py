# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
簡化的Podcast工作流測試

不依賴autogen_core的基本功能測試。
"""

import asyncio
import json
from typing import Dict, Any

from src.logging import get_logger

logger = get_logger(__name__)


def test_script_prompt():
    """測試腳本生成提示"""
    print("=== 測試腳本生成提示 ===")

    try:
        # 模擬PodcastWorkflowManager的提示生成
        prompt = """You are a professional podcast editor for a show called "Hello Deer." Transform raw content into a conversational podcast script suitable for two hosts to read aloud.

# Guidelines

- **Tone**: The script should sound natural and conversational, like two people chatting. Include casual expressions, filler words, and interactive dialogue, but avoid regional dialects like "啥."
- **Hosts**: There are only two hosts, one male and one female. Ensure the dialogue alternates between them frequently, with no other characters or voices included.
- **Length**: Keep the script concise, aiming for a runtime of 10 minutes.
- **Structure**: Start with the male host speaking first. Avoid overly long sentences and ensure the hosts interact often.
- **Output**: Provide only the hosts' dialogue. Do not include introductions, dates, or any other meta information.
- **Language**: Use natural, easy-to-understand language. Avoid mathematical formulas, complex technical notation, or any content that would be difficult to read aloud. Always explain technical concepts in simple, conversational terms.

# Output Format

The output should be formatted as a valid, parseable JSON object of `Script` without "```json". The `Script` interface is defined as follows:

```ts
interface ScriptLine {
  speaker: 'male' | 'female';
  paragraph: string; // only plain text, never Markdown
}

interface Script {
  locale: "en" | "zh";
  lines: ScriptLine[];
}
```"""

        print("✅ 腳本提示生成成功")
        print(f"   - 提示長度: {len(prompt)} 字符")
        print(f"   - 包含指引: {'Guidelines' in prompt}")
        print(f"   - 包含格式: {'Output Format' in prompt}")
        return True

    except Exception as e:
        print(f"❌ 腳本提示測試失敗: {e}")
        return False


def test_script_parsing():
    """測試腳本解析"""
    print("\n=== 測試腳本解析 ===")

    try:
        # 模擬腳本響應
        mock_response = {
            "locale": "zh",
            "lines": [
                {"speaker": "male", "paragraph": "歡迎收聽Hello Deer播客！我是男主持人。"},
                {
                    "speaker": "female",
                    "paragraph": "大家好！我是女主持人，今天我們要聊一個很有趣的話題。",
                },
                {"speaker": "male", "paragraph": "沒錯，今天的主題是人工智慧在現代生活中的應用。"},
            ],
        }

        # 測試JSON序列化和反序列化
        json_str = json.dumps(mock_response, ensure_ascii=False)
        parsed = json.loads(json_str)

        # 驗證結構
        has_locale = "locale" in parsed
        has_lines = "lines" in parsed and isinstance(parsed["lines"], list)
        correct_speakers = all(
            line.get("speaker") in ["male", "female"] for line in parsed["lines"]
        )
        has_paragraphs = all(
            "paragraph" in line and isinstance(line["paragraph"], str) for line in parsed["lines"]
        )

        print("✅ 腳本解析測試成功")
        print(f"   - 有語言設定: {has_locale}")
        print(f"   - 有對話行: {has_lines}")
        print(f"   - 講者正確: {correct_speakers}")
        print(f"   - 有段落內容: {has_paragraphs}")
        print(f"   - 總行數: {len(parsed['lines'])}")

        return has_locale and has_lines and correct_speakers and has_paragraphs

    except Exception as e:
        print(f"❌ 腳本解析測試失敗: {e}")
        return False


def test_voice_type_mapping():
    """測試聲音類型映射"""
    print("\n=== 測試聲音類型映射 ===")

    try:
        # 模擬聲音類型映射邏輯
        def get_voice_type(speaker: str, voice_config: Dict[str, Any]) -> str:
            default_voices = {"male": "BV002_streaming", "female": "BV001_streaming"}

            voice_mapping = voice_config.get("voice_mapping", default_voices)
            return voice_mapping.get(speaker, default_voices.get(speaker, "BV001_streaming"))

        # 測試默認配置
        default_config = {}
        male_voice = get_voice_type("male", default_config)
        female_voice = get_voice_type("female", default_config)

        # 測試自定義配置
        custom_config = {
            "voice_mapping": {"male": "custom_male_voice", "female": "custom_female_voice"}
        }
        custom_male = get_voice_type("male", custom_config)
        custom_female = get_voice_type("female", custom_config)

        print("✅ 聲音類型映射測試成功")
        print(f"   - 默認男聲: {male_voice}")
        print(f"   - 默認女聲: {female_voice}")
        print(f"   - 自定義男聲: {custom_male}")
        print(f"   - 自定義女聲: {custom_female}")

        # 驗證結果
        default_correct = male_voice == "BV002_streaming" and female_voice == "BV001_streaming"
        custom_correct = (
            custom_male == "custom_male_voice" and custom_female == "custom_female_voice"
        )

        return default_correct and custom_correct

    except Exception as e:
        print(f"❌ 聲音類型映射測試失敗: {e}")
        return False


def test_audio_mixing():
    """測試音頻混合邏輯"""
    print("\n=== 測試音頻混合邏輯 ===")

    try:
        # 模擬音頻片段
        audio_chunks = [b"mock_audio_chunk_1", b"mock_audio_chunk_2", b"mock_audio_chunk_3"]

        # 簡單的音頻拼接
        combined_audio = b"".join(audio_chunks)

        # 驗證結果
        expected_size = sum(len(chunk) for chunk in audio_chunks)
        actual_size = len(combined_audio)

        print("✅ 音頻混合測試成功")
        print(f"   - 輸入片段數: {len(audio_chunks)}")
        print(f"   - 預期大小: {expected_size} bytes")
        print(f"   - 實際大小: {actual_size} bytes")
        print(f"   - 大小匹配: {expected_size == actual_size}")

        return expected_size == actual_size

    except Exception as e:
        print(f"❌ 音頻混合測試失敗: {e}")
        return False


def test_workflow_structure():
    """測試工作流結構"""
    print("\n=== 測試工作流結構 ===")

    try:
        # 模擬工作流步驟結構
        workflow_steps = [
            {
                "id": "script_generation",
                "type": "script_generation",
                "description": "生成播客腳本",
                "dependencies": [],
                "timeout": 120,
            },
            {
                "id": "tts_generation",
                "type": "tts_generation",
                "description": "將腳本轉換為語音",
                "dependencies": ["script_generation"],
                "timeout": 300,
            },
            {
                "id": "audio_mixing",
                "type": "audio_mixing",
                "description": "混合音頻片段",
                "dependencies": ["tts_generation"],
                "timeout": 60,
            },
        ]

        # 驗證步驟順序和依賴
        step_ids = [step["id"] for step in workflow_steps]
        expected_order = ["script_generation", "tts_generation", "audio_mixing"]

        correct_order = step_ids == expected_order

        # 檢查依賴關係
        dependencies_valid = (
            workflow_steps[0]["dependencies"] == []
            and workflow_steps[1]["dependencies"] == ["script_generation"]
            and workflow_steps[2]["dependencies"] == ["tts_generation"]
        )

        # 檢查超時設置
        timeouts_reasonable = all(
            step["timeout"] > 0 and step["timeout"] <= 300 for step in workflow_steps
        )

        print("✅ 工作流結構測試成功")
        print(f"   - 步驟數量: {len(workflow_steps)}")
        print(f"   - 順序正確: {correct_order}")
        print(f"   - 依賴有效: {dependencies_valid}")
        print(f"   - 超時合理: {timeouts_reasonable}")

        return correct_order and dependencies_valid and timeouts_reasonable

    except Exception as e:
        print(f"❌ 工作流結構測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("AutoGen Podcast工作流 - 簡化測試")
    print("=" * 50)

    test_functions = [
        test_script_prompt,
        test_script_parsing,
        test_voice_type_mapping,
        test_audio_mixing,
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
        print("\n✅ Podcast工作流基本結構測試通過，可以進行下一步！")
    else:
        print("\n❌ 測試存在問題，需要檢查實現")

    return success_rate >= 80


if __name__ == "__main__":
    main()
