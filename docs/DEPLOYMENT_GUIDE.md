# AutoGen系統部署指南

**版本**: 1.0.0  
**更新時間**: 2025-01-08  

## 📋 概述

本指南提供AutoGen系統的完整部署流程，包括環境準備、安裝配置、服務啟動和運維監控。

## 🎯 部署架構

### 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer                          │
│                    (Nginx/HAProxy)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
              ┌───────┴───────┐
              │               │
              ▼               ▼
    ┌─────────────────┐ ┌─────────────────┐
    │  AutoGen App 1  │ │  AutoGen App 2  │
    │  (Port 8000)    │ │  (Port 8001)    │
    └─────────────────┘ └─────────────────┘
              │               │
              └───────┬───────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │     Shared Services     │
         │ ┌─────────┐ ┌─────────┐ │
         │ │ Redis   │ │ MongoDB │ │
         │ │ (Cache) │ │ (Logs)  │ │
         │ └─────────┘ └─────────┘ │
         └─────────────────────────┘
```

### 🔧 部署選項

1. **🚀 開發環境** - 單機部署，快速開始
2. **🏢 生產環境** - 高可用集群部署
3. **☁️ 雲原生** - Docker + Kubernetes部署
4. **🐳 容器化** - Docker Compose部署

## 📋 系統要求

### 🖥️ 硬件要求

| 環境 | CPU | 內存 | 存儲 | 網絡 |
|------|-----|------|------|------|
| **開發** | 2核+ | 4GB+ | 10GB+ | 100Mbps+ |
| **測試** | 4核+ | 8GB+ | 50GB+ | 1Gbps+ |
| **生產** | 8核+ | 16GB+ | 100GB+ | 1Gbps+ |

### 💿 軟件要求

- **作業系統**: Linux (Ubuntu 20.04+), macOS (12+), Windows (10+)
- **Python**: 3.12+
- **Node.js**: 18+ (前端部署需要)
- **數據庫**: PostgreSQL 13+ (可選)
- **緩存**: Redis 6+ (推薦)
- **Web服務器**: Nginx 1.20+ (生產環境)

## 🚀 快速部署

### 1. 🛠️ 環境準備

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝基礎依賴
sudo apt install -y python3.12 python3.12-pip python3.12-venv git curl

# 創建虛擬環境
python3.12 -m venv autogen_env
source autogen_env/bin/activate

# 升級pip
pip install --upgrade pip setuptools wheel
```

### 2. 📦 下載和安裝

```bash
# 克隆項目
git clone <repository-url> autogen-system
cd autogen-system

# 安裝Python依賴
pip install -r requirements.txt

# 安裝開發依賴 (可選)
pip install -r requirements-dev.txt
```

### 3. ⚙️ 基礎配置

```bash
# 複製配置模板
cp conf_autogen.yaml.example conf_autogen.yaml

# 設置環境變量
export OPENAI_API_KEY="your-openai-api-key"
export TAVILY_API_KEY="your-tavily-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# 或創建 .env 文件
cat > .env << EOF
OPENAI_API_KEY=your-openai-api-key
TAVILY_API_KEY=your-tavily-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
ENVIRONMENT=development
LOG_LEVEL=INFO
EOF
```

### 4. 🧪 驗證安裝

```bash
# 運行測試套件
make test-unit

# 運行性能演示
python tests/autogen_system/performance_demo_standalone.py

# 檢查系統狀態
python -c "
from src.autogen_system.controllers import create_conversation_manager
print('✅ AutoGen系統安裝成功!')
"
```

### 5. 🚀 啟動服務

```bash
# 開發模式啟動
python -m src.server.autogen_app

# 或使用 uvicorn
uvicorn src.server.autogen_app:app --host 0.0.0.0 --port 8000 --reload

# 服務啟動後訪問
curl http://localhost:8001/api/system/status
```

## 🏢 生產環境部署

### 📝 部署清單

- [ ] 服務器環境準備
- [ ] 依賴安裝和配置
- [ ] 數據庫設置 (可選)
- [ ] 緩存系統設置 (推薦)
- [ ] Web服務器配置
- [ ] SSL證書配置
- [ ] 監控系統設置
- [ ] 日誌系統配置
- [ ] 備份策略實施
- [ ] 安全措施配置

### 1. 🔧 系統配置

#### 創建服務用戶
```bash
# 創建專用用戶
sudo useradd -r -s /bin/false autogen
sudo mkdir -p /opt/autogen
sudo chown autogen:autogen /opt/autogen
```

#### 部署應用
```bash
# 切換到部署目錄
cd /opt/autogen

# 克隆應用
sudo -u autogen git clone <repository-url> app
cd app

# 創建虛擬環境
sudo -u autogen python3.12 -m venv venv
sudo -u autogen venv/bin/pip install -r requirements.txt
```

#### 生產配置
```bash
# 創建生產配置
sudo -u autogen cp conf_autogen.yaml.example conf_autogen.yaml

# 編輯配置文件
sudo -u autogen vim conf_autogen.yaml
```

生產配置示例 (`conf_autogen.yaml`):
```yaml
# 生產環境配置
environment: production
debug: false

# 模型配置
models:
  default:
    type: "openai"
    model: "gpt-4"
    api_key: "${OPENAI_API_KEY}"
    timeout: 30
    max_retries: 3

# 服務配置
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  max_connections: 1000

# 日誌配置
logging:
  level: "INFO"
  format: "json"
  file: "/var/log/autogen/app.log"
  max_size: "100MB"
  backup_count: 10

# 性能配置
performance:
  enable_monitoring: true
  metrics_collection_interval: 1.0
  max_concurrent_workflows: 100

# 緩存配置
cache:
  type: "redis"
  host: "localhost"
  port: 6379
  db: 0
  ttl: 3600

# 安全配置
security:
  api_key_required: true
  rate_limiting:
    enabled: true
    requests_per_minute: 100
  cors:
    enabled: true
    allowed_origins:
      - "https://yourdomain.com"
```

### 2. 🗄️ 數據庫設置 (可選)

```bash
# 安裝PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 創建數據庫和用戶
sudo -u postgres psql << EOF
CREATE DATABASE autogen_db;
CREATE USER autogen_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE autogen_db TO autogen_user;
\q
EOF

# 配置連接
echo "DATABASE_URL=postgresql://autogen_user:secure_password@localhost/autogen_db" >> .env
```

### 3. ⚡ Redis設置 (推薦)

```bash
# 安裝Redis
sudo apt install -y redis-server

# 配置Redis
sudo vim /etc/redis/redis.conf
# 修改以下配置:
# bind 127.0.0.1
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# 啟動Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 測試連接
redis-cli ping
```

### 4. 🌐 Nginx配置

```bash
# 安裝Nginx
sudo apt install -y nginx

# 創建配置文件
sudo vim /etc/nginx/sites-available/autogen
```

Nginx配置 (`/etc/nginx/sites-available/autogen`):
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL配置
    ssl_certificate /etc/ssl/certs/autogen.crt;
    ssl_certificate_key /etc/ssl/private/autogen.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # 安全頭
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=63072000" always;
    
    # 上傳大小限制
    client_max_body_size 10M;
    
    # 主要代理配置
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # 超時配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 靜態文件
    location /static/ {
        alias /opt/autogen/app/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    
    # 健康檢查
    location /health {
        proxy_pass http://127.0.0.1:8001/api/system/status;
        access_log off;
    }
}
```

```bash
# 啟用配置
sudo ln -s /etc/nginx/sites-available/autogen /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. 🔐 SSL證書

#### 使用Let's Encrypt (推薦)
```bash
# 安裝Certbot
sudo apt install -y certbot python3-certbot-nginx

# 獲取證書
sudo certbot --nginx -d yourdomain.com

# 自動續期
sudo crontab -e
# 添加以下行:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 或使用自簽名證書 (測試環境)
```bash
# 創建自簽名證書
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/autogen.key \
    -out /etc/ssl/certs/autogen.crt
```

### 6. 🔧 Systemd服務

創建服務文件 (`/etc/systemd/system/autogen.service`):
```ini
[Unit]
Description=AutoGen AI Workflow System
After=network.target

[Service]
Type=exec
User=autogen
Group=autogen
WorkingDirectory=/opt/autogen/app
Environment="PATH=/opt/autogen/app/venv/bin"
EnvironmentFile=/opt/autogen/app/.env
ExecStart=/opt/autogen/app/venv/bin/uvicorn src.server.autogen_app:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=3

# 安全設置
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/autogen/app /var/log/autogen /tmp

[Install]
WantedBy=multi-user.target
```

```bash
# 啟動服務
sudo systemctl daemon-reload
sudo systemctl start autogen
sudo systemctl enable autogen

# 檢查狀態
sudo systemctl status autogen
```

## 🐳 Docker部署

### 📦 Dockerfile

創建 `Dockerfile`:
```dockerfile
FROM python:3.12-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴文件
COPY requirements.txt .

# 安裝Python依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 創建非root用戶
RUN useradd -r -u 1001 autogen && \
    chown -R autogen:autogen /app

USER autogen

# 暴露端口
EXPOSE 8000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/system/status || exit 1

# 啟動命令
CMD ["uvicorn", "src.server.autogen_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 🐙 Docker Compose

創建 `docker-compose.yml`:
```yaml
version: '3.8'

services:
  autogen:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - autogen
    restart: unless-stopped

volumes:
  redis_data:
```

```bash
# 構建和啟動
docker-compose up --build -d

# 查看日誌
docker-compose logs -f autogen

# 停止服務
docker-compose down
```

## 📊 監控和日誌

### 📈 性能監控

#### 內置監控
```python
# 啟用性能監控
from src.autogen_system.performance import create_metrics_collector

collector = create_metrics_collector(workflow_specific=True)
collector.start_collection()

# 查看實時指標
metrics = collector.get_metrics()
summary = collector.get_summary_report()
```

#### Prometheus集成 (可選)
```bash
# 安裝Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*
```

配置 `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'autogen'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
```

### 📝 日誌管理

#### 日誌配置
創建 `/etc/rsyslog.d/autogen.conf`:
```
# AutoGen日誌配置
:programname, isequal, "autogen" /var/log/autogen/app.log
& stop
```

#### 日誌輪轉
創建 `/etc/logrotate.d/autogen`:
```
/var/log/autogen/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 autogen autogen
    postrotate
        systemctl reload autogen
    endscript
}
```

### 🚨 監控腳本

創建健康檢查腳本 (`scripts/health_check.sh`):
```bash
#!/bin/bash

# AutoGen系統健康檢查

# 配置
API_URL="http://localhost:8001/api/system/status"
LOG_FILE="/var/log/autogen/health_check.log"
MAX_RESPONSE_TIME=10

# 記錄函數
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
}

# 檢查API響應
check_api() {
    local start_time=$(date +%s)
    local response=$(curl -s -w "%{http_code}" -o /dev/null $API_URL)
    local end_time=$(date +%s)
    local response_time=$((end_time - start_time))
    
    if [ "$response" = "200" ] && [ $response_time -le $MAX_RESPONSE_TIME ]; then
        log_message "✅ API健康檢查通過 (響應時間: ${response_time}s)"
        return 0
    else
        log_message "❌ API健康檢查失敗 (狀態碼: $response, 響應時間: ${response_time}s)"
        return 1
    fi
}

# 檢查系統資源
check_resources() {
    local memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    local disk_usage=$(df -h / | awk 'NR==2{printf "%.1f", $5}' | sed 's/%//')
    
    log_message "📊 系統資源: CPU: ${cpu_usage}%, 內存: ${memory_usage}%, 磁盤: ${disk_usage}%"
    
    # 警告閾值
    if (( $(echo "$memory_usage > 80" | bc -l) )); then
        log_message "⚠️ 內存使用率過高: ${memory_usage}%"
    fi
    
    if (( $(echo "$disk_usage > 80" | bc -l) )); then
        log_message "⚠️ 磁盤使用率過高: ${disk_usage}%"
    fi
}

# 主檢查流程
main() {
    log_message "🚀 開始健康檢查"
    
    if check_api; then
        check_resources
        log_message "✅ 健康檢查完成"
        exit 0
    else
        log_message "❌ 健康檢查失敗"
        # 可以在這裡添加告警通知
        exit 1
    fi
}

main "$@"
```

```bash
# 設置定時檢查
crontab -e
# 添加: */5 * * * * /opt/autogen/scripts/health_check.sh
```

## 🔧 運維操作

### 🚀 應用更新

```bash
# 創建更新腳本 update.sh
#!/bin/bash

echo "🚀 開始更新AutoGen系統..."

# 備份當前版本
sudo -u autogen cp -r /opt/autogen/app /opt/autogen/app.backup.$(date +%Y%m%d_%H%M%S)

# 停止服務
sudo systemctl stop autogen

# 更新代碼
cd /opt/autogen/app
sudo -u autogen git pull origin main

# 更新依賴
sudo -u autogen venv/bin/pip install -r requirements.txt

# 運行遷移 (如果需要)
# sudo -u autogen venv/bin/python manage.py migrate

# 重啟服務
sudo systemctl start autogen

# 檢查狀態
sleep 5
if sudo systemctl is-active --quiet autogen; then
    echo "✅ 更新成功，服務正常運行"
else
    echo "❌ 更新失敗，正在回滾..."
    # 回滾邏輯
    sudo systemctl stop autogen
    sudo -u autogen rm -rf /opt/autogen/app
    sudo -u autogen mv /opt/autogen/app.backup.* /opt/autogen/app
    sudo systemctl start autogen
    echo "🔄 已回滾到上一版本"
fi
```

### 💾 備份策略

```bash
# 創建備份腳本 backup.sh
#!/bin/bash

BACKUP_DIR="/backup/autogen"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="autogen_backup_$DATE"

# 創建備份目錄
mkdir -p $BACKUP_DIR

# 備份應用文件
tar -czf $BACKUP_DIR/${BACKUP_NAME}_app.tar.gz -C /opt/autogen app

# 備份配置文件
tar -czf $BACKUP_DIR/${BACKUP_NAME}_config.tar.gz -C /opt/autogen/app config

# 備份數據庫 (如果使用)
# pg_dump autogen_db > $BACKUP_DIR/${BACKUP_NAME}_db.sql

# 備份日誌
tar -czf $BACKUP_DIR/${BACKUP_NAME}_logs.tar.gz -C /var/log autogen

# 清理舊備份 (保留7天)
find $BACKUP_DIR -name "autogen_backup_*" -mtime +7 -delete

echo "✅ 備份完成: $BACKUP_NAME"
```

### 🔍 故障排除

#### 常見問題檢查腳本
```bash
#!/bin/bash
# troubleshoot.sh

echo "🔍 AutoGen系統故障排除"
echo "========================"

# 檢查服務狀態
echo "📊 服務狀態:"
systemctl status autogen --no-pager

# 檢查端口
echo -e "\n🌐 端口檢查:"
ss -tulpn | grep :8000

# 檢查進程
echo -e "\n🔧 進程狀態:"
ps aux | grep -E "(autogen|uvicorn)" | grep -v grep

# 檢查日誌
echo -e "\n📝 最近日誌:"
tail -20 /var/log/autogen/app.log

# 檢查磁盤空間
echo -e "\n💾 磁盤使用:"
df -h /

# 檢查內存
echo -e "\n🧠 內存使用:"
free -h

# 檢查網絡連接
echo -e "\n🌍 網絡測試:"
curl -s -o /dev/null -w "API響應時間: %{time_total}s\n" http://localhost:8001/api/system/status
```

## 🔐 安全配置

### 🛡️ 基礎安全

```bash
# 配置防火牆
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # 只允許通過Nginx訪問

# 設置fail2ban
sudo apt install -y fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# 配置SSH安全
sudo vim /etc/ssh/sshd_config
# 添加或修改:
# PermitRootLogin no
# PasswordAuthentication no
# AllowUsers autogen

sudo systemctl restart ssh
```

### 🔑 API安全

在 `conf_autogen.yaml` 中配置:
```yaml
security:
  api_key_required: true
  api_keys:
    - "your-secure-api-key-here"
  
  rate_limiting:
    enabled: true
    requests_per_minute: 100
    burst_size: 20
  
  cors:
    enabled: true
    allowed_origins:
      - "https://yourdomain.com"
      - "https://app.yourdomain.com"
  
  headers:
    x_frame_options: "DENY"
    x_content_type_options: "nosniff"
    x_xss_protection: "1; mode=block"
```

## 📋 部署檢查清單

### ✅ 部署前檢查

- [ ] 服務器配置滿足最低要求
- [ ] 所有依賴已正確安裝
- [ ] 配置文件已正確設置
- [ ] 環境變數已配置
- [ ] SSL證書已安裝
- [ ] 防火牆規則已配置
- [ ] 備份策略已實施

### ✅ 部署後檢查

- [ ] 服務正常啟動
- [ ] API端點響應正常
- [ ] 健康檢查通過
- [ ] 日誌正常記錄
- [ ] 監控系統正常工作
- [ ] 性能指標在正常範圍
- [ ] 安全配置生效

### ✅ 運行檢查

```bash
# 運行完整檢查
make deploy-check

# 或手動檢查
curl -f http://localhost:8001/api/system/status
python tests/autogen_system/performance_demo_standalone.py
make test-integration
```

## 🆘 支持和聯繫

- **文檔**: 查看 `docs/` 目錄
- **示例**: 參考 `examples/` 目錄  
- **測試**: 運行 `make test-all`
- **監控**: 訪問 `/api/system/status`

---

**部署成功後，您的AutoGen系統就可以為用戶提供強大的AI工作流服務了！** 🎉
