#!/usr/bin/env python3
"""
使用 Docker 建置 volcengine wheel 檔案的腳本
適用於跨平台 wheel 建置
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


def create_dockerfile():
    """建立 Dockerfile 來建置 wheel"""
    dockerfile_content = """FROM python:3.12-slim

WORKDIR /app

# 安裝建置工具
RUN pip install --upgrade pip wheel setuptools

# 複製 requirements
COPY requirements.txt .

# 下載 wheel 檔案
RUN pip download volcengine>=1.0.191 -d /wheels
RUN pip download requests>=2.25.1 -d /wheels
RUN pip download urllib3>=1.26.0 -d /wheels
RUN pip download certifi>=2020.12.5 -d /wheels
RUN pip download charset-normalizer>=2.0.0 -d /wheels
RUN pip download idna>=2.10 -d /wheels

# 設定 volume 來分享 wheel 檔案
VOLUME /wheels
"""

    with open("Dockerfile.wheels", "w") as f:
        f.write(dockerfile_content)


def main():
    # 建立 wheels 目錄
    wheels_dir = Path("wheels")
    wheels_dir.mkdir(exist_ok=True)

    # 建立 Dockerfile
    create_dockerfile()

    # 建立 requirements.txt
    with open("requirements.txt", "w") as f:
        f.write("volcengine>=1.0.191\n")

    # 建置 Docker 映像
    print("建置 Docker 映像...")
    if not run_command("docker build -f Dockerfile.wheels -t volcengine-wheels ."):
        print("建置 Docker 映像失敗")
        return False

    # 執行容器來下載 wheel
    print("下載 wheel 檔案...")
    if not run_command(f"docker run --rm -v {wheels_dir.absolute()}:/wheels volcengine-wheels"):
        print("下載 wheel 檔案失敗")
        return False

    # 清理臨時檔案
    os.remove("Dockerfile.wheels")
    os.remove("requirements.txt")

    print(f"所有 wheel 檔案已下載到 {wheels_dir} 目錄")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
