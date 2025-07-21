# Volcengine Wheel 手動下載指南

由於網路連線問題，以下是幾種手動獲取 volcengine wheel 檔案的方法：

## 方法一：設定代理環境變數

在執行下載腳本前，先設定代理：

```bash
# Windows
set HTTP_PROXY=http://proxy-server:port
set HTTPS_PROXY=http://proxy-server:port

# Linux/macOS
export HTTP_PROXY=http://proxy-server:port
export HTTPS_PROXY=http://proxy-server:port

# 然後執行下載
python scripts/download_volcengine_offline.py
```

## 方法二：使用國內鏡像站

### 清華大學鏡像
```bash
pip download volcengine>=1.0.191 -d wheels -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 阿里雲鏡像
```bash
pip download volcengine>=1.0.191 -d wheels -i https://mirrors.aliyun.com/pypi/simple
```

### 豆瓣鏡像
```bash
pip download volcengine>=1.0.191 -d wheels -i https://pypi.douban.com/simple
```

### 中科大鏡像
```bash
pip download volcengine>=1.0.191 -d wheels -i https://pypi.mirrors.ustc.edu.cn/simple
```

## 方法三：直接下載連結

### volcengine 1.0.191 直接下載連結：

**Source Distribution (tar.gz):**
- https://files.pythonhosted.org/packages/f4/d8/0ea9b18f216808af709306084d10369f712b98cb5381381d44115dfa6536/volcengine-1.0.191.tar.gz

**Wheel Distribution (如果可用):**
- https://files.pythonhosted.org/packages/volcengine-1.0.191-py3-none-any.whl

### 下載命令：
```bash
# 建立 wheels 目錄
mkdir -p wheels

# 下載 volcengine
curl -L -o wheels/volcengine-1.0.191.tar.gz "https://files.pythonhosted.org/packages/f4/d8/0ea9b18f216808af709306084d10369f712b98cb5381381d44115dfa6536/volcengine-1.0.191.tar.gz"

# 或使用 wget
wget -O wheels/volcengine-1.0.191.tar.gz "https://files.pythonhosted.org/packages/f4/d8/0ea9b18f216808af709306084d10369f712b98cb5381381d44115dfa6536/volcengine-1.0.191.tar.gz"
```

## 方法四：從其他機器複製

如果您有其他可以連網的機器：

1. **在有網路的機器上下載：**
```bash
pip download volcengine>=1.0.191 -d wheels
```

2. **複製到目標機器：**
```bash
# 使用 scp
scp -r wheels/ user@target-machine:/path/to/project/

# 使用 rsync
rsync -av wheels/ user@target-machine:/path/to/project/wheels/

# 使用 USB 隨身碟或其他方式
```

## 方法五：使用 Docker 容器

```bash
# 建立臨時容器來下載
docker run --rm -v $(pwd)/wheels:/wheels python:3.12-slim bash -c "
pip install --upgrade pip &&
pip download volcengine>=1.0.191 -d /wheels &&
pip download requests>=2.25.1 -d /wheels &&
pip download urllib3>=1.26.0 -d /wheels &&
pip download certifi>=2020.12.5 -d /wheels &&
pip download charset-normalizer>=2.0.0 -d /wheels &&
pip download idna>=2.10 -d /wheels
"
```

## 方法六：從 GitHub 或其他來源

如果 volcengine 有 GitHub 倉庫：

```bash
# 克隆倉庫
git clone https://github.com/volcengine/volcengine-python-sdk.git

# 建置 wheel
cd volcengine-python-sdk
python setup.py bdist_wheel

# 複製 wheel 檔案
cp dist/*.whl ../wheels/
```

## 驗證下載

下載完成後，檢查檔案：

```bash
ls -la wheels/
```

應該看到類似以下的檔案：
- volcengine-1.0.191.tar.gz
- requests-*.whl
- urllib3-*.whl
- certifi-*.whl
- charset-normalizer-*.whl
- idna-*.whl

## 安裝下載的檔案

```bash
# 安裝 volcengine
pip install wheels/volcengine-1.0.191.tar.gz

# 安裝依賴
pip install wheels/requests-*.whl
pip install wheels/urllib3-*.whl
pip install wheels/certifi-*.whl
pip install wheels/charset-normalizer-*.whl
pip install wheels/idna-*.whl
```

## 故障排除

### 代理問題
如果仍然有代理問題，嘗試：

```bash
# 暫時禁用代理
unset HTTP_PROXY
unset HTTPS_PROXY
unset http_proxy
unset https_proxy

# 或設定為空
export HTTP_PROXY=""
export HTTPS_PROXY=""
```

### 網路連線問題
```bash
# 測試網路連線
ping pypi.org
curl -I https://pypi.org

# 測試鏡像站
curl -I https://pypi.tuna.tsinghua.edu.cn/simple
```

### 權限問題
```bash
# 確保有寫入權限
chmod 755 wheels/
chmod 644 wheels/*
``` 