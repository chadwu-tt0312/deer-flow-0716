# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
AutoGen系統性能測試

測試系統性能指標和瓶頸。
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

from src.autogen_system.controllers.workflow_controller import WorkflowController
from src.autogen_system.workflows.prose_workflow import ProseWorkflowManager
from src.autogen_system.workflows.prompt_enhancer_workflow import PromptEnhancerWorkflowManager


class TestPerformanceMetrics:
    """性能指標測試"""

    @pytest.mark.performance
    async def test_workflow_execution_time(self, performance_monitor):
        """測試工作流執行時間"""

        # 創建模擬工作流控制器
        controller = WorkflowController()

        # 測量不同大小工作流的執行時間
        execution_times = []

        for step_count in [1, 5, 10, 20]:
            # 創建工作流計劃
            from src.autogen_system.controllers.workflow_controller import (
                WorkflowPlan,
                WorkflowStep,
                StepType,
            )

            steps = [
                WorkflowStep(
                    id=f"step_{i}",
                    name=f"步驟 {i}",
                    step_type=StepType.PROCESSING,
                    description=f"第 {i} 個步驟",
                    dependencies=[f"step_{i - 1}"] if i > 0 else [],
                    estimated_duration=10,
                )
                for i in range(step_count)
            ]

            plan = WorkflowPlan(
                id=f"perf_test_{step_count}",
                name=f"性能測試 {step_count} 步驟",
                description="性能測試計劃",
                steps=steps,
                estimated_duration=step_count * 10,
            )

            # 測量執行時間
            async def mock_executor(step, state):
                await asyncio.sleep(0.01)  # 模擬處理時間
                return state

            start_time = time.time()
            await controller.execute_plan(plan, {}, mock_executor)
            end_time = time.time()

            execution_time = end_time - start_time
            execution_times.append(execution_time)

            print(f"步驟數: {step_count}, 執行時間: {execution_time:.3f}s")

        # 驗證執行時間隨步驟數線性增長
        assert len(execution_times) == 4

        # 檢查時間增長趨勢（允許一些變動）
        for i in range(1, len(execution_times)):
            ratio = execution_times[i] / execution_times[i - 1]
            # 執行時間應該大致與步驟數成正比
            assert 1.0 < ratio < 10.0, f"執行時間增長異常: {ratio}"

    @pytest.mark.performance
    async def test_concurrent_workflow_performance(self, performance_monitor):
        """測試並發工作流性能"""

        async def mock_workflow_task(task_id: int, duration: float = 0.1):
            """模擬工作流任務"""
            start_time = time.time()
            await asyncio.sleep(duration)
            end_time = time.time()
            return {"task_id": task_id, "duration": end_time - start_time, "status": "completed"}

        # 測試不同並發級別
        concurrency_levels = [1, 5, 10, 20]

        for concurrency in concurrency_levels:
            with performance_monitor.measure(f"concurrent_{concurrency}"):
                # 創建並發任務
                tasks = [mock_workflow_task(i, 0.1) for i in range(concurrency)]

                # 並發執行
                results = await asyncio.gather(*tasks)

                # 驗證所有任務完成
                assert len(results) == concurrency
                for result in results:
                    assert result["status"] == "completed"

        # 分析性能結果
        measurements = performance_monitor.measurements

        # 驗證並發執行效率
        sequential_time = measurements.get("concurrent_1", 0.1)
        parallel_10_time = measurements.get("concurrent_10", 1.0)

        # 10個並發任務不應該比1個任務慢10倍
        efficiency = sequential_time * 10 / parallel_10_time
        assert efficiency > 5.0, f"並發效率過低: {efficiency}"

    @pytest.mark.performance
    async def test_memory_efficiency(self):
        """測試內存效率"""

        import gc
        import psutil
        import os

        # 獲取當前進程
        process = psutil.Process(os.getpid())

        # 記錄初始內存
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_objects = len(gc.get_objects())

        # 創建大量工作流對象
        workflows = []
        for i in range(100):
            # 模擬工作流管理器創建
            mock_manager = Mock()
            mock_manager.conversation_manager = Mock()
            mock_manager.workflow_controller = Mock()
            workflows.append(mock_manager)

        # 模擬工作流執行
        for workflow in workflows[:10]:  # 只執行一部分
            with patch.object(workflow, "process_request", new_callable=AsyncMock) as mock_process:
                mock_process.return_value = "Mock result"
                await mock_process("test task")

        # 檢查內存使用
        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = current_memory - initial_memory

        # 清理對象
        del workflows
        gc.collect()

        # 檢查內存釋放
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        final_objects = len(gc.get_objects())

        print(f"初始內存: {initial_memory:.2f}MB")
        print(f"峰值內存: {current_memory:.2f}MB")
        print(f"最終內存: {final_memory:.2f}MB")
        print(f"內存增長: {memory_growth:.2f}MB")
        print(f"對象增長: {final_objects - initial_objects}")

        # 驗證內存效率
        assert memory_growth < 100, f"內存增長過多: {memory_growth}MB"
        assert final_objects - initial_objects < 1000, (
            f"對象洩漏: {final_objects - initial_objects}"
        )

    @pytest.mark.performance
    async def test_agent_response_time(self, mock_model_client):
        """測試代理響應時間"""

        from src.autogen_system.agents.coordinator_agent import CoordinatorAgent

        # 配置模擬客戶端延遲
        response_times = []

        async def mock_complete_with_delay(messages, **kwargs):
            delay = 0.05  # 50ms模擬網絡延遲
            await asyncio.sleep(delay)
            return "Mock response"

        mock_model_client.complete = mock_complete_with_delay

        # 創建代理
        agent = CoordinatorAgent(model_client=mock_model_client, tools=[])

        # 測量多次請求的響應時間
        for i in range(10):
            start_time = time.time()
            await agent.process_request(f"Test request {i}")
            end_time = time.time()

            response_time = end_time - start_time
            response_times.append(response_time)

        # 分析響應時間
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        std_response_time = statistics.stdev(response_times)

        print(f"平均響應時間: {avg_response_time:.3f}s")
        print(f"最大響應時間: {max_response_time:.3f}s")
        print(f"最小響應時間: {min_response_time:.3f}s")
        print(f"響應時間標準差: {std_response_time:.3f}s")

        # 驗證響應時間在合理範圍內
        assert avg_response_time < 0.2, f"平均響應時間過長: {avg_response_time}s"
        assert std_response_time < 0.1, f"響應時間變動過大: {std_response_time}s"

    @pytest.mark.performance
    async def test_tool_execution_performance(self):
        """測試工具執行性能"""

        # 創建模擬工具
        class MockTool:
            def __init__(self, execution_time: float):
                self.execution_time = execution_time
                self.call_count = 0

            async def __call__(self, **kwargs):
                self.call_count += 1
                await asyncio.sleep(self.execution_time)
                return f"Tool result {self.call_count}"

        # 測試不同執行時間的工具
        tools = {
            "fast_tool": MockTool(0.01),  # 10ms
            "medium_tool": MockTool(0.05),  # 50ms
            "slow_tool": MockTool(0.1),  # 100ms
        }

        # 測量工具執行性能
        tool_performance = {}

        for tool_name, tool in tools.items():
            execution_times = []

            # 執行多次測量
            for _ in range(5):
                start_time = time.time()
                await tool(test_param="value")
                end_time = time.time()

                execution_times.append(end_time - start_time)

            avg_time = statistics.mean(execution_times)
            tool_performance[tool_name] = avg_time

            print(f"{tool_name}: 平均執行時間 {avg_time:.3f}s")

        # 驗證工具性能符合預期
        assert tool_performance["fast_tool"] < 0.02
        assert tool_performance["medium_tool"] < 0.08
        assert tool_performance["slow_tool"] < 0.15

    @pytest.mark.performance
    async def test_prose_workflow_performance(self, mock_conversation_manager):
        """測試Prose工作流性能"""

        from src.autogen_system.workflows.prose_workflow import ProseOption

        prose_manager = ProseWorkflowManager(mock_conversation_manager)

        # 模擬工作流執行
        with patch.object(prose_manager.workflow_controller, "execute_plan") as mock_execute:
            mock_execute.return_value = {
                "status": "completed",
                "output": "Processed content",
                "execution_time": 0.5,
            }

            # 測試不同選項的性能
            performance_results = {}

            for option in ProseOption:
                execution_times = []

                # 執行多次測量
                for _ in range(3):
                    start_time = time.time()

                    result = await prose_manager.process_prose_simple(
                        content="Test content for performance", option=option
                    )

                    end_time = time.time()
                    execution_times.append(end_time - start_time)

                avg_time = statistics.mean(execution_times)
                performance_results[option.value] = avg_time

                print(f"Prose {option.value}: 平均執行時間 {avg_time:.3f}s")

            # 驗證所有選項性能在合理範圍內
            for option, avg_time in performance_results.items():
                assert avg_time < 1.0, f"Prose {option} 執行時間過長: {avg_time}s"

    @pytest.mark.performance
    async def test_load_testing(self):
        """測試負載能力"""

        async def simulate_user_request(user_id: int):
            """模擬用戶請求"""
            # 模擬請求處理時間
            processing_time = 0.05 + (user_id % 10) * 0.01  # 50-140ms
            await asyncio.sleep(processing_time)

            return {
                "user_id": user_id,
                "response": f"Response for user {user_id}",
                "processing_time": processing_time,
            }

        # 模擬不同負載級別
        load_levels = [10, 50, 100]

        for load in load_levels:
            print(f"\n測試負載級別: {load} 並發用戶")

            start_time = time.time()

            # 創建並發請求
            tasks = [simulate_user_request(i) for i in range(load)]

            # 執行負載測試
            results = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            total_time = end_time - start_time

            # 統計結果
            successful_requests = [r for r in results if not isinstance(r, Exception)]
            failed_requests = [r for r in results if isinstance(r, Exception)]

            success_rate = len(successful_requests) / load * 100
            throughput = load / total_time

            print(f"總時間: {total_time:.3f}s")
            print(f"成功率: {success_rate:.1f}%")
            print(f"吞吐量: {throughput:.1f} 請求/秒")
            print(f"失敗請求: {len(failed_requests)}")

            # 驗證負載測試結果
            assert success_rate >= 95.0, f"成功率過低: {success_rate}%"
            assert throughput > load / 10, f"吞吐量過低: {throughput} 請求/秒"

    @pytest.mark.performance
    async def test_resource_utilization(self):
        """測試資源利用率"""

        import psutil
        import threading
        import time

        # 資源監控器
        class ResourceMonitor:
            def __init__(self):
                self.cpu_samples = []
                self.memory_samples = []
                self.monitoring = False

            def start_monitoring(self):
                self.monitoring = True
                thread = threading.Thread(target=self._monitor)
                thread.start()
                return thread

            def stop_monitoring(self):
                self.monitoring = False

            def _monitor(self):
                while self.monitoring:
                    self.cpu_samples.append(psutil.cpu_percent())
                    self.memory_samples.append(psutil.virtual_memory().percent)
                    time.sleep(0.1)

        # 開始監控
        monitor = ResourceMonitor()
        monitor_thread = monitor.start_monitoring()

        try:
            # 模擬高負載工作
            async def cpu_intensive_task():
                # 模擬CPU密集型任務
                for _ in range(1000):
                    await asyncio.sleep(0.001)

            # 執行多個並發任務
            tasks = [cpu_intensive_task() for _ in range(10)]
            await asyncio.gather(*tasks)

        finally:
            # 停止監控
            monitor.stop_monitoring()
            monitor_thread.join(timeout=1.0)

        # 分析資源使用
        if monitor.cpu_samples and monitor.memory_samples:
            avg_cpu = statistics.mean(monitor.cpu_samples)
            max_cpu = max(monitor.cpu_samples)
            avg_memory = statistics.mean(monitor.memory_samples)
            max_memory = max(monitor.memory_samples)

            print(f"平均CPU使用率: {avg_cpu:.1f}%")
            print(f"峰值CPU使用率: {max_cpu:.1f}%")
            print(f"平均內存使用率: {avg_memory:.1f}%")
            print(f"峰值內存使用率: {max_memory:.1f}%")

            # 驗證資源使用在合理範圍內
            assert max_cpu < 90.0, f"CPU使用率過高: {max_cpu}%"
            assert max_memory < 90.0, f"內存使用率過高: {max_memory}%"


class TestPerformanceBenchmarks:
    """性能基準測試"""

    @pytest.mark.benchmark
    async def test_workflow_controller_benchmark(self, performance_monitor):
        """工作流控制器基準測試"""

        controller = WorkflowController()

        # 創建基準測試計劃
        from src.autogen_system.controllers.workflow_controller import (
            WorkflowPlan,
            WorkflowStep,
            StepType,
        )

        steps = [
            WorkflowStep(
                id=f"benchmark_step_{i}",
                name=f"基準步驟 {i}",
                step_type=StepType.PROCESSING,
                description="基準測試步驟",
                dependencies=[],
                estimated_duration=1,
            )
            for i in range(50)
        ]

        plan = WorkflowPlan(
            id="benchmark_plan",
            name="基準測試計劃",
            description="用於性能基準測試",
            steps=steps,
            estimated_duration=50,
        )

        async def benchmark_executor(step, state):
            # 最小化處理時間
            state[step.id] = "completed"
            return state

        # 執行基準測試
        benchmark_runs = 5
        execution_times = []

        for run in range(benchmark_runs):
            with performance_monitor.measure(f"benchmark_run_{run}"):
                start_time = time.time()
                await controller.execute_plan(plan, {}, benchmark_executor)
                end_time = time.time()

                execution_times.append(end_time - start_time)

        # 計算基準指標
        avg_time = statistics.mean(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        std_time = statistics.stdev(execution_times) if len(execution_times) > 1 else 0

        print(f"\n=== 工作流控制器基準測試結果 ===")
        print(f"步驟數: {len(steps)}")
        print(f"運行次數: {benchmark_runs}")
        print(f"平均執行時間: {avg_time:.4f}s")
        print(f"最快執行時間: {min_time:.4f}s")
        print(f"最慢執行時間: {max_time:.4f}s")
        print(f"標準差: {std_time:.4f}s")
        print(f"步驟/秒: {len(steps) / avg_time:.1f}")

        # 基準驗證
        assert avg_time < 1.0, f"基準測試失敗：平均執行時間 {avg_time}s 超過 1s"
        assert std_time < 0.1, f"基準測試失敗：執行時間變動過大 {std_time}s"

    @pytest.mark.benchmark
    async def test_agent_throughput_benchmark(self, mock_model_client):
        """代理吞吐量基準測試"""

        from src.autogen_system.agents.coordinator_agent import CoordinatorAgent

        # 配置快速響應模擬
        mock_model_client.complete = AsyncMock(return_value="Benchmark response")

        agent = CoordinatorAgent(model_client=mock_model_client, tools=[])

        # 基準測試參數
        request_count = 100
        concurrent_batches = [1, 5, 10, 20]

        results = {}

        for batch_size in concurrent_batches:
            print(f"\n測試批次大小: {batch_size}")

            start_time = time.time()

            # 分批執行請求
            all_tasks = []
            for batch in range(0, request_count, batch_size):
                batch_tasks = []
                for i in range(batch, min(batch + batch_size, request_count)):
                    task = agent.process_request(f"Benchmark request {i}")
                    batch_tasks.append(task)

                # 執行當前批次
                await asyncio.gather(*batch_tasks)
                all_tasks.extend(batch_tasks)

            end_time = time.time()
            total_time = end_time - start_time
            throughput = request_count / total_time

            results[batch_size] = {
                "total_time": total_time,
                "throughput": throughput,
                "avg_response_time": total_time / request_count,
            }

            print(f"總時間: {total_time:.3f}s")
            print(f"吞吐量: {throughput:.1f} 請求/秒")
            print(f"平均響應時間: {total_time / request_count:.4f}s")

        # 基準驗證
        max_throughput = max(r["throughput"] for r in results.values())
        assert max_throughput > 50, f"代理吞吐量過低: {max_throughput} 請求/秒"

        print(f"\n=== 代理吞吐量基準測試總結 ===")
        print(f"最大吞吐量: {max_throughput:.1f} 請求/秒")
        print(f"最佳批次大小: {max(results.keys(), key=lambda k: results[k]['throughput'])}")
