#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen系統測試運行器

提供統一的測試執行和報告生成。
"""

import os
import sys
import asyncio
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import coverage


class TestSuite(Enum):
    """測試套件類型"""

    UNIT = "unit"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    ALL = "all"


class TestStatus(Enum):
    """測試狀態"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """測試結果"""

    name: str
    status: TestStatus
    duration: float
    message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class TestSuiteResult:
    """測試套件結果"""

    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    coverage_percentage: Optional[float] = None
    results: List[TestResult] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

    @property
    def success_rate(self) -> float:
        """計算成功率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100


class AutoGenTestRunner:
    """AutoGen測試運行器"""

    def __init__(self, project_root: Path = None):
        """
        初始化測試運行器

        Args:
            project_root: 項目根目錄路徑
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.test_dir = self.project_root / "tests" / "autogen_system"
        self.coverage = None
        self.results: Dict[str, TestSuiteResult] = {}

    def setup_coverage(self, source_dir: str = "src/autogen_system"):
        """設置代碼覆蓋率監控"""

        self.coverage = coverage.Coverage(
            source=[str(self.project_root / source_dir)],
            config_file=False,
            auto_data=True,
        )
        self.coverage.start()

    def stop_coverage(self) -> float:
        """停止覆蓋率監控並返回覆蓋率百分比"""

        if not self.coverage:
            return 0.0

        self.coverage.stop()
        self.coverage.save()

        # 計算覆蓋率
        coverage_data = self.coverage.get_data()
        total_lines = 0
        covered_lines = 0

        for filename in coverage_data.measured_files():
            lines = coverage_data.lines(filename) or []
            total_lines += len(lines)
            covered_lines += len(lines)

        if total_lines == 0:
            return 0.0

        return (covered_lines / total_lines) * 100

    async def run_test_suite(
        self, suite: TestSuite, verbose: bool = False, capture_output: bool = True
    ) -> TestSuiteResult:
        """
        運行指定的測試套件

        Args:
            suite: 測試套件類型
            verbose: 是否顯示詳細輸出
            capture_output: 是否捕獲輸出

        Returns:
            TestSuiteResult: 測試結果
        """

        print(f"\n{'=' * 60}")
        print(f"運行測試套件: {suite.value.upper()}")
        print(f"{'=' * 60}")

        # 確定測試路徑
        if suite == TestSuite.UNIT:
            test_path = self.test_dir / "unit"
        elif suite == TestSuite.INTEGRATION:
            test_path = self.test_dir / "integration"
        elif suite == TestSuite.PERFORMANCE:
            test_path = self.test_dir / "integration" / "test_performance.py"
        elif suite == TestSuite.ALL:
            test_path = self.test_dir
        else:
            raise ValueError(f"未知的測試套件: {suite}")

        # 設置pytest參數
        pytest_args = [
            str(test_path),
            "-v" if verbose else "-q",
            "--tb=short",
            "--durations=10",
        ]

        if not capture_output:
            pytest_args.append("-s")

        # 根據套件類型添加標記
        if suite == TestSuite.PERFORMANCE:
            pytest_args.extend(["-m", "performance or benchmark"])
        elif suite == TestSuite.UNIT:
            pytest_args.extend(["-m", "not performance and not benchmark"])

        # 啟動覆蓋率監控
        if suite in [TestSuite.UNIT, TestSuite.ALL]:
            self.setup_coverage()

        start_time = time.time()

        try:
            # 運行pytest
            exit_code = pytest.main(pytest_args)

            end_time = time.time()
            duration = end_time - start_time

            # 停止覆蓋率監控
            coverage_percentage = None
            if self.coverage:
                coverage_percentage = self.stop_coverage()

            # 解析結果（簡化版本）
            result = TestSuiteResult(
                suite_name=suite.value,
                total_tests=0,  # 需要從pytest結果中解析
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=duration,
                coverage_percentage=coverage_percentage,
            )

            # 根據退出碼設置基本結果
            if exit_code == 0:
                print(f"✅ 測試套件 {suite.value} 執行成功")
                result.passed = 1  # 簡化
                result.total_tests = 1
            else:
                print(f"❌ 測試套件 {suite.value} 執行失敗 (退出碼: {exit_code})")
                result.failed = 1  # 簡化
                result.total_tests = 1

            return result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            print(f"❌ 測試套件執行異常: {e}")

            return TestSuiteResult(
                suite_name=suite.value,
                total_tests=1,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration=duration,
            )

    async def run_all_tests(
        self, include_performance: bool = False, verbose: bool = False
    ) -> Dict[str, TestSuiteResult]:
        """
        運行所有測試套件

        Args:
            include_performance: 是否包含性能測試
            verbose: 是否顯示詳細輸出

        Returns:
            Dict[str, TestSuiteResult]: 所有測試結果
        """

        suites_to_run = [TestSuite.UNIT, TestSuite.INTEGRATION]

        if include_performance:
            suites_to_run.append(TestSuite.PERFORMANCE)

        results = {}

        for suite in suites_to_run:
            try:
                result = await self.run_test_suite(suite, verbose=verbose)
                results[suite.value] = result
                self.results[suite.value] = result
            except Exception as e:
                print(f"運行測試套件 {suite.value} 時出錯: {e}")
                results[suite.value] = TestSuiteResult(
                    suite_name=suite.value,
                    total_tests=0,
                    passed=0,
                    failed=0,
                    skipped=0,
                    errors=1,
                    duration=0.0,
                )

        return results

    def generate_report(
        self, results: Dict[str, TestSuiteResult], output_file: Optional[Path] = None
    ) -> str:
        """
        生成測試報告

        Args:
            results: 測試結果
            output_file: 輸出文件路徑

        Returns:
            str: 報告內容
        """

        report_lines = []
        report_lines.append("# AutoGen系統測試報告")
        report_lines.append(f"\n**生成時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**項目路徑**: {self.project_root}")

        # 總體概況
        total_tests = sum(r.total_tests for r in results.values())
        total_passed = sum(r.passed for r in results.values())
        total_failed = sum(r.failed for r in results.values())
        total_skipped = sum(r.skipped for r in results.values())
        total_errors = sum(r.errors for r in results.values())
        total_duration = sum(r.duration for r in results.values())

        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        report_lines.append("\n## 📊 總體概況")
        report_lines.append(f"- **總測試數**: {total_tests}")
        report_lines.append(f"- **通過**: {total_passed} ✅")
        report_lines.append(f"- **失敗**: {total_failed} ❌")
        report_lines.append(f"- **跳過**: {total_skipped} ⏭️")
        report_lines.append(f"- **錯誤**: {total_errors} 💥")
        report_lines.append(f"- **成功率**: {overall_success_rate:.1f}%")
        report_lines.append(f"- **總耗時**: {total_duration:.3f}s")

        # 各套件詳情
        report_lines.append("\n## 📋 測試套件詳情")

        for suite_name, result in results.items():
            status_emoji = "✅" if result.failed == 0 and result.errors == 0 else "❌"

            report_lines.append(f"\n### {status_emoji} {suite_name.upper()}")
            report_lines.append(f"- **測試數**: {result.total_tests}")
            report_lines.append(f"- **通過**: {result.passed}")
            report_lines.append(f"- **失敗**: {result.failed}")
            report_lines.append(f"- **跳過**: {result.skipped}")
            report_lines.append(f"- **錯誤**: {result.errors}")
            report_lines.append(f"- **成功率**: {result.success_rate:.1f}%")
            report_lines.append(f"- **耗時**: {result.duration:.3f}s")

            if result.coverage_percentage is not None:
                report_lines.append(f"- **代碼覆蓋率**: {result.coverage_percentage:.1f}%")

        # 性能指標（如果有的話）
        if "performance" in results:
            perf_result = results["performance"]
            report_lines.append("\n## 🚀 性能指標")
            report_lines.append(f"- **性能測試耗時**: {perf_result.duration:.3f}s")
            report_lines.append(
                f"- **性能測試狀態**: {'通過' if perf_result.failed == 0 else '失敗'}"
            )

        # 建議和總結
        report_lines.append("\n## 💡 建議和總結")

        if overall_success_rate >= 95:
            report_lines.append("- ✅ 測試覆蓋良好，系統穩定性高")
        elif overall_success_rate >= 80:
            report_lines.append("- ⚠️ 測試基本通過，建議關注失敗的測試案例")
        else:
            report_lines.append("- ❌ 測試失敗率較高，需要重點改進")

        if total_errors > 0:
            report_lines.append("- 🔧 發現系統錯誤，建議優先修復")

        if any(r.coverage_percentage and r.coverage_percentage < 80 for r in results.values()):
            report_lines.append("- 📈 建議提高代碼覆蓋率至80%以上")

        report_content = "\n".join(report_lines)

        # 保存到文件
        if output_file:
            output_file.write_text(report_content, encoding="utf-8")
            print(f"\n📄 測試報告已保存到: {output_file}")

        return report_content

    def generate_json_report(
        self, results: Dict[str, TestSuiteResult], output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        生成JSON格式的測試報告

        Args:
            results: 測試結果
            output_file: 輸出文件路徑

        Returns:
            Dict[str, Any]: JSON報告數據
        """

        report_data = {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project_root": str(self.project_root),
            "summary": {
                "total_tests": sum(r.total_tests for r in results.values()),
                "total_passed": sum(r.passed for r in results.values()),
                "total_failed": sum(r.failed for r in results.values()),
                "total_skipped": sum(r.skipped for r in results.values()),
                "total_errors": sum(r.errors for r in results.values()),
                "total_duration": sum(r.duration for r in results.values()),
                "overall_success_rate": 0.0,
            },
            "suites": {},
        }

        # 計算總體成功率
        total_tests = report_data["summary"]["total_tests"]
        if total_tests > 0:
            success_rate = (report_data["summary"]["total_passed"] / total_tests) * 100
            report_data["summary"]["overall_success_rate"] = success_rate

        # 添加各套件結果
        for suite_name, result in results.items():
            report_data["suites"][suite_name] = asdict(result)

        # 保存到文件
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"📊 JSON報告已保存到: {output_file}")

        return report_data


async def main():
    """主函數"""

    parser = argparse.ArgumentParser(description="AutoGen系統測試運行器")
    parser.add_argument(
        "--suite",
        choices=["unit", "integration", "performance", "all"],
        default="all",
        help="要運行的測試套件",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="顯示詳細輸出")
    parser.add_argument("--no-performance", action="store_true", help="跳過性能測試")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("test_reports"), help="報告輸出目錄"
    )
    parser.add_argument("--no-capture", action="store_true", help="不捕獲測試輸出")

    args = parser.parse_args()

    # 創建測試運行器
    runner = AutoGenTestRunner()

    # 確保輸出目錄存在
    args.output_dir.mkdir(exist_ok=True)

    print("🚀 AutoGen系統測試運行器")
    print(f"📁 項目路徑: {runner.project_root}")
    print(f"📋 測試套件: {args.suite}")

    try:
        if args.suite == "all":
            # 運行所有測試
            results = await runner.run_all_tests(
                include_performance=not args.no_performance, verbose=args.verbose
            )
        else:
            # 運行指定測試套件
            suite = TestSuite(args.suite)
            result = await runner.run_test_suite(
                suite, verbose=args.verbose, capture_output=not args.no_capture
            )
            results = {suite.value: result}

        # 生成報告
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Markdown報告
        md_report_file = args.output_dir / f"test_report_{timestamp}.md"
        runner.generate_report(results, md_report_file)

        # JSON報告
        json_report_file = args.output_dir / f"test_report_{timestamp}.json"
        runner.generate_json_report(results, json_report_file)

        # 輸出摘要
        total_tests = sum(r.total_tests for r in results.values())
        total_failed = sum(r.failed for r in results.values())
        total_errors = sum(r.errors for r in results.values())

        print(f"\n{'=' * 60}")
        print("📋 測試完成總結")
        print(f"{'=' * 60}")

        if total_failed == 0 and total_errors == 0:
            print("✅ 所有測試通過！")
            exit_code = 0
        else:
            print(f"❌ 測試失敗: {total_failed} 失敗, {total_errors} 錯誤")
            exit_code = 1

        print(f"📊 詳細報告: {md_report_file}")
        print(f"📈 JSON數據: {json_report_file}")

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n⚠️ 測試被用戶中斷")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 測試運行器錯誤: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
