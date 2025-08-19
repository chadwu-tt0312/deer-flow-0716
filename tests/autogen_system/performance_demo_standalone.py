#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen性能優化獨立演示

不依賴autogen_core的性能監控和優化演示。
"""

import asyncio
import time
import random
import statistics
import threading
import psutil
import gc
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class MetricType(Enum):
    """指標類型"""

    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    CPU = "cpu"


@dataclass
class MetricPoint:
    """指標數據點"""

    timestamp: float
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class SimpleMetricsCollector:
    """簡化的指標收集器"""

    def __init__(self):
        self.metrics = {}
        self.is_collecting = False
        self.collection_thread = None
        self.process = psutil.Process()

    def start_collection(self):
        """開始收集指標"""
        if self.is_collecting:
            return

        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collect_metrics)
        self.collection_thread.start()
        print("✓ 性能指標收集已開始")

    def stop_collection(self):
        """停止收集指標"""
        if not self.is_collecting:
            return

        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join()
        print("✓ 性能指標收集已停止")

    def _collect_metrics(self):
        """收集系統指標"""
        while self.is_collecting:
            try:
                # CPU使用率
                cpu_percent = self.process.cpu_percent()
                self.add_metric("cpu_usage", cpu_percent)

                # 內存使用
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self.add_metric("memory_usage_mb", memory_mb)

                # 線程數
                thread_count = self.process.num_threads()
                self.add_metric("thread_count", thread_count)

            except Exception as e:
                print(f"收集指標時出錯: {e}")

            time.sleep(0.5)

    def add_metric(self, name: str, value: float, metadata: Dict[str, Any] = None):
        """添加指標"""
        if name not in self.metrics:
            self.metrics[name] = []

        point = MetricPoint(timestamp=time.time(), value=value, metadata=metadata or {})
        self.metrics[name].append(point)

        # 限制數據點數量
        if len(self.metrics[name]) > 100:
            self.metrics[name] = self.metrics[name][-100:]

    def get_average(self, name: str) -> Optional[float]:
        """獲取平均值"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        values = [point.value for point in self.metrics[name]]
        return statistics.mean(values)

    def get_latest(self, name: str) -> Optional[float]:
        """獲取最新值"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        return self.metrics[name][-1].value

    def measure_latency(self, operation_name: str):
        """測量延遲的上下文管理器"""

        class LatencyMeasurer:
            def __init__(self, collector, name):
                self.collector = collector
                self.name = name
                self.start_time = None

            def __enter__(self):
                self.start_time = time.time()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.start_time:
                    duration = time.time() - self.start_time
                    self.collector.add_metric(f"latency_{self.name}", duration)

        return LatencyMeasurer(self, operation_name)


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self):
        self.bottlenecks = []
        self.recommendations = []

    def analyze(self, metrics_collector: SimpleMetricsCollector) -> Dict[str, Any]:
        """分析性能"""
        analysis = {
            "overall_score": 100.0,
            "bottlenecks": [],
            "recommendations": [],
            "insights": [],
        }

        # 分析內存使用
        memory_avg = metrics_collector.get_average("memory_usage_mb")
        if memory_avg and memory_avg > 500:
            analysis["bottlenecks"].append(
                {
                    "type": "memory",
                    "severity": min(1.0, memory_avg / 1000),
                    "description": f"內存使用較高: {memory_avg:.1f}MB",
                }
            )
            analysis["recommendations"].append("優化內存使用，檢查內存洩漏")
            analysis["overall_score"] -= 15

        # 分析CPU使用
        cpu_avg = metrics_collector.get_average("cpu_usage")
        if cpu_avg and cpu_avg > 70:
            analysis["bottlenecks"].append(
                {
                    "type": "cpu",
                    "severity": min(1.0, cpu_avg / 100),
                    "description": f"CPU使用率較高: {cpu_avg:.1f}%",
                }
            )
            analysis["recommendations"].append("優化CPU密集型操作")
            analysis["overall_score"] -= 10

        # 分析延遲
        latency_metrics = [
            name for name in metrics_collector.metrics.keys() if name.startswith("latency_")
        ]

        high_latency_count = 0
        for metric_name in latency_metrics:
            avg_latency = metrics_collector.get_average(metric_name)
            if avg_latency and avg_latency > 1.0:  # 大於1秒
                operation = metric_name.replace("latency_", "")
                analysis["bottlenecks"].append(
                    {
                        "type": "latency",
                        "severity": min(1.0, avg_latency / 5.0),
                        "description": f"操作 {operation} 延遲較高: {avg_latency:.2f}s",
                    }
                )
                high_latency_count += 1

        if high_latency_count > 0:
            analysis["recommendations"].append("優化高延遲操作，考慮異步處理")
            analysis["overall_score"] -= high_latency_count * 5

        # 生成洞察
        if analysis["overall_score"] >= 90:
            analysis["insights"].append("系統性能優秀，運行良好")
        elif analysis["overall_score"] >= 75:
            analysis["insights"].append("系統性能良好，有小幅優化空間")
        elif analysis["overall_score"] >= 60:
            analysis["insights"].append("系統性能一般，需要注意優化")
        else:
            analysis["insights"].append("系統性能需要改進，建議立即優化")

        if len(analysis["bottlenecks"]) > 2:
            analysis["insights"].append("發現多個性能瓶頸，建議系統性優化")

        return analysis


class PerformanceOptimizer:
    """性能優化器"""

    def __init__(self):
        self.optimizations_applied = []

    async def apply_optimizations(self) -> List[str]:
        """應用自動優化"""
        optimizations = []

        try:
            # 1. 垃圾回收優化
            before_objects = len(gc.get_objects())
            collected = gc.collect()
            after_objects = len(gc.get_objects())

            if collected > 0:
                optimizations.append(f"垃圾回收: 釋放了 {collected} 個對象")
                optimizations.append(f"對象數量: {before_objects} -> {after_objects}")

            # 2. 內存優化
            import sys

            before_refs = sys.gettotalrefcount() if hasattr(sys, "gettotalrefcount") else 0

            # 清理可能的循環引用
            gc.set_threshold(700, 10, 10)  # 更激進的垃圾回收
            optimizations.append("調整垃圾回收閾值以更頻繁清理")

            # 3. 併發優化建議
            import os

            cpu_count = os.cpu_count()
            optimizations.append(f"建議線程池大小: {cpu_count * 2} (基於 {cpu_count} 核CPU)")

        except Exception as e:
            print(f"應用優化時出錯: {e}")

        self.optimizations_applied.extend(optimizations)
        return optimizations


class PerformanceDemo:
    """性能演示"""

    def __init__(self):
        self.metrics_collector = SimpleMetricsCollector()
        self.analyzer = PerformanceAnalyzer()
        self.optimizer = PerformanceOptimizer()

    async def run_demo(self):
        """運行演示"""
        print("🚀 AutoGen性能優化演示開始")
        print("=" * 60)

        try:
            # 1. 開始監控
            await self._start_monitoring()

            # 2. 模擬工作負載
            await self._simulate_workloads()

            # 3. 性能分析
            await self._analyze_performance()

            # 4. 應用優化
            await self._apply_optimizations()

            # 5. 生成報告
            await self._generate_reports()

            print("\n✅ 演示完成!")

        except Exception as e:
            print(f"❌ 演示失敗: {e}")
            import traceback

            traceback.print_exc()

    async def _start_monitoring(self):
        """開始監控"""
        print("\n📊 步驟1: 開始性能監控")
        print("-" * 30)

        self.metrics_collector.start_collection()
        await asyncio.sleep(1)  # 收集一些基準數據

        # 顯示初始狀態
        memory = self.metrics_collector.get_latest("memory_usage_mb")
        cpu = self.metrics_collector.get_latest("cpu_usage")

        if memory:
            print(f"📈 初始內存使用: {memory:.1f}MB")
        if cpu:
            print(f"📈 初始CPU使用: {cpu:.1f}%")

    async def _simulate_workloads(self):
        """模擬工作負載"""
        print("\n⚡ 步驟2: 模擬工作負載")
        print("-" * 30)

        # CPU密集型任務
        print("🔥 執行CPU密集型任務...")
        with self.metrics_collector.measure_latency("cpu_intensive"):
            await self._cpu_intensive_task()

        # 內存密集型任務
        print("💾 執行內存密集型任務...")
        with self.metrics_collector.measure_latency("memory_intensive"):
            await self._memory_intensive_task()

        # IO密集型任務
        print("💿 執行IO密集型任務...")
        with self.metrics_collector.measure_latency("io_intensive"):
            await self._io_intensive_task()

        # 混合任務
        print("🔄 執行混合工作負載...")
        await self._mixed_workload()

    async def _cpu_intensive_task(self):
        """CPU密集型任務"""
        start_time = time.time()
        total = 0

        # 運行1秒的計算
        while time.time() - start_time < 1.0:
            total += sum(range(1000))
            await asyncio.sleep(0.001)  # 讓出控制權

        self.metrics_collector.add_metric("cpu_task_operations", total)

    async def _memory_intensive_task(self):
        """內存密集型任務"""
        large_data = []

        # 分配大量內存
        for i in range(50):
            chunk = [random.random() for _ in range(10000)]
            large_data.append(chunk)

            if i % 10 == 0:
                await asyncio.sleep(0.1)
                # 記錄內存使用
                current_memory = self.metrics_collector.get_latest("memory_usage_mb")
                if current_memory:
                    self.metrics_collector.add_metric("peak_memory", current_memory)

        # 估算分配的內存
        estimated_mb = len(large_data) * len(large_data[0]) * 8 / 1024 / 1024
        self.metrics_collector.add_metric("allocated_memory_mb", estimated_mb)

        # 清理
        del large_data
        gc.collect()

    async def _io_intensive_task(self):
        """IO密集型任務"""
        tasks = []

        # 模擬多個並發IO操作
        for i in range(5):
            task = self._simulate_io_operation(f"operation_{i}")
            tasks.append(task)

        await asyncio.gather(*tasks)

    async def _simulate_io_operation(self, name: str):
        """模擬單個IO操作"""
        with self.metrics_collector.measure_latency(f"io_{name}"):
            # 模擬IO延遲
            delay = random.uniform(0.1, 0.3)
            await asyncio.sleep(delay)

            # 記錄操作
            self.metrics_collector.add_metric("io_operations", 1)

    async def _mixed_workload(self):
        """混合工作負載"""
        tasks = []

        # 併發執行不同類型的任務
        for i in range(3):
            # CPU任務
            tasks.append(self._light_cpu_task(f"cpu_{i}"))
            # IO任務
            tasks.append(self._light_io_task(f"io_{i}"))

        await asyncio.gather(*tasks)

    async def _light_cpu_task(self, name: str):
        """輕量CPU任務"""
        with self.metrics_collector.measure_latency(f"light_cpu_{name}"):
            total = sum(range(5000))
            await asyncio.sleep(0.1)
            self.metrics_collector.add_metric("light_cpu_result", total)

    async def _light_io_task(self, name: str):
        """輕量IO任務"""
        with self.metrics_collector.measure_latency(f"light_io_{name}"):
            await asyncio.sleep(random.uniform(0.05, 0.15))
            self.metrics_collector.add_metric("light_io_operations", 1)

    async def _analyze_performance(self):
        """分析性能"""
        print("\n🔍 步驟3: 性能分析")
        print("-" * 30)

        # 停止收集數據進行分析
        self.metrics_collector.stop_collection()

        # 執行分析
        analysis = self.analyzer.analyze(self.metrics_collector)

        # 顯示分析結果
        print(f"📊 總體性能分數: {analysis['overall_score']:.1f}/100")

        if analysis["overall_score"] >= 90:
            grade = "優秀 🟢"
        elif analysis["overall_score"] >= 75:
            grade = "良好 🟡"
        elif analysis["overall_score"] >= 60:
            grade = "一般 🟠"
        else:
            grade = "需要改進 🔴"

        print(f"🎯 性能等級: {grade}")

        # 顯示瓶頸
        if analysis["bottlenecks"]:
            print(f"\n🔍 發現 {len(analysis['bottlenecks'])} 個性能瓶頸:")
            for bottleneck in analysis["bottlenecks"]:
                severity = bottleneck["severity"]
                icon = "🔴" if severity > 0.7 else "🟡" if severity > 0.4 else "🟢"
                print(f"  {icon} {bottleneck['description']}")
        else:
            print("\n✅ 未發現明顯性能瓶頸")

        # 顯示洞察
        if analysis["insights"]:
            print(f"\n💡 關鍵洞察:")
            for insight in analysis["insights"]:
                print(f"  - {insight}")

        return analysis

    async def _apply_optimizations(self):
        """應用優化"""
        print("\n🎯 步驟4: 應用優化")
        print("-" * 30)

        optimizations = await self.optimizer.apply_optimizations()

        if optimizations:
            print("✅ 已應用以下優化:")
            for opt in optimizations:
                print(f"  - {opt}")
        else:
            print("📝 當前無可應用的自動優化")

    async def _generate_reports(self):
        """生成報告"""
        print("\n📄 步驟5: 生成報告")
        print("-" * 30)

        # 收集報告數據
        report_data = {
            "performance_summary": {
                "memory_avg": self.metrics_collector.get_average("memory_usage_mb"),
                "cpu_avg": self.metrics_collector.get_average("cpu_usage"),
                "thread_avg": self.metrics_collector.get_average("thread_count"),
            },
            "latency_summary": {},
            "optimizations": self.optimizer.optimizations_applied,
        }

        # 收集延遲數據
        for metric_name in self.metrics_collector.metrics:
            if metric_name.startswith("latency_"):
                avg_latency = self.metrics_collector.get_average(metric_name)
                if avg_latency:
                    operation = metric_name.replace("latency_", "")
                    report_data["latency_summary"][operation] = f"{avg_latency:.3f}s"

        # 生成簡單報告
        report_lines = []
        report_lines.append("# AutoGen性能測試報告")
        report_lines.append(f"\n**測試時間**: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 性能摘要
        report_lines.append("\n## 📊 性能摘要")
        summary = report_data["performance_summary"]
        if summary["memory_avg"]:
            report_lines.append(f"- **平均內存使用**: {summary['memory_avg']:.1f}MB")
        if summary["cpu_avg"]:
            report_lines.append(f"- **平均CPU使用**: {summary['cpu_avg']:.1f}%")
        if summary["thread_avg"]:
            report_lines.append(f"- **平均線程數**: {summary['thread_avg']:.0f}")

        # 延遲摘要
        if report_data["latency_summary"]:
            report_lines.append("\n## ⏱️ 延遲摘要")
            for operation, latency in report_data["latency_summary"].items():
                report_lines.append(f"- **{operation}**: {latency}")

        # 優化記錄
        if report_data["optimizations"]:
            report_lines.append("\n## 🔧 已應用優化")
            for opt in report_data["optimizations"]:
                report_lines.append(f"- {opt}")

        # 保存報告
        report_content = "\n".join(report_lines)
        report_file = Path("autogen_performance_report.md")
        report_file.write_text(report_content, encoding="utf-8")

        print(f"📄 性能報告已保存到: {report_file}")

        # 顯示摘要
        print("\n📊 性能測試摘要:")
        if summary["memory_avg"]:
            print(f"  💾 平均內存: {summary['memory_avg']:.1f}MB")
        if summary["cpu_avg"]:
            print(f"  🔥 平均CPU: {summary['cpu_avg']:.1f}%")

        if report_data["latency_summary"]:
            print("  ⏱️ 主要延遲:")
            for operation, latency in list(report_data["latency_summary"].items())[:3]:
                print(f"    - {operation}: {latency}")


async def main():
    """主函數"""
    demo = PerformanceDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
