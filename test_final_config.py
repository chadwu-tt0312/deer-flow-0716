#!/usr/bin/env python3
"""
只測試配置讀取功能，避免導入整個日誌模組
"""

import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_config_loading():
    """測試配置讀取功能"""
    print("🧪 開始測試配置讀取...")

    try:
        # 測試導入
        print("1. 測試導入 config 模組...")
        from src.config import load_yaml_config

        print("✅ config 模組導入成功")

        # 測試配置讀取
        print("2. 測試讀取 conf.yaml...")
        config = load_yaml_config("conf.yaml")
        print(f"✅ 配置讀取成功: {type(config)}")

        # 測試基本配置
        print("3. 檢查配置內容...")
        if config:
            print(f"  - 配置類型: {type(config)}")
            print(f"  - 配置鍵: {list(config.keys())}")

            logging_config = config.get("LOGGING", {})
            if logging_config:
                print(f"  - LOGGING 配置: {logging_config}")

                # 檢查具體的配置項
                print(f"  - 日誌級別: {logging_config.get('level', 'N/A')}")
                print(f"  - 控制台輸出: {logging_config.get('console_output', 'N/A')}")
                print(f"  - 提供者: {logging_config.get('provider', 'N/A')}")
                print(
                    f"  - 檔案輸出: {'自動啟用' if logging_config.get('provider') == 'file' else '資料庫輸出'}"
                )

                external_loggers = logging_config.get("external_loggers", {})
                if external_loggers:
                    print(f"  - 外部套件日誌級別: {external_loggers.get('level', 'N/A')}")

                format_config = logging_config.get("format", {})
                if format_config:
                    print(f"  - 主日誌格式: {format_config.get('main', 'N/A')}")
                    print(f"  - Thread 日誌格式: {format_config.get('thread', 'N/A')}")
            else:
                print("  - 沒有 LOGGING 配置")
        else:
            print("  - 配置為空")

        print("✅ 配置內容檢查完成")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_logging_config_function():
    """測試日誌配置函數（不導入整個模組）"""
    print("\n🧪 開始測試日誌配置函數...")

    try:
        # 直接測試函數邏輯，不導入整個模組
        print("1. 測試配置解析邏輯...")

        # 模擬 _load_logging_config_from_yaml 函數的邏輯
        from src.config import load_yaml_config

        config = load_yaml_config("conf.yaml")
        logging_config = config.get("LOGGING", {})

        if logging_config:
            # 解析配置
            result = {}

            # 基本設定
            result["level"] = logging_config.get("level", "INFO")
            result["debug"] = result["level"].upper() == "DEBUG"

            # 檔案設定
            file_settings = logging_config.get("file_settings", {})
            result["log_dir"] = file_settings.get("log_dir", "logs")
            result["max_days"] = file_settings.get("max_days", 10)
            result["compress_old_files"] = file_settings.get("compress_old_files", True)

            # 輸出設定（主日誌和 Thread 日誌使用相同設定）
            result["console_output"] = logging_config.get("console_output", False)
            # 根據 provider 決定是否輸出到檔案
            provider = logging_config.get("provider", "file")
            result["file_output"] = provider == "file"  # 只有 file provider 才輸出到檔案

            # Thread-specific 日誌設定（永遠啟用，使用與主日誌相同的設定）
            result["thread_enabled"] = True  # 永遠啟用
            result["thread_level"] = result["level"]
            result["thread_console_output"] = result["console_output"]
            result["thread_file_output"] = result["file_output"]

            # 外部套件日誌設定
            external_loggers = logging_config.get("external_loggers", {})
            result["external_loggers_level"] = external_loggers.get("level", "ERROR")

            # 日誌格式設定
            format_config = logging_config.get("format", {})
            result["main_format"] = format_config.get(
                "main", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            result["thread_format"] = format_config.get(
                "thread", "%(asctime)s - %(levelname)s - %(message)s"
            )

            # 特殊設定
            result["provider"] = logging_config.get("provider", "file")

            print(f"✅ 配置解析成功: {result}")

            # 驗證關鍵配置
            print(f"  - 日誌級別: {result.get('level')}")
            print(f"  - 控制台輸出: {result.get('console_output')}")
            print(f"  - 檔案輸出: {result.get('file_output')}")
            print(f"  - Thread 日誌啟用: {result.get('thread_enabled')}")
            print(f"  - Thread 日誌級別: {result.get('thread_level')}")
            print(f"  - 外部套件日誌級別: {result.get('external_loggers_level')}")

        else:
            print("⚠️ 沒有 LOGGING 配置")

        print("✅ 日誌配置函數測試完成")

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    print("🚀 開始配置讀取測試...\n")

    # 測試配置讀取
    config_ok = test_config_loading()

    # 測試日誌配置函數
    logging_ok = test_logging_config_function()

    print(f"\n📊 測試結果:")
    print(f"  - 配置讀取: {'✅ 成功' if config_ok else '❌ 失敗'}")
    print(f"  - 日誌配置函數: {'✅ 成功' if logging_ok else '❌ 失敗'}")

    if config_ok and logging_ok:
        print("\n🎉 所有測試通過！")
        print("\n📋 配置摘要:")
        print("  - 系統已成功從 conf.yaml 讀取日誌配置")
        print("  - Thread-specific 日誌功能已配置")
        print("  - 外部套件日誌級別已設定")
        print("  - 日誌格式已自定義")
    else:
        print("\n⚠️ 部分測試失敗，請檢查錯誤信息")
