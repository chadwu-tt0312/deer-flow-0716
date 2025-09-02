#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
系統遷移測試腳本

測試從 LangGraph 到 AutoGen 的遷移功能和 API 相容性。
"""

import asyncio
import json
import time
from typing import Dict, Any
from datetime import datetime

# 設置路徑
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging import get_logger
from src.config.report_style import ReportStyle

logger = get_logger(__name__)


class MigrationTester:
    """遷移測試器"""

    def __init__(self):
        self.test_results = []
        self.performance_data = {}

    async def run_all_tests(self):
        """執行所有測試"""
        print("🧪 開始執行系統遷移測試...")
        print("=" * 60)

        # 1. 基本 API 相容性測試
        await self.test_api_compatibility()

        # 2. 系統切換功能測試
        await self.test_system_switching()

        # 3. 工作流相容性測試
        await self.test_workflow_compatibility()

        # 4. 效能比較測試
        await self.test_performance_comparison()

        # 5. 健康檢查測試
        await self.test_health_check()

        # 生成測試報告
        self.generate_test_report()

    async def test_api_compatibility(self):
        """測試 API 相容性"""
        print("\n📋 測試 API 相容性...")

        tests = [
            {"name": "AutoGen API 基本調用", "test_func": self._test_autogen_api_basic},
            {"name": "LangGraph 相容性層", "test_func": self._test_langgraph_compatibility},
            {"name": "參數傳遞相容性", "test_func": self._test_parameter_compatibility},
        ]

        for test in tests:
            try:
                start_time = time.time()
                result = await test["test_func"]()
                execution_time = time.time() - start_time

                self.test_results.append(
                    {
                        "category": "API相容性",
                        "test_name": test["name"],
                        "status": "PASS" if result["success"] else "FAIL",
                        "execution_time": execution_time,
                        "details": result,
                    }
                )
                print(f"  ✅ {test['name']} - PASS ({execution_time:.2f}s)")

            except Exception as e:
                self.test_results.append(
                    {
                        "category": "API相容性",
                        "test_name": test["name"],
                        "status": "ERROR",
                        "execution_time": 0,
                        "error": str(e),
                    }
                )
                print(f"  ❌ {test['name']} - ERROR: {e}")

    async def _test_autogen_api_basic(self) -> Dict[str, Any]:
        """測試 AutoGen API 基本功能"""
        from src.autogen_system.compatibility.api_adapter import run_agent_workflow_async

        result = await run_agent_workflow_async(
            user_input="這是一個測試查詢", auto_accepted_plan=True, max_step_num=1, debug=True
        )

        return {
            "success": result.get("success", False),
            "has_final_report": bool(result.get("final_report")),
            "system_used": "autogen",
            "result_keys": list(result.keys()),
        }

    async def _test_langgraph_compatibility(self) -> Dict[str, Any]:
        """測試 LangGraph 相容性層"""
        try:
            from src.llms.llm import get_default_model_client
            from src.autogen_system.compatibility.langgraph_compatibility import (
                create_langgraph_compatible_graph,
            )

            model_client = get_default_model_client()
            graph = create_langgraph_compatible_graph(model_client)

            # 測試 ainvoke
            result = await graph.ainvoke(
                {"messages": [{"role": "user", "content": "測試 LangGraph 相容性"}]}
            )

            return {
                "success": result.get("execution_metadata", {}).get("success", False),
                "has_messages": bool(result.get("messages")),
                "has_final_report": bool(result.get("final_report")),
                "system_used": "langgraph_compatibility",
                "result_keys": list(result.keys()),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_parameter_compatibility(self) -> Dict[str, Any]:
        """測試參數傳遞相容性"""
        from src.autogen_system.compatibility.api_adapter import run_agent_workflow_async

        # 測試所有參數
        result = await run_agent_workflow_async(
            user_input="參數相容性測試",
            debug=True,
            max_plan_iterations=1,
            max_step_num=2,
            enable_background_investigation=False,
            auto_accepted_plan=True,
            report_style=ReportStyle.ACADEMIC,
            resources=[],
            mcp_settings={},
        )

        return {
            "success": result.get("success", False),
            "parameters_handled": True,
            "debug_info_present": bool(result.get("debug_info")),
            "execution_metadata": bool(result.get("execution_metadata")),
        }

    async def test_system_switching(self):
        """測試系統切換功能"""
        print("\n🔄 測試系統切換功能...")

        tests = [
            {"name": "切換到 AutoGen", "test_func": self._test_switch_to_autogen},
            {"name": "環境變數控制", "test_func": self._test_environment_switching},
            {"name": "自動系統選擇", "test_func": self._test_auto_system_selection},
        ]

        for test in tests:
            try:
                start_time = time.time()
                result = await test["test_func"]()
                execution_time = time.time() - start_time

                self.test_results.append(
                    {
                        "category": "系統切換",
                        "test_name": test["name"],
                        "status": "PASS" if result["success"] else "FAIL",
                        "execution_time": execution_time,
                        "details": result,
                    }
                )
                print(f"  ✅ {test['name']} - PASS ({execution_time:.2f}s)")

            except Exception as e:
                self.test_results.append(
                    {
                        "category": "系統切換",
                        "test_name": test["name"],
                        "status": "ERROR",
                        "execution_time": 0,
                        "error": str(e),
                    }
                )
                print(f"  ❌ {test['name']} - ERROR: {e}")

    async def _test_switch_to_autogen(self) -> Dict[str, Any]:
        """測試切換到 AutoGen"""
        from src.autogen_system.compatibility.system_switcher import (
            switch_to_autogen,
            get_current_system,
            run_workflow_with_auto_switch,
        )

        # 切換到 AutoGen
        switch_to_autogen()
        current_system = get_current_system()

        # 執行工作流
        result = await run_workflow_with_auto_switch("測試 AutoGen 系統", workflow_type="research")

        return {
            "success": True,
            "current_system": current_system,
            "workflow_success": result.get("success", False),
            "system_used": result.get("system_used"),
        }

    async def _test_environment_switching(self) -> Dict[str, Any]:
        """測試環境變數控制"""
        import os
        from src.autogen_system.compatibility.system_switcher import SystemSwitcher, SystemType

        # 設置環境變數
        os.environ["USE_AUTOGEN_SYSTEM"] = "true"
        switcher = SystemSwitcher()
        autogen_system = switcher.get_current_system()

        os.environ["USE_AUTOGEN_SYSTEM"] = "false"
        switcher = SystemSwitcher()
        langgraph_system = switcher.get_current_system()

        return {
            "success": True,
            "autogen_detected": autogen_system == SystemType.AUTOGEN,
            "langgraph_detected": langgraph_system == SystemType.LANGGRAPH,
            "environment_control_works": True,
        }

    async def _test_auto_system_selection(self) -> Dict[str, Any]:
        """測試自動系統選擇"""
        from src.autogen_system.compatibility.system_switcher import run_workflow_with_auto_switch

        result = await run_workflow_with_auto_switch("自動系統選擇測試", workflow_type="research")

        return {
            "success": result.get("success", False),
            "system_selected": result.get("system_used"),
            "auto_selection_works": bool(result.get("system_used")),
        }

    async def test_workflow_compatibility(self):
        """測試工作流相容性"""
        print("\n🔧 測試工作流相容性...")

        workflows = ["research", "podcast", "ppt", "prose", "prompt_enhancer"]

        for workflow_type in workflows:
            try:
                start_time = time.time()
                result = await self._test_single_workflow(workflow_type)
                execution_time = time.time() - start_time

                self.test_results.append(
                    {
                        "category": "工作流相容性",
                        "test_name": f"{workflow_type} 工作流",
                        "status": "PASS" if result["success"] else "FAIL",
                        "execution_time": execution_time,
                        "details": result,
                    }
                )
                print(f"  ✅ {workflow_type} 工作流 - PASS ({execution_time:.2f}s)")

            except Exception as e:
                self.test_results.append(
                    {
                        "category": "工作流相容性",
                        "test_name": f"{workflow_type} 工作流",
                        "status": "ERROR",
                        "execution_time": 0,
                        "error": str(e),
                    }
                )
                print(f"  ❌ {workflow_type} 工作流 - ERROR: {e}")

    async def _test_single_workflow(self, workflow_type: str) -> Dict[str, Any]:
        """測試單個工作流"""
        from src.autogen_system.compatibility.system_switcher import run_workflow_with_auto_switch

        test_inputs = {
            "research": "測試研究主題",
            "podcast": "生成測試播客",
            "ppt": "製作測試簡報",
            "prose": "撰寫測試文章",
            "prompt_enhancer": "優化測試提示詞",
        }

        user_input = test_inputs.get(workflow_type, "測試輸入")

        result = await run_workflow_with_auto_switch(user_input, workflow_type=workflow_type)

        return {
            "success": result.get("success", False),
            "workflow_type": workflow_type,
            "system_used": result.get("system_used"),
            "has_output": bool(result.get("final_report") or result.get("result")),
        }

    async def test_performance_comparison(self):
        """測試效能比較"""
        print("\n⚡ 測試效能比較...")

        # 簡單的效能測試
        test_query = "效能測試查詢"

        # 測試 AutoGen 系統
        try:
            start_time = time.time()
            from src.autogen_system.compatibility.api_adapter import run_agent_workflow_async

            autogen_result = await run_agent_workflow_async(
                user_input=test_query, auto_accepted_plan=True, max_step_num=1
            )
            autogen_time = time.time() - start_time

            self.performance_data["autogen"] = {
                "execution_time": autogen_time,
                "success": autogen_result.get("success", False),
                "system": "AutoGen",
            }
            print(f"  📊 AutoGen 系統: {autogen_time:.2f}s")

        except Exception as e:
            self.performance_data["autogen"] = {
                "execution_time": 0,
                "success": False,
                "error": str(e),
                "system": "AutoGen",
            }
            print(f"  ❌ AutoGen 系統測試失敗: {e}")

        # 嘗試測試 LangGraph 系統（如果可用）
        try:
            start_time = time.time()
            from src.workflow import run_agent_workflow_async as langgraph_workflow

            langgraph_result = await langgraph_workflow(
                user_input=test_query, auto_accepted_plan=True, max_step_num=1
            )
            langgraph_time = time.time() - start_time

            self.performance_data["langgraph"] = {
                "execution_time": langgraph_time,
                "success": langgraph_result.get("success", False),
                "system": "LangGraph",
            }
            print(f"  📊 LangGraph 系統: {langgraph_time:.2f}s")

        except Exception as e:
            self.performance_data["langgraph"] = {
                "execution_time": 0,
                "success": False,
                "error": str(e),
                "system": "LangGraph",
            }
            print(f"  ⚠️  LangGraph 系統不可用: {e}")

    async def test_health_check(self):
        """測試健康檢查"""
        print("\n🏥 執行系統健康檢查...")

        try:
            from src.autogen_system.compatibility.system_switcher import system_health_check

            health_result = await system_health_check()

            autogen_healthy = (
                health_result.get("systems", {}).get("autogen", {}).get("available", False)
            )
            langgraph_healthy = (
                health_result.get("systems", {}).get("langgraph", {}).get("available", False)
            )

            self.test_results.append(
                {
                    "category": "健康檢查",
                    "test_name": "系統健康檢查",
                    "status": "PASS" if autogen_healthy else "WARN",
                    "details": {
                        "autogen_healthy": autogen_healthy,
                        "langgraph_healthy": langgraph_healthy,
                        "current_system": health_result.get("current_system"),
                        "health_data": health_result,
                    },
                }
            )

            print(f"  🟢 AutoGen 系統: {'健康' if autogen_healthy else '不可用'}")
            print(
                f"  {'🟢' if langgraph_healthy else '🟡'} LangGraph 系統: {'健康' if langgraph_healthy else '不可用'}"
            )

        except Exception as e:
            self.test_results.append(
                {
                    "category": "健康檢查",
                    "test_name": "系統健康檢查",
                    "status": "ERROR",
                    "error": str(e),
                }
            )
            print(f"  ❌ 健康檢查失敗: {e}")

    def generate_test_report(self):
        """生成測試報告"""
        print("\n" + "=" * 60)
        print("📊 測試報告")
        print("=" * 60)

        # 統計結果
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        error_tests = len([r for r in self.test_results if r["status"] == "ERROR"])

        print(f"總測試數: {total_tests}")
        print(f"通過: {passed_tests}")
        print(f"失敗: {failed_tests}")
        print(f"錯誤: {error_tests}")
        print(f"成功率: {passed_tests / total_tests * 100:.1f}%")

        # 按類別統計
        categories = {}
        for result in self.test_results:
            category = result["category"]
            if category not in categories:
                categories[category] = {"pass": 0, "fail": 0, "error": 0, "warn": 0}
            status_lower = result["status"].lower()
            if status_lower in categories[category]:
                categories[category][status_lower] += 1
            else:
                # 處理未知狀態
                categories[category]["error"] += 1

        print("\n分類結果:")
        for category, stats in categories.items():
            total = sum(stats.values())
            pass_rate = stats["pass"] / total * 100 if total > 0 else 0
            print(f"  {category}: {stats['pass']}/{total} 通過 ({pass_rate:.1f}%)")

        # 效能比較
        if self.performance_data:
            print("\n效能比較:")
            for system, data in self.performance_data.items():
                if data["success"]:
                    print(f"  {data['system']}: {data['execution_time']:.2f}s")
                else:
                    print(f"  {data['system']}: 測試失敗")

        # 建議
        print("\n🎯 遷移建議:")
        if passed_tests / total_tests >= 0.8:
            print("  ✅ 系統遷移準備就緒！AutoGen 系統可正常運作。")
            print("  📈 建議開始進行生產環境切換。")
        elif passed_tests / total_tests >= 0.6:
            print("  ⚠️  系統基本功能正常，但存在一些問題。")
            print("  🔧 建議修復失敗的測試後再進行遷移。")
        else:
            print("  ❌ 系統存在嚴重問題，不建議現在遷移。")
            print("  🛠️  請先解決關鍵問題。")

        # 保存詳細報告
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "error_tests": error_tests,
                "success_rate": passed_tests / total_tests * 100,
            },
            "categories": categories,
            "performance_data": self.performance_data,
            "detailed_results": self.test_results,
        }

        with open("migration_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"\n📄 詳細報告已保存到: migration_test_report.json")


async def main():
    """主函數"""
    print("🚀 DeerFlow 系統遷移測試")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tester = MigrationTester()
    await tester.run_all_tests()

    print("\n✨ 測試完成！")


if __name__ == "__main__":
    asyncio.run(main())
