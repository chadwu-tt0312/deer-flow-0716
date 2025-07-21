#!/usr/bin/env python3
"""
離線下載 volcengine wheel 檔案的腳本
支援多種下載來源和代理設定
"""

import subprocess
import sys
import os
import urllib.request
import urllib.parse
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


def download_file(url, filename):
    """下載檔案"""
    try:
        print(f"下載 {url} 到 {filename}")
        urllib.request.urlretrieve(url, filename)
        return True
    except Exception as e:
        print(f"下載失敗: {e}")
        return False


def main():
    # 建立 wheels 目錄
    wheels_dir = Path("wheels")
    wheels_dir.mkdir(exist_ok=True)

    # 設定代理（如果需要）
    proxy_handler = None
    if os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        print(f"使用代理: {proxy}")
        proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)

    # volcengine wheel 的直接下載連結
    volcengine_urls = [
        "https://files.pythonhosted.org/packages/f4/d8/0ea9b18f216808af709306084d10369f712b98cb5381381d44115dfa6536/volcengine-1.0.191.tar.gz",
        "https://pypi.tuna.tsinghua.edu.cn/simple/volcengine/",
        "https://mirrors.aliyun.com/pypi/simple/volcengine/",
    ]

    # 嘗試不同的下載方法
    success = False

    # 方法1: 使用 pip 下載（帶代理）
    print("方法1: 使用 pip 下載...")
    proxy_args = ""
    if os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        proxy_args = f"--proxy {os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')}"

    download_cmd = f"pip download volcengine>=1.0.191 -d {wheels_dir} {proxy_args}".strip()
    if run_command(download_cmd):
        success = True

    # 方法2: 使用國內鏡像
    if not success:
        print("方法2: 使用國內鏡像...")
        mirrors = [
            "https://pypi.tuna.tsinghua.edu.cn/simple",
            "https://mirrors.aliyun.com/pypi/simple",
            "https://pypi.douban.com/simple",
            "https://pypi.mirrors.ustc.edu.cn/simple",
        ]

        for mirror in mirrors:
            print(f"嘗試鏡像: {mirror}")
            mirror_cmd = (
                f"pip download volcengine>=1.0.191 -d {wheels_dir} -i {mirror} {proxy_args}".strip()
            )
            if run_command(mirror_cmd):
                success = True
                break

    # 方法3: 直接下載 wheel 檔案
    if not success:
        print("方法3: 直接下載 wheel 檔案...")
        wheel_filename = wheels_dir / "volcengine-1.0.191-py3-none-any.whl"
        if download_file(volcengine_urls[0], wheel_filename):
            success = True

    # 下載依賴套件
    if success:
        print("下載依賴套件...")
        dependencies = [
            "requests>=2.25.1",
            "urllib3>=1.26.0",
            "certifi>=2020.12.5",
            "charset-normalizer>=2.0.0",
            "idna>=2.10",
        ]

        for dep in dependencies:
            dep_cmd = f"pip download {dep} -d {wheels_dir} {proxy_args}".strip()
            if not run_command(dep_cmd):
                print(f"警告: 下載 {dep} 失敗，但繼續執行")

    if success:
        print(f"所有 wheel 檔案已下載到 {wheels_dir} 目錄")
        return True
    else:
        print("所有下載方法都失敗了")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
