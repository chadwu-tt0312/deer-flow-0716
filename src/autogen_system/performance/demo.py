#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen性能優化演示

展示性能監控、分析和優化的完整流程。
"""

import asyncio
import time
import random
from pathlib import Path

from src.logging import get_logger
from .metrics import create_metrics_collector, WorkflowMetricsCollector
from .profiler import create_profiler
from .optimizer import create_optimizer
from .analyzer import create_analyzer

logger = get_logger(__name__)


class PerformanceDemo:
    """性能優化演示"""

    def __init__(self):
        """初始化演示"""
        self.metrics_collector = create_metrics_collector(
            collection_interval=0.5, workflow_specific=True
        )
        self.profiler = create_profiler()
        self.optimizer = create_optimizer(self.metrics_collector)
        self.analyzer = create_analyzer()

    async def run_demo(self):
        """運行完整演示"""
        print("🚀 AutoGen性能優化演示開始")
        print("=" * 60)

        try:
            # 1. 開始性能監控
            await self._demo_performance_monitoring()

            # 2. 模擬工作負載
            await self._demo_workload_simulation()

            # 3. 性能分析
            await self._demo_performance_analysis()

            # 4. 優化建議
            await self._demo_optimization()

            print("\n✅ 演示完成!")

        except Exception as e:
            logger.error(f"演示過程中出錯: {e}")
            print(f"❌ 演示失敗: {e}")

    async def _demo_performance_monitoring(self):
        """演示性能監控"""
        print("\n📊 步驟1: 性能監控")
        print("-" * 30)

        # 開始收集指標
        self.metrics_collector.start_collection()
        print("✓ 系統指標收集已開始")

        # 開始性能分析
        self.profiler.start_profiling()
        print("✓ 性能分析已開始")

        # 讓監控運行一段時間
        await asyncio.sleep(2)

        # 顯示當前指標
        metrics = self.metrics_collector.get_metrics()
        latest_memory = metrics.get_latest("memory_usage_mb")
        latest_cpu = metrics.get_latest("cpu_usage")

        if latest_memory:
            print(f"📈 當前內存使用: {latest_memory.value:.1f}MB")
        if latest_cpu:
            print(f"📈 當前CPU使用: {latest_cpu.value:.1f}%")

    async def _demo_workload_simulation(self):
        """演示工作負載模擬"""
        print("\n⚡ 步驟2: 工作負載模擬")
        print("-" * 30)

        # 模擬不同類型的工作負載
        await self._simulate_cpu_intensive_task()
        await self._simulate_memory_intensive_task()
        await self._simulate_io_intensive_task()
        await self._simulate_workflow_execution()

    async def _simulate_cpu_intensive_task(self):
        """模擬CPU密集型任務"""
        print("🔥 模擬CPU密集型任務...")

        with self.metrics_collector.measure_latency("cpu_intensive"):
            # 模擬CPU密集型計算
            start_time = time.time()
            total = 0
            while time.time() - start_time < 1.0:  # 運行1秒
                total += sum(range(1000))

            self.metrics_collector.add_metric("cpu_task_result", total)

        print("✓ CPU密集型任務完成")

    async def _simulate_memory_intensive_task(self):
        """模擬內存密集型任務"""
        print("💾 模擬內存密集型任務...")

        with self.metrics_collector.measure_latency("memory_intensive"):
            # 模擬大量內存分配
            large_data = []
            for i in range(100):
                large_data.append([random.random() for _ in range(10000)])
                if i % 20 == 0:
                    await asyncio.sleep(0.1)  # 讓出控制權

            # 記錄內存使用
            memory_size = len(large_data) * len(large_data[0]) * 8  # 估算字節數
            self.metrics_collector.add_metric("allocated_memory_mb", memory_size / 1024 / 1024)

            # 清理內存
            del large_data

        print("✓ 內存密集型任務完成")

    async def _simulate_io_intensive_task(self):
        """模擬IO密集型任務"""
        print("💿 模擬IO密集型任務...")

        # 模擬多個IO操作
        io_tasks = []
        for i in range(5):
            task = self._simulate_single_io_operation(f"io_op_{i}")
            io_tasks.append(task)

        # 並發執行IO操作
        await asyncio.gather(*io_tasks)
        print("✓ IO密集型任務完成")

    async def _simulate_single_io_operation(self, operation_name: str):
        """模擬單個IO操作"""
        with self.metrics_collector.measure_latency(f"io_{operation_name}"):
            # 模擬IO延遲
            delay = random.uniform(0.1, 0.5)
            await asyncio.sleep(delay)

            # 記錄IO操作
            self.metrics_collector.increment_counter("io_operations")

    async def _simulate_workflow_execution(self):
        """模擬工作流執行"""
        print("🔄 模擬工作流執行...")

        if isinstance(self.metrics_collector, WorkflowMetricsCollector):
            # 模擬3個不同的工作流
            workflows = [
                ("prose_workflow", "prose"),
                ("research_workflow", "research"),
                ("optimization_workflow", "optimization"),
            ]

            for workflow_id, workflow_type in workflows:
                # 開始工作流
                self.metrics_collector.record_workflow_start(workflow_id, workflow_type)

                # 模擬工作流步驟
                steps = ["init", "process", "finalize"]
                for step in steps:
                    step_duration = random.uniform(0.2, 0.8)
                    await asyncio.sleep(step_duration)

                    success = random.random() > 0.1  # 90%成功率
                    self.metrics_collector.record_step_execution(
                        workflow_id, step, step_duration, success
                    )

                # 結束工作流
                workflow_success = random.random() > 0.05  # 95%成功率
                self.metrics_collector.record_workflow_end(
                    workflow_id, workflow_type, workflow_success
                )

                print(f"  ✓ {workflow_type} 工作流完成")

    async def _demo_performance_analysis(self):
        """演示性能分析"""
        print("\n🔍 步驟3: 性能分析")
        print("-" * 30)

        # 停止收集並獲取結果
        self.metrics_collector.stop_collection()
        profiler_result = self.profiler.stop_profiling()

        # 獲取指標數據
        metrics = self.metrics_collector.get_metrics()

        # 執行綜合分析
        analysis_result = self.analyzer.analyze_performance(metrics, profiler_result)

        # 顯示分析結果
        print(f"📊 總體性能分數: {analysis_result.overall_score:.1f}/100")

        if analysis_result.bottlenecks:
            print(f"🔍 發現 {len(analysis_result.bottlenecks)} 個性能瓶頸:")
            for bottleneck in analysis_result.bottlenecks[:3]:  # 顯示前3個
                print(f"  - {bottleneck.description} (嚴重程度: {bottleneck.severity:.1f})")
        else:
            print("✅ 未發現明顯性能瓶頸")

        if analysis_result.trends:
            print(f"📈 性能趨勢分析:")
            for trend in analysis_result.trends[:3]:  # 顯示前3個
                direction_icon = {"improving": "📈", "degrading": "📉", "stable": "➡️"}
                icon = direction_icon.get(trend.trend_direction, "➡️")
                print(f"  {icon} {trend.metric_name}: {trend.trend_direction}")

        # 保存詳細報告
        report = self.analyzer.generate_analysis_report(analysis_result)
        report_file = Path("performance_analysis_report.md")
        report_file.write_text(report, encoding="utf-8")
        print(f"📄 詳細分析報告已保存到: {report_file}")

        return analysis_result, metrics, profiler_result

    async def _demo_optimization(self):
        """演示優化建議"""
        print("\n🎯 步驟4: 優化建議")
        print("-" * 30)

        # 重新收集一些基準數據
        self.metrics_collector.start_collection()
        await asyncio.sleep(1)
        metrics = self.metrics_collector.get_metrics()
        self.metrics_collector.stop_collection()

        # 生成優化建議
        optimization_result = await self.optimizer.analyze_performance(metrics=metrics)

        print(f"💡 生成了 {len(optimization_result.suggestions)} 個優化建議:")

        # 顯示高優先級建議
        high_priority = [s for s in optimization_result.suggestions if s.priority >= 8]
        if high_priority:
            print("\n🔴 高優先級建議:")
            for suggestion in high_priority:
                print(f"  - {suggestion.description}")
                print(f"    預期改進: {suggestion.estimated_improvement:.1f}%")
                print(f"    實施難度: {suggestion.implementation_effort}")

        # 應用自動優化
        print("\n🔧 應用自動優化...")
        applied_optimizations = await self.optimizer.apply_automatic_optimizations()

        if applied_optimizations:
            print("✅ 已應用以下自動優化:")
            for optimization in applied_optimizations:
                print(f"  - {optimization}")
        else:
            print("📝 當前無可自動應用的優化")

        # 生成優化報告
        optimization_report = self.optimizer.generate_optimization_report(optimization_result)
        report_file = Path("optimization_report.md")
        report_file.write_text(optimization_report, encoding="utf-8")
        print(f"📄 優化報告已保存到: {report_file}")

        # 顯示指標摘要
        print("\n📊 性能指標摘要:")
        summary = self.metrics_collector.get_summary_report()

        if "metrics" in summary:
            for metric_name, stats in list(summary["metrics"].items())[:5]:  # 顯示前5個
                if "mean" in stats:
                    unit = (
                        "MB" if "memory" in metric_name else "%" if "usage" in metric_name else "s"
                    )
                    print(f"  - {metric_name}: {stats['mean']:.2f} {unit} (平均)")


async def main():
    """主函數"""
    demo = PerformanceDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
