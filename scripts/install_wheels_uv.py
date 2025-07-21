#!/usr/bin/env python3
"""
安裝預下載的 wheel 檔案的腳本
適用於離線環境部署
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None):
    """執行命令並返回結果"""
    print(f"執行: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"錯誤: {result.stderr}")
        return False
    print(f"成功: {result.stdout}")
    return True


def main():
    wheels_dir = Path("wheels")

    if not wheels_dir.exists():
        print(f"錯誤: {wheels_dir} 目錄不存在")
        return False

    # 安裝所有 wheel 檔案
    print("安裝 wheel 檔案...")
    wheel_files = list(wheels_dir.glob("*.whl"))

    if not wheel_files:
        print("沒有找到 wheel 檔案")
        return False

    # 按依賴順序安裝
    for wheel_file in wheel_files:
        if not run_command(f"uv pip install {wheel_file}"):
            print(f"安裝 {wheel_file} 失敗")
            return False

    print("所有 wheel 檔案安裝完成")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
