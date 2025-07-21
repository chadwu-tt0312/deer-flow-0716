# Volcengine Wheel 部署指南

本指南說明如何將 volcengine package 預編譯成 wheel 檔案，並在其他電腦上進行離線安裝。

## 方法一：使用 pip 下載 wheel

### 在有網路連線的環境中

1. **下載 wheel 檔案**：
```bash
# 使用 Makefile
make build-wheels

# 或直接執行腳本
python scripts/build_wheels.py
```

2. **檢查下載的檔案**：
```bash
ls -la wheels/
```

### 在離線環境中安裝

1. **複製 wheels 目錄到目標機器**：
```bash
# 將整個 wheels 目錄複製到目標機器
scp -r wheels/ user@target-machine:/path/to/project/
```

2. **安裝 wheel 檔案**：
```bash
# 使用 Makefile
make install-wheels

# 或直接執行腳本
python scripts/install_wheels.py
```

## 方法二：使用 uv 下載 wheel

### 在有網路連線的環境中

```bash
python scripts/build_wheels_uv.py
```

### 在離線環境中安裝

```bash
# 使用 uv 安裝
uv pip install wheels/*.whl
```

## 方法三：使用 Docker 建置 wheel

### 在有網路連線的環境中

```bash
python scripts/build_wheels_docker.py
```

### 在離線環境中安裝

```bash
python scripts/install_wheels.py
```

## 驗證安裝

安裝完成後，可以驗證 volcengine 是否正確安裝：

```python
import volcengine
print(volcengine.__version__)
```

## 注意事項

1. **平台相容性**：wheel 檔案是平台特定的，確保在相同平台（作業系統、Python 版本、架構）上建置和安裝。

2. **依賴關係**：volcengine 依賴以下套件：
   - requests>=2.25.1
   - urllib3>=1.26.0
   - certifi>=2020.12.5
   - charset-normalizer>=2.0.0
   - idna>=2.10

3. **版本相容性**：確保下載的 wheel 版本與專案需求相符（>=1.0.191）。

4. **網路配置**：如果目標環境有特殊的網路配置，可能需要額外的設定。

## 故障排除

### 常見問題

1. **版本不相容**：
   ```bash
   # 檢查已安裝的版本
   pip show volcengine
   ```

2. **依賴缺失**：
   ```bash
   # 手動安裝缺失的依賴
   pip install wheels/requests-*.whl
   pip install wheels/urllib3-*.whl
   ```

3. **權限問題**：
   ```bash
   # 使用 sudo 安裝（Linux/macOS）
   sudo python scripts/install_wheels.py
   ```

### 日誌檢查

如果安裝失敗，檢查以下日誌：
- pip 安裝日誌
- Python 錯誤訊息
- 系統權限日誌

## 進階配置

### 自訂 wheel 目錄

可以修改腳本中的 `wheels_dir` 變數來指定不同的目錄：

```python
wheels_dir = Path("/custom/path/to/wheels")
```

### 批次處理多個套件

可以擴展腳本來處理多個套件：

```python
packages = [
    "volcengine>=1.0.191",
    "requests>=2.25.1",
    # 其他套件...
]
```

### 自動化部署腳本

可以建立自動化腳本來處理整個部署流程：

```bash
#!/bin/bash
# deploy.sh
python scripts/build_wheels.py
rsync -av wheels/ target-machine:/path/to/project/
ssh target-machine "cd /path/to/project && python scripts/install_wheels.py"
``` 