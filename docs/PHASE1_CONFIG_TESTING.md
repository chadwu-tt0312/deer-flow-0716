# PHASE1 配置系統測試指南

## 概述

本文檔說明如何測試驗證 PHASE1 完成後的配置系統，特別是 `conf_autogen.yaml` 配置檔案的實際載入和使用。

## 測試方法

### 1. 快速測試（推薦）

使用快速測試腳本進行基本驗證：

```bash
# 在專案根目錄執行
python scripts/quick_config_test.py
```

這個腳本會：
- ✅ 檢查配置檔案存在性
- ✅ 測試配置載入器
- ✅ 驗證 YAML 配置載入
- ✅ 測試 LLM 配置
- ✅ 驗證智能體配置
- ✅ 測試工作流配置
- ✅ 檢查工具配置
- ✅ 驗證安全配置

### 2. 完整測試

使用完整驗證腳本進行詳細測試：

```bash
# 在專案根目錄執行
python scripts/verify_config_system.py
```

這個腳本提供：
- 🔍 詳細的配置檢查
- 📊 驗證結果摘要
- ⚠️ 問題診斷和建議
- 🎯 端到端配置整合測試

### 3. 單元測試

運行 pytest 單元測試：

```bash
# 運行配置系統測試
python -m pytest tests/autogen_system/unit/test_config_system.py -v

# 運行所有配置相關測試
python -m pytest tests/unit/config/ -v
```

## 測試內容詳解

### 3.1 配置檔案驗證

#### 檔案存在性檢查
- 確認 `conf_autogen.yaml` 檔案存在
- 檢查檔案大小和可讀性

#### YAML 語法檢查
- 驗證 YAML 格式正確性
- 檢查語法錯誤和格式問題

#### 配置結構檢查
- 驗證必要配置區段存在
- 檢查 `autogen`、`agents`、`workflows`、`tools` 等區段

### 3.2 LLM 配置驗證

#### 基本配置檢查
- 模型名稱設定
- 溫度參數
- 最大 token 數量
- 超時設定

#### 環境變數覆蓋
- API Key 設定
- Base URL 設定
- 環境變數優先級

### 3.3 智能體配置驗證

#### 必要智能體檢查
- `coordinator`: 協調者
- `planner`: 計劃者
- `researcher`: 研究者
- `coder`: 程式設計師
- `reporter`: 報告者

#### 配置完整性
- 系統訊息設定
- 角色定義
- 工具配置
- LLM 配置覆蓋

### 3.4 工作流配置驗證

#### 研究工作流
- 智能體組合
- 工作流類型
- 迭代次數設定
- 人機互動配置

#### 配置整合
- 智能體配置關聯
- 工作流執行參數
- 群組對話設定

### 3.5 工具配置驗證

#### 主要工具
- `web_search`: 網路搜尋
- `code_execution`: 程式碼執行
- `mcp_servers`: MCP 伺服器

#### 工具參數
- 提供者設定
- 超時配置
- 安全限制

### 3.6 安全配置驗證

#### 安全設定
- 程式碼執行開關
- 沙盒模式
- 檔案類型限制
- 檔案大小限制

## 測試腳本使用

### 快速測試腳本

```python
# scripts/quick_config_test.py
def test_config_loading():
    """測試配置載入"""
    # 基本配置檢查
    
def test_config_usage():
    """測試配置使用"""
    # 配置實際應用測試
```

### 完整驗證腳本

```python
# scripts/verify_config_system.py
class ConfigSystemVerifier:
    def verify_config_file_exists(self) -> bool:
        # 檔案存在性檢查
        
    def verify_yaml_syntax(self) -> bool:
        # YAML 語法檢查
        
    def verify_config_structure(self) -> bool:
        # 配置結構檢查
        
    def verify_llm_config(self) -> bool:
        # LLM 配置檢查
        
    def verify_agents_config(self) -> bool:
        # 智能體配置檢查
        
    def verify_workflows_config(self) -> bool:
        # 工作流配置檢查
        
    def verify_tools_config(self) -> bool:
        # 工具配置檢查
        
    def verify_security_config(self) -> bool:
        # 安全配置檢查
        
    def verify_environment_variables(self) -> bool:
        # 環境變數檢查
        
    def verify_config_integration(self) -> bool:
        # 配置整合檢查
```

## 預期測試結果

### 成功情況

```
🚀 開始 PHASE1 配置系統驗證
==================================================
🔍 檢查配置檔案...
✅ 配置檔案存在: /path/to/conf_autogen.yaml
   檔案大小: 1234 bytes

🔍 檢查 YAML 語法...
✅ YAML 語法正確

🔍 檢查配置結構...
✅ 配置結構完整
   主要區段: ['autogen', 'agents', 'workflows', 'tools']
✅ autogen 區段完整

🔍 檢查 LLM 配置...
✅ LLM 配置載入成功
   模型: gpt-4o-mini
   溫度: 0.2
   最大 token: 1000
   超時: 30

🔍 檢查智能體配置...
✅ 找到 5 個智能體配置
✅ 所有必要智能體都已配置
   ✅ coordinator: CoordinatorAgent (coordinator)
      系統訊息: 你是協調者，負責管理整個研究工作流程。...
      工具數量: 0
   ✅ planner: PlannerAgent (planner)
      系統訊息: 你是計劃者，負責分析需求並制定詳細的執行計劃。...
      工具數量: 0
   ✅ researcher: ResearcherAgent (researcher)
      系統訊息: 你是研究員，負責進行網路搜尋和資訊收集。...
      工具數量: 3
   ✅ coder: CoderAgent (coder)
      系統訊息: 你是程式設計師，負責程式碼分析和執行。...
      工具數量: 1
   ✅ reporter: ReporterAgent (reporter)
      系統訊息: 你是報告撰寫者，負責整理資訊並生成最終報告。...
      工具數量: 0

🔍 檢查工作流配置...
✅ 研究工作流配置載入成功
   名稱: research
   類型: research
   智能體數量: 5
     1. CoordinatorAgent (coordinator)
     2. PlannerAgent (planner)
     3. ResearcherAgent (researcher)
     4. CoderAgent (coder)
     5. ReporterAgent (reporter)

🔍 檢查工具配置...
✅ 工具配置完整
   ✅ web_search: 已配置
   ✅ code_execution: 已配置
   ✅ mcp_servers: 已配置
   🔍 web_search 提供者: tavily
   🔍 最大結果數: 5

🔍 檢查安全配置...
✅ 安全配置載入成功
   程式碼執行: True
   沙盒模式: True
   允許的檔案類型: ['.py', '.txt', '.md', '.json', '.csv']
   最大檔案大小: 10 MB

🔍 檢查環境變數...
   ⚠️  OPENAI_API_KEY: 未設定 (OpenAI API 金鑰)
   ⚠️  OPENAI_BASE_URL: 未設定 (OpenAI 基礎 URL)
⚠️  建議設定環境變數: ['OPENAI_API_KEY', 'OPENAI_BASE_URL]
   注意: 這些變數可以在 conf_autogen.yaml 中設定，或通過環境變數覆蓋

🔍 檢查配置整合...
✅ 配置整合檢查通過
   工作流智能體數量: 5

==================================================
📊 驗證結果摘要
==================================================
配置檔案存在性 : ✅ 通過
YAML 語法      : ✅ 通過
配置結構       : ✅ 通過
LLM 配置       : ✅ 通過
智能體配置     : ✅ 通過
工作流配置     : ✅ 通過
工具配置       : ✅ 通過
安全配置       : ✅ 通過
環境變數       : ✅ 通過
配置整合       : ✅ 通過
==================================================
總計: 10/10 項驗證通過
🎉 所有驗證都通過！配置系統正常運作。
```

### 失敗情況

如果測試失敗，腳本會顯示具體的錯誤信息：

```
❌ 配置結構檢查失敗: 缺少必要配置區段: ['workflows']
❌ 智能體配置載入失敗: 找不到智能體配置: researcher
❌ 工作流配置載入失敗: 智能體 researcher 缺少 LLM 配置
```

## 問題診斷

### 常見問題

#### 1. 配置檔案不存在
```
❌ 配置檔案不存在: /path/to/conf_autogen.yaml
```
**解決方案：**
- 確認檔案路徑正確
- 檢查檔案權限
- 複製 `conf_autogen.yaml.example` 為 `conf_autogen.yaml`

#### 2. YAML 語法錯誤
```
❌ YAML 語法錯誤: expected <block end>, but found '<scalar>'
```
**解決方案：**
- 檢查 YAML 縮排
- 驗證冒號和空格
- 使用 YAML 驗證工具

#### 3. 缺少配置區段
```
❌ 缺少必要配置區段: ['agents']
```
**解決方案：**
- 檢查 YAML 檔案結構
- 確認區段名稱拼寫
- 參考範例檔案

#### 4. 智能體配置錯誤
```
❌ 智能體 coordinator 配置載入失敗: 無效的角色值
```
**解決方案：**
- 檢查角色名稱拼寫
- 確認角色值在 `AgentRole` 枚舉中定義
- 參考 `agent_config.py` 中的定義

### 調試建議

1. **逐步測試**：先運行快速測試，再進行完整驗證
2. **檢查日誌**：查看詳細的錯誤信息和堆疊追蹤
3. **對比範例**：與 `conf_autogen.yaml.example` 進行對比
4. **環境檢查**：確認 Python 環境和依賴正確安裝

## 下一步

配置系統驗證通過後，可以：

1. **進入 PHASE2**：開始實現核心智能體
2. **運行工作流測試**：測試完整的智能體協作
3. **整合測試**：驗證整個系統的端到端功能

## 總結

PHASE1 的配置系統測試是確保整個 AutoGen 遷移項目成功的關鍵步驟。通過這些測試，我們可以：

- ✅ 確認配置檔案的正確性
- ✅ 驗證配置載入器的功能
- ✅ 測試智能體和工作流配置
- ✅ 確保系統的穩定性和可靠性

只有配置系統驗證通過，我們才能有信心進入下一階段的開發工作。
