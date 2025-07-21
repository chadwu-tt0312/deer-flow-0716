# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
網路配置使用範例

此範例展示如何在特定網路限制環境中使用網路配置功能，
包括代理伺服器和自訂 User-Agent 的設定。
"""

import os
import requests
from src.utils.network_config import network_config


def example_basic_usage():
    """基本使用範例"""
    print("=== 基本使用範例 ===")

    # 設定環境變數（實際使用時應該在 .env 檔案中設定）
    os.environ["HTTP_PROXY"] = "http://DOMAIN%5Cuser:pwd@proxy.ccc.com:8080"
    os.environ["HTTPS_PROXY"] = "http://DOMAIN%5Cuser:pwd@proxy.ccc.com:8080"
    os.environ["USER_AGENT"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/135.0.3179.54"
    )

    # 測試 HTTPS URL
    url = "https://api.example.com/test"
    config = network_config.get_request_config(url)

    print(f"URL: {url}")
    print(f"網路配置: {config}")
    print()


def example_azure_openai_endpoint():
    """Azure OpenAI 端點範例"""
    print("=== Azure OpenAI 端點範例 ===")

    # 設定 Azure OpenAI 端點
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://my-resource.openai.azure.com/"
    os.environ["HTTP_PROXY"] = "http://proxy.example.com:8080"
    os.environ["USER_AGENT"] = "Custom Azure UA"

    # 測試 Azure OpenAI URL
    url = "https://my-resource.openai.azure.com/openai/deployments/gpt-4/chat/completions"
    config = network_config.get_request_config(url)

    print(f"Azure OpenAI URL: {url}")
    print(f"網路配置: {config}")
    print()


def example_basic_model_url():
    """基本模型 URL 範例"""
    print("=== 基本模型 URL 範例 ===")

    # 設定基本模型 URL
    os.environ["BASIC_MODEL__BASE_URL"] = "https://my-model-endpoint.com"
    os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
    os.environ["USER_AGENT"] = "Custom Model UA"

    # 測試基本模型 URL
    url = "https://my-model-endpoint.com/v1/chat/completions"
    config = network_config.get_request_config(url)

    print(f"基本模型 URL: {url}")
    print(f"網路配置: {config}")
    print()


def example_http_url():
    """HTTP URL 範例（不需要代理和 headers）"""
    print("=== HTTP URL 範例 ===")

    # 設定代理和 User-Agent
    os.environ["HTTP_PROXY"] = "http://proxy.example.com:8080"
    os.environ["USER_AGENT"] = "Custom UA"

    # 測試 HTTP URL
    url = "http://api.example.com/test"
    config = network_config.get_request_config(url)

    print(f"HTTP URL: {url}")
    print(f"網路配置: {config}")
    print()


def example_headers_update():
    """Headers 更新範例"""
    print("=== Headers 更新範例 ===")

    os.environ["USER_AGENT"] = "Custom User Agent"

    # 現有的 headers
    existing_headers = {"Authorization": "Bearer token123", "Content-Type": "application/json"}

    # 更新 headers
    updated_headers = network_config.update_headers(existing_headers)

    print(f"原始 headers: {existing_headers}")
    print(f"更新後 headers: {updated_headers}")
    print()


def example_proxy_only():
    """僅代理設定範例"""
    print("=== 僅代理設定範例 ===")

    os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"

    url = "https://api.example.com/test"
    proxies = network_config.get_proxies_for_url(url)

    print(f"URL: {url}")
    print(f"代理設定: {proxies}")
    print()


def example_requests_integration():
    """與 requests 整合範例"""
    print("=== 與 requests 整合範例 ===")

    # 設定環境變數
    os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
    os.environ["USER_AGENT"] = "Custom Integration UA"

    url = "https://httpbin.org/get"

    try:
        # 取得網路配置
        request_config = network_config.get_request_config(url)

        print(f"請求 URL: {url}")
        print(f"網路配置: {request_config}")

        # 執行請求
        response = requests.get(url, **request_config)

        print(f"回應狀態碼: {response.status_code}")
        print(f"回應內容: {response.json()}")

    except Exception as e:
        print(f"請求失敗: {e}")

    print()


def example_conditional_usage():
    """條件式使用範例"""
    print("=== 條件式使用範例 ===")

    # 檢查是否需要使用代理和 headers
    urls = [
        "https://api.example.com/test",
        "http://api.example.com/test",
        "https://my-resource.openai.azure.com/openai/deployments/gpt-4",
    ]

    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://my-resource.openai.azure.com/"
    os.environ["HTTPS_PROXY"] = "http://proxy.example.com:8080"
    os.environ["USER_AGENT"] = "Conditional UA"

    for url in urls:
        needs_config = network_config._should_use_proxy_and_headers(url)
        config = network_config.get_request_config(url)

        print(f"URL: {url}")
        print(f"需要網路配置: {needs_config}")
        print(f"配置: {config}")
        print()


def main():
    """主函數"""
    print("網路配置使用範例")
    print("=" * 50)
    print()

    # 執行各種範例
    example_basic_usage()
    example_azure_openai_endpoint()
    example_basic_model_url()
    example_http_url()
    example_headers_update()
    example_proxy_only()
    example_requests_integration()
    example_conditional_usage()

    print("範例執行完成！")
    print()
    print("注意事項:")
    print("1. 實際使用時請在 .env 檔案中設定環境變數")
    print("2. 代理伺服器 URL 中的特殊字元需要進行 URL 編碼")
    print("3. 網路配置會自動快取以提高效能")
    print("4. 只有 HTTPS URL 或特定的端點才會套用網路配置")


if __name__ == "__main__":
    main()
