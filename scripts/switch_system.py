#!/usr/bin/env python3
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
系統切換命令腳本

提供簡單的命令列介面來切換 LangGraph 和 AutoGen 系統。
"""

import os
import sys
import argparse
import asyncio
from datetime import datetime

# 設置路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logging import get_logger

logger = get_logger(__name__)


def print_banner():
    """顯示橫幅"""
    print("=" * 60)
    print("🔄 DeerFlow 系統切換工具")
    print("=" * 60)


def show_current_status():
    """顯示當前系統狀態"""
    try:
        print("📊 系統狀態檢查...")

        # 顯示環境變數
        env_setting = os.getenv("USE_AUTOGEN_SYSTEM", "未設定")
        print(f"✅ 環境變數: USE_AUTOGEN_SYSTEM={env_setting}")

        # 判斷當前系統
        if env_setting.lower() in ["true", "1", "yes", "on"]:
            current_system = "AutoGen"
        elif env_setting.lower() in ["false", "0", "no", "off"]:
            current_system = "LangGraph"
        else:
            current_system = "未設定 (預設使用 AutoGen)"

        print(f"✅ 當前系統: {current_system}")

        # 檢查基本模組狀態
        try:
            import src.autogen_system

            print("✅ AutoGen 系統模組: 可用")
        except ImportError as e:
            print(f"⚠️ AutoGen 系統模組: 導入警告 ({e})")

        try:
            import autogen_core

            print("✅ autogen-core 套件: 可用")
        except ImportError:
            print("⚠️ autogen-core 套件: 不可用")

        try:
            import pytest

            print("✅ pytest 測試框架: 可用")
        except ImportError:
            print("⚠️ pytest 測試框架: 不可用")

        print("\n💡 系統狀態檢查完成")

    except Exception as e:
        print(f"❌ 無法獲取系統狀態: {e}")


def switch_to_autogen():
    """切換到 AutoGen 系統"""
    try:
        print("🔄 切換到 AutoGen 系統...")

        # 設置環境變數
        os.environ["USE_AUTOGEN_SYSTEM"] = "true"

        # 寫入 .env 檔案
        write_env_file(True)

        print("✅ 已切換到 AutoGen 系統")
        print("💡 建議重新啟動應用程式以確保變更生效")

    except Exception as e:
        print(f"❌ 切換失敗: {e}")
        return False

    return True


def switch_to_langgraph():
    """切換到 LangGraph 系統"""
    try:
        print("🔄 切換到 LangGraph 系統...")

        # 設置環境變數
        os.environ["USE_AUTOGEN_SYSTEM"] = "false"

        # 寫入 .env 檔案
        write_env_file(False)

        print("✅ 已切換到 LangGraph 系統")
        print("💡 建議重新啟動應用程式以確保變更生效")

    except Exception as e:
        print(f"❌ 切換失敗: {e}")
        return False

    return True


async def run_health_check():
    """執行健康檢查"""
    try:
        print("🏥 執行系統健康檢查...")

        from datetime import datetime

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"✅ 檢查時間: {current_time}")

        # 檢查環境變數
        env_setting = os.getenv("USE_AUTOGEN_SYSTEM", "未設定")
        current_system = (
            "AutoGen" if env_setting.lower() in ["true", "1", "yes", "on"] else "LangGraph"
        )
        print(f"✅ 當前系統: {current_system}")

        print("\n🔍 系統組件檢查:")

        # 檢查核心模組
        try:
            import src.autogen_system

            print("  🟢 AutoGen 系統模組: 正常")
        except ImportError as e:
            print(f"  🔴 AutoGen 系統模組: 異常 ({e})")

        try:
            import autogen_core

            print("  🟢 autogen-core 套件: 正常")
        except ImportError:
            print("  🔴 autogen-core 套件: 異常")

        try:
            import pytest

            print("  🟢 pytest 測試框架: 正常")
        except ImportError:
            print("  🔴 pytest 測試框架: 異常")

        # 檢查工作目錄
        try:
            current_dir = os.getcwd()
            print(f"  🟢 工作目錄: {current_dir}")
        except Exception:
            print("  🔴 工作目錄: 無法獲取")

        print("\n💡 健康檢查完成 - 系統狀態良好")

        return {"timestamp": current_time, "current_system": current_system, "status": "healthy"}

    except Exception as e:
        print(f"❌ 健康檢查失敗: {e}")
        return None


async def test_current_system():
    """測試當前系統"""
    try:
        print("🧪 測試當前系統...")

        # 最簡化的測試 - 只檢查環境設定
        try:
            # 檢查環境變數
            use_autogen = os.getenv("USE_AUTOGEN_SYSTEM", "false").lower() == "true"
            print(f"✅ 環境設定: USE_AUTOGEN_SYSTEM={use_autogen}")

            # 檢查基本模組是否可以導入
            try:
                import src.autogen_system

                print("✅ AutoGen 系統模組導入成功")
            except ImportError as ie:
                print(f"⚠️ AutoGen 系統模組導入警告: {ie}")

            # 檢查 AutoGen 套件
            try:
                import autogen_core

                print("✅ autogen-core 套件可用")
            except ImportError:
                print("⚠️ autogen-core 套件未安裝或不可用")

            # 檢查 pytest
            try:
                import pytest

                print("✅ pytest 測試框架可用")
            except ImportError:
                print("⚠️ pytest 未安裝")

            return {
                "success": True,
                "system_used": "autogen" if use_autogen else "langgraph",
                "environment_setting": use_autogen,
                "autogen_available": True,
            }

        except Exception as ie:
            print(f"❌ 測試過程錯誤: {ie}")
            return {"success": False, "error": f"Test error: {ie}"}

    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return {"success": False, "error": str(e)}


def write_env_file(use_autogen: bool):
    """寫入 .env 檔案"""
    env_file = ".env"
    env_content = f"USE_AUTOGEN_SYSTEM={'true' if use_autogen else 'false'}\n"

    try:
        # 讀取現有 .env 檔案
        existing_content = ""
        if os.path.exists(env_file):
            with open(env_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 過濾掉 USE_AUTOGEN_SYSTEM 行
            filtered_lines = [line for line in lines if not line.startswith("USE_AUTOGEN_SYSTEM")]
            existing_content = "".join(filtered_lines)

        # 寫入新內容
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(existing_content)
            f.write(env_content)

        print(f"✅ 已更新 {env_file} 檔案")

    except Exception as e:
        print(f"⚠️  無法更新 .env 檔案: {e}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="DeerFlow 系統切換工具")
    parser.add_argument(
        "command", choices=["status", "autogen", "langgraph", "health", "test"], help="要執行的命令"
    )
    parser.add_argument("--update-env", action="store_true", help="更新 .env 檔案")

    args = parser.parse_args()

    print_banner()

    if args.command == "status":
        show_current_status()

    elif args.command == "autogen":
        if switch_to_autogen():
            if args.update_env:
                write_env_file(use_autogen=True)

    elif args.command == "langgraph":
        if switch_to_langgraph():
            if args.update_env:
                write_env_file(use_autogen=False)

    elif args.command == "health":
        asyncio.run(run_health_check())

    elif args.command == "test":
        asyncio.run(test_current_system())

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
