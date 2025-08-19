# AutoGen性能測試報告

**測試時間**: 2025-08-15 00:03:49

## 📊 性能摘要
- **平均內存使用**: 29.1MB
- **平均CPU使用**: 3.5%
- **平均線程數**: 6

## ⏱️ 延遲摘要
- **cpu_intensive**: 1.002s
- **memory_intensive**: 0.605s
- **io_operation_0**: 0.141s
- **io_operation_2**: 0.141s
- **io_operation_1**: 0.141s
- **io_operation_4**: 0.226s
- **io_operation_3**: 0.273s
- **io_intensive**: 0.273s
- **light_io_io_0**: 0.087s
- **light_cpu_cpu_1**: 0.120s
- **light_cpu_cpu_0**: 0.120s
- **light_cpu_cpu_2**: 0.120s
- **light_io_io_2**: 0.120s
- **light_io_io_1**: 0.120s

## 🔧 已應用優化
- 垃圾回收: 釋放了 116 個對象
- 對象數量: 19721 -> 19590
- 調整垃圾回收閾值以更頻繁清理
- 建議線程池大小: 32 (基於 16 核CPU)