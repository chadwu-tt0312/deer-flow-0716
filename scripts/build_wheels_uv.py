#!/usr/bin/env python3
"""
使用 uv 下載並建置 volcengine wheel 檔案的腳本
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
    # 建立 wheels 目錄
    wheels_dir = Path("wheels")
    wheels_dir.mkdir(exist_ok=True)

    # 使用 uv 下載 volcengine wheel
    print("使用 uv 下載 volcengine wheel...")
    if not run_command(f"uv pip download volcengine>=1.0.191 -d {wheels_dir}"):
        print("下載 volcengine wheel 失敗")
        return False

    # 下載依賴的 wheel
    print("下載 volcengine 依賴的 wheel...")
    dependencies = [
        "requests>=2.25.1",
        "urllib3>=1.26.0",
        "certifi>=2020.12.5",
        "charset-normalizer>=2.0.0",
        "idna>=2.10",
    ]

    for dep in dependencies:
        if not run_command(f"uv pip download {dep} -d {wheels_dir}"):
            print(f"下載 {dep} 失敗")
            return False

    print(f"所有 wheel 檔案已下載到 {wheels_dir} 目錄")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
