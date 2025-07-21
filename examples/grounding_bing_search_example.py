#!/usr/bin/env python
# coding: utf-8
"""
Grounding Bing Search 使用範例

這個範例展示如何使用 DeerFlow 的 Grounding Bing Search 功能。
"""

import os
from src.tools.grounding_bing_search import GroundingBingSearchTool
from src.tools.grounding_bing_search.grounding_bing_search_api_wrapper import (
    GroundingBingSearchAPIWrapper,
    GroundingBingSearchConfig,
)


def example_direct_api_usage():
    """直接使用 API 包裝器的範例"""
    print("=== 直接使用 API 包裝器範例 ===")

    # 設定配置
    config = GroundingBingSearchConfig(
        client_id=os.getenv("GROUNDING_BING_CLIENT_ID", ""),
        client_secret=os.getenv("GROUNDING_BING_CLIENT_SECRET", ""),
        tenant_id=os.getenv("GROUNDING_BING_TENANT_ID", ""),
        connection_id=os.getenv("GROUNDING_BING_CONNECTION_ID", ""),
        count=5,
        market="zh-tw",
        set_lang="zh-hant",
    )

    # 建立 API 包裝器
    wrapper = GroundingBingSearchAPIWrapper(config)

    try:
        # 執行搜尋
        results = wrapper.search("最新的人工智慧發展")
        print(f"查詢: {results['query']}")
        print(f"結果數量: {len(results['results'])}")

        for i, result in enumerate(results["results"], 1):
            print(f"\n結果 {i}:")
            print(f"類型: {result['type']}")
            print(f"內容: {result['content'][:200]}...")  # 只顯示前 200 字元

    except Exception as e:
        print(f"搜尋失敗: {e}")


def example_tool_usage():
    """使用 LangChain 工具的範例"""
    print("\n=== 使用 LangChain 工具範例 ===")

    # 建立工具
    tool = GroundingBingSearchTool(max_results=3, market="zh-tw", set_lang="zh-hant")

    try:
        # 執行搜尋
        results = tool.invoke("台灣的科技發展現況")
        print(f"查詢: 台灣的科技發展現況")
        print(f"結果數量: {len(results)}")

        for i, result in enumerate(results, 1):
            print(f"\n結果 {i}:")
            print(f"標題: {result['title']}")
            print(f"內容: {result['content'][:200]}...")  # 只顯示前 200 字元
            print(f"來源: {result['source']}")

    except Exception as e:
        print(f"搜尋失敗: {e}")


def example_with_error_handling():
    """包含錯誤處理的範例"""
    print("\n=== 錯誤處理範例 ===")

    # 測試無效配置
    config = GroundingBingSearchConfig(
        client_id="invalid_id",
        client_secret="invalid_secret",
        tenant_id="invalid_tenant",
        connection_id="invalid_connection",
    )

    wrapper = GroundingBingSearchAPIWrapper(config)

    try:
        results = wrapper.search("測試查詢")
        print("搜尋成功")
    except Exception as e:
        print(f"預期的錯誤: {e}")


if __name__ == "__main__":
    # 檢查環境變數
    required_vars = [
        "GROUNDING_BING_CLIENT_ID",
        "GROUNDING_BING_CLIENT_SECRET",
        "GROUNDING_BING_TENANT_ID",
        "GROUNDING_BING_CONNECTION_ID",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print("警告: 以下環境變數未設定:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\n請設定這些變數後再執行範例。")
        print("範例將使用預設值進行演示。")

    # 執行範例
    example_direct_api_usage()
    example_tool_usage()
    example_with_error_handling()

    print("\n=== 範例完成 ===")
