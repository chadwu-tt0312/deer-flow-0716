#!/usr/bin/env python3
"""
User-Agent Hook 範例

這個範例展示如何在 LLM 請求中自動注入 User-Agent header。
"""

import os
import httpx
from unittest.mock import patch

# 清除可能影響的環境變數（必須在最開始就清除）
for var in ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION"]:
    if var in os.environ:
        del os.environ[var]

# 設定環境變數
os.environ["USER_AGENT"] = "Custom Test User Agent v1.0"
os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"


def test_user_agent_hook():
    """測試 User-Agent hook 是否正確運作"""
    from src.llms.llm import _create_llm_use_conf

    # 再次確保清除 Azure 相關環境變數
    for var in ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION"]:
        if var in os.environ:
            del os.environ[var]

    # 模擬配置
    conf = {
        "BASIC_MODEL": {
            "base_url": "https://api.openai.com/v1",
            "api_key": "test_key",
            "model": "gpt-4",
        }
    }

    print("=== User-Agent Hook 測試 ===")
    print(f"環境變數 USER_AGENT: {os.environ.get('USER_AGENT')}")
    print(f"環境變數 HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")

    # 模擬 ChatOpenAI 以避免實際的 API 呼叫
    with patch("src.llms.llm.ChatOpenAI") as mock_chat_openai:
        result = _create_llm_use_conf("basic", conf)

        # 檢查是否呼叫了 ChatOpenAI
        mock_chat_openai.assert_called_once()

        # 檢查傳入的參數
        call_args = mock_chat_openai.call_args[1]

        print(f"\n建立的 LLM 類型: {type(result).__name__}")
        print(f"是否包含 http_client: {'http_client' in call_args}")
        print(f"是否包含 http_async_client: {'http_async_client' in call_args}")

        if "http_client" in call_args:
            http_client = call_args["http_client"]
            print(f"HTTP 客戶端類型: {type(http_client).__name__}")

            # 檢查是否有 event_hooks
            if hasattr(http_client, "_event_hooks"):
                print(f"Event hooks: {http_client._event_hooks}")
                if "request" in http_client._event_hooks:
                    print(f"Request hooks 數量: {len(http_client._event_hooks['request'])}")
                    for hook in http_client._event_hooks["request"]:
                        print(f"  - Hook: {hook.__name__}")
            else:
                print("HTTP 客戶端沒有 event_hooks")

        if "http_async_client" in call_args:
            http_async_client = call_args["http_async_client"]
            print(f"HTTP 異步客戶端類型: {type(http_async_client).__name__}")

            # 檢查是否有 event_hooks
            if hasattr(http_async_client, "_event_hooks"):
                print(f"Event hooks: {http_async_client._event_hooks}")
                if "request" in http_async_client._event_hooks:
                    print(f"Request hooks 數量: {len(http_async_client._event_hooks['request'])}")
                    for hook in http_async_client._event_hooks["request"]:
                        print(f"  - Hook: {hook.__name__}")
            else:
                print("HTTP 異步客戶端沒有 event_hooks")


def test_actual_request_with_hook():
    """測試實際的 HTTP 請求中 User-Agent hook 的運作"""
    from src.utils.network_config import network_config

    print("\n=== 實際 HTTP 請求測試 ===")

    # 建立一個帶有 User-Agent hook 的 httpx 客戶端
    def user_agent_hook(request):
        """Hook to inject User-Agent header into all requests."""
        ua = network_config._get_headers().get("User-Agent")
        if ua:
            request.headers["User-Agent"] = ua
            print(f"注入 User-Agent: {ua}")

    # 建立客戶端
    client = httpx.Client(event_hooks={"request": [user_agent_hook]})

    try:
        # 發送一個測試請求（使用 httpbin.org 來檢查 headers）
        print("發送測試請求到 httpbin.org...")
        response = client.get("https://httpbin.org/headers")

        if response.status_code == 200:
            data = response.json()
            headers = data.get("headers", {})
            user_agent = headers.get("User-Agent", "未找到")
            print(f"伺服器收到的 User-Agent: {user_agent}")

            # 檢查是否與我們設定的相符
            expected_ua = os.environ.get("USER_AGENT")
            if user_agent == expected_ua:
                print("✅ User-Agent 正確注入！")
            else:
                print(f"❌ User-Agent 不匹配。期望: {expected_ua}, 實際: {user_agent}")
        else:
            print(f"請求失敗，狀態碼: {response.status_code}")

    except Exception as e:
        print(f"請求發生錯誤: {e}")

    finally:
        client.close()


if __name__ == "__main__":
    test_user_agent_hook()
    test_actual_request_with_hook()
