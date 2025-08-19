# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
工具集成測試

測試各種工具的適配和集成功能。
"""

import asyncio
import json
from typing import Dict, Any, List

from .tool_factory import global_tool_factory, initialize_tools
from .adapters import global_tool_registry
from src.logging import get_logger

logger = get_logger(__name__)


async def test_search_tools():
    """測試搜尋工具"""
    logger.info("🔍 測試搜尋工具")

    try:
        # 獲取搜尋工具
        search_tools = global_tool_registry.get_tools_by_category("search")

        if not search_tools:
            logger.warning("未找到搜尋工具")
            return False

        # 測試第一個搜尋工具
        search_tool = search_tools[0]
        test_query = "人工智慧發展趨勢"

        logger.info(f"使用工具 {search_tool.__name__} 測試查詢: {test_query}")
        result = await search_tool(query=test_query, max_results=3)

        logger.info(f"搜尋結果類型: {type(result)}")
        logger.info(f"搜尋結果長度: {len(str(result))}")

        return True

    except Exception as e:
        logger.error(f"搜尋工具測試失敗: {e}")
        return False


async def test_code_execution_tools():
    """測試程式碼執行工具"""
    logger.info("💻 測試程式碼執行工具")

    try:
        # 獲取程式碼執行工具
        code_tools = global_tool_registry.get_tools_by_category("code")

        if not code_tools:
            logger.warning("未找到程式碼執行工具")
            return False

        # 測試第一個程式碼執行工具
        code_tool = code_tools[0]
        test_code = "print('Hello, AutoGen!')\nresult = 2 + 2\nprint(f'2 + 2 = {result}')"

        logger.info(f"使用工具 {code_tool.__name__} 測試程式碼執行")
        result = await code_tool(code=test_code)

        logger.info(f"程式碼執行結果類型: {type(result)}")
        logger.info(f"程式碼執行結果: {result[:200]}...")

        return True

    except Exception as e:
        logger.error(f"程式碼執行工具測試失敗: {e}")
        return False


async def test_crawl_tools():
    """測試爬蟲工具"""
    logger.info("🕷️ 測試爬蟲工具")

    try:
        # 獲取爬蟲工具
        crawl_tools = global_tool_registry.get_tools_by_category("crawl")

        if not crawl_tools:
            logger.warning("未找到爬蟲工具")
            return False

        # 測試第一個爬蟲工具
        crawl_tool = crawl_tools[0]
        test_url = "https://httpbin.org/html"  # 測試用的簡單 HTML 頁面

        logger.info(f"使用工具 {crawl_tool.__name__} 測試 URL 爬取: {test_url}")
        result = await crawl_tool(url=test_url)

        logger.info(f"爬蟲結果類型: {type(result)}")
        logger.info(f"爬蟲結果長度: {len(str(result))}")

        return True

    except Exception as e:
        logger.error(f"爬蟲工具測試失敗: {e}")
        return False


async def test_tool_registry():
    """測試工具註冊中心"""
    logger.info("📋 測試工具註冊中心")

    try:
        # 獲取註冊統計
        stats = global_tool_registry.get_registry_stats()
        logger.info(f"註冊統計: {json.dumps(stats, indent=2, ensure_ascii=False)}")

        # 列出所有工具
        all_tools = global_tool_registry.list_tools()
        logger.info(f"註冊的工具 ({len(all_tools)} 個): {all_tools}")

        # 列出工具類別
        categories = global_tool_registry.list_categories()
        logger.info(f"工具類別: {categories}")

        # 獲取每個類別的工具數量
        for category in categories:
            tools_in_category = global_tool_registry.get_tools_by_category(category)
            logger.info(f"類別 '{category}': {len(tools_in_category)} 個工具")

        return True

    except Exception as e:
        logger.error(f"工具註冊中心測試失敗: {e}")
        return False


async def test_tool_factory():
    """測試工具工廠"""
    logger.info("🏭 測試工具工廠")

    try:
        # 測試工具工廠統計
        factory_stats = global_tool_factory.get_tool_registry_stats()
        logger.info(f"工廠統計: {json.dumps(factory_stats, indent=2, ensure_ascii=False)}")

        # 測試智能體工具獲取
        agent_types = ["researcher", "coder", "coordinator", "all"]

        for agent_type in agent_types:
            tools = global_tool_factory.get_tools_for_agent(agent_type)
            logger.info(f"智能體 '{agent_type}' 可用工具: {len(tools)} 個")

        # 導出工具定義
        tool_definitions = global_tool_factory.export_tool_definitions()
        logger.info(f"工具定義導出: {len(tool_definitions.get('tools', {}))} 個工具")

        return True

    except Exception as e:
        logger.error(f"工具工廠測試失敗: {e}")
        return False


async def test_all_tool_integrations():
    """執行所有工具集成測試"""
    logger.info("🚀 開始工具集成測試")

    # 初始化工具
    logger.info("初始化工具...")
    await initialize_tools()

    # 執行各項測試
    test_results = {}

    test_cases = [
        ("工具註冊中心", test_tool_registry),
        ("工具工廠", test_tool_factory),
        ("搜尋工具", test_search_tools),
        ("程式碼執行工具", test_code_execution_tools),
        ("爬蟲工具", test_crawl_tools),
    ]

    for test_name, test_func in test_cases:
        logger.info(f"\n{'=' * 50}")
        logger.info(f"執行測試: {test_name}")
        logger.info(f"{'=' * 50}")

        try:
            result = await test_func()
            test_results[test_name] = result
            status = "✅ 通過" if result else "❌ 失敗"
            logger.info(f"測試 '{test_name}': {status}")
        except Exception as e:
            test_results[test_name] = False
            logger.error(f"測試 '{test_name}' 異常: {e}")

    # 輸出測試總結
    logger.info(f"\n{'=' * 50}")
    logger.info("🏁 工具集成測試總結")
    logger.info(f"{'=' * 50}")

    passed_tests = sum(test_results.values())
    total_tests = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info(f"  {test_name}: {status}")

    logger.info(f"\n總計: {passed_tests}/{total_tests} 個測試通過")

    if passed_tests == total_tests:
        logger.info("🎉 所有工具集成測試通過！")
        return True
    else:
        logger.warning(f"⚠️ 有 {total_tests - passed_tests} 個測試失敗")
        return False


if __name__ == "__main__":
    asyncio.run(test_all_tool_integrations())
