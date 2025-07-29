# 生产环境部署指南 (Production Deployment Guide)

Learn Chinese Perth - 增强聊天交互功能部署文档

## 目录 (Table of Contents)

1. [系统要求](#系统要求-system-requirements)
2. [预部署准备](#预部署准备-pre-deployment-preparation)
3. [环境配置](#环境配置-environment-configuration)
4. [数据库设置](#数据库设置-database-setup)
5. [应用程序部署](#应用程序部署-application-deployment)
6. [Web服务器配置](#web服务器配置-web-server-configuration)
7. [SSL证书配置](#ssl证书配置-ssl-certificate-configuration)
8. [监控和日志](#监控和日志-monitoring-and-logging)
9. [安全配置](#安全配置-security-configuration)
10. [故障排除](#故障排除-troubleshooting)

## 系统要求 (System Requirements)

### 最低硬件要求 (Minimum Hardware Requirements)
- **CPU**: 2核心 2.0GHz
- **内存**: 4GB RAM
- **存储**: 20GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐硬件要求 (Recommended Hardware Requirements)
- **CPU**: 4核心 2.5GHz
- **内存**: 8GB RAM
- **存储**: 50GB SSD
- **网络**: 高速互联网连接

### 软件要求 (Software Requirements)
- **操作系统**: Ubuntu 20.04 LTS 或更高版本
- **Python**: 3.8+
- **数据库**: PostgreSQL 12+
- **缓存**: Redis 6+
- **Web服务器**: Nginx 1.18+
- **进程管理**: systemd

## 预部署准备 (Pre-deployment Preparation)

### 1. 服务器准备 (Server Preparation)

```bash
# 更新系统包 (Update system packages)
sudo apt update && sudo apt upgrade -y

# 安装必需的系统包 (Install required system packages)
sudo apt install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib redis-server nginx git \
    build-essential libpq-dev libmagic1 supervisor certbot \
    python3-certbot-nginx ufw fail2ban

# 创建应用用户 (Create application user)
sudo useradd -m -s /bin/bash tongcove
sudo usermod -aG www-data tongcove
```

### 2. 防火墙配置 (Firewall Configuration)

```bash
# 配置UFW防火墙 (Configure UFW firewall)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw status
```

### 3. 创建目录结构 (Create Directory Structure)

```bash
# 创建应用目录 (Create application directories)
sudo mkdir -p /var/www/tongcove
sudo mkdir -p /var/www/tongcove/logs
sudo mkdir -p /var/www/tongcove/media
sudo mkdir -p /var/backups/tongcove

# 设置权限 (Set permissions)
sudo chown -R tongcove:www-data /var/www/tongcove
sudo chmod -R 755 /var/www/tongcove
```

## 环境配置 (Environment Configuration)

### 1. API密钥获取 (API Key Acquisition)

#### OpenAI API密钥 (OpenAI API Key)
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 创建账户并获取API密钥
3. 确保账户有足够的使用额度

#### Google Cloud TTS API密钥 (Google Cloud TTS API Key)
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用Text-to-Speech API
4. 创建服务账户并下载JSON密钥文件
5. 或创建API密钥用于简单认证

### 2. 环境变量配置 (Environment Variables Configuration)

```bash
# 复制环境变量模板 (Copy environment template)
cd /var/www/tongcove
cp .env.production.template .env.production

# 编辑环境变量 (Edit environment variables)
sudo nano .env.production
```

**重要环境变量说明 (Important Environment Variables):**

```bash
# Django核心配置 (Django Core Configuration)
DJANGO_SECRET_KEY=your-super-secret-key-here-at-least-50-characters-long
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# 数据库配置 (Database Configuration)
DB_NAME=tongcove_production
DB_USER=tongcove_user
DB_PASSWORD=secure-database-password
DB_HOST=localhost
DB_PORT=5432

# API密钥 (API Keys)
OPENAI_API_KEY=sk-your-openai-api-key-here
GOOGLE_API_KEY=your-google-api-key-here

# 安全配置 (Security Configuration)
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 监控配置 (Monitoring Configuration)
SECURITY_ALERT_EMAIL=admin@yourdomain.com
```

### 3. 文件权限设置 (File Permissions Setup)

```bash
# 设置环境文件权限 (Set environment file permissions)
sudo chmod 600 /var/www/tongcove/.env.production
sudo chown tongcove:www-data /var/www/tongcove/.env.production
```

## 数据库设置 (Database Setup)

### 1. PostgreSQL配置 (PostgreSQL Configuration)

```bash
# 启动PostgreSQL服务 (Start PostgreSQL service)
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库用户和数据库 (Create database user and database)
sudo -u postgres psql << EOF
CREATE USER tongcove_user WITH PASSWORD 'secure-database-password';
CREATE DATABASE tongcove_production OWNER tongcove_user;
GRANT ALL PRIVILEGES ON DATABASE tongcove_production TO tongcove_user;
ALTER USER tongcove_user CREATEDB;
\q
EOF
```

### 2. 数据库安全配置 (Database Security Configuration)

```bash
# 编辑PostgreSQL配置 (Edit PostgreSQL configuration)
sudo nano /etc/postgresql/12/main/postgresql.conf

# 修改以下设置 (Modify the following settings):
# listen_addresses = 'localhost'
# max_connections = 100
# shared_buffers = 256MB

# 编辑访问控制 (Edit access control)
sudo nano /etc/postgresql/12/main/pg_hba.conf

# 确保本地连接使用密码认证 (Ensure local connections use password authentication)
# local   all             all                                     md5
# host    all             all             127.0.0.1/32            md5

# 重启PostgreSQL (Restart PostgreSQL)
sudo systemctl restart postgresql
```

### 3. Redis配置 (Redis Configuration)

```bash
# 启动Redis服务 (Start Redis service)
sudo systemctl start redis-server
sudo systemctl enable redis-server

# 配置Redis安全 (Configure Redis security)
sudo nano /etc/redis/redis.conf

# 修改以下设置 (Modify the following settings):
# bind 127.0.0.1
# requirepass your-redis-password
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# 重启Redis (Restart Redis)
sudo systemctl restart redis-server
```

## 应用程序部署 (Application Deployment)

### 1. 代码部署 (Code Deployment)

```bash
# 切换到应用用户 (Switch to application user)
sudo su - tongcove

# 克隆代码仓库 (Clone code repository)
cd /var/www/tongcove
git clone https://github.com/your-repo/tongcove.git .

# 或者上传代码文件 (Or upload code files)
# scp -r /local/path/to/code/* tongcove@server:/var/www/tongcove/
```

### 2. Python虚拟环境设置 (Python Virtual Environment Setup)

```bash
# 创建虚拟环境 (Create virtual environment)
python3 -m venv .venv

# 激活虚拟环境 (Activate virtual environment)
source .venv/bin/activate

# 升级pip (Upgrade pip)
pip install --upgrade pip

# 安装依赖 (Install dependencies)
pip install -r requirements.txt

# 安装生产环境依赖 (Install production dependencies)
pip install gunicorn psycopg2-binary redis whitenoise
```

### 3. 数据库迁移 (Database Migration)

```bash
# 设置Django设置模块 (Set Django settings module)
export DJANGO_SETTINGS_MODULE=deployment.production_settings

# 运行数据库迁移 (Run database migrations)
python manage.py migrate

# 收集静态文件 (Collect static files)
python manage.py collectstatic --noinput

# 创建超级用户 (Create superuser)
python manage.py createsuperuser
```

### 4. 应用程序测试 (Application Testing)

```bash
# 运行Django检查 (Run Django checks)
python manage.py check --deploy

# 运行安全检查 (Run security checks)
python manage.py security_monitor validate

# 测试应用程序启动 (Test application startup)
python manage.py runserver 127.0.0.1:8000
# 按Ctrl+C停止测试服务器
```

## Web服务器配置 (Web Server Configuration)

### 1. Gunicorn配置 (Gunicorn Configuration)

```bash
# 创建Gunicorn配置文件 (Create Gunicorn configuration file)
sudo nano /var/www/tongcove/gunicorn.conf.py
```

```python
# Gunicorn配置 (Gunicorn Configuration)
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
user = "tongcove"
group = "www-data"
tmp_upload_dir = None
```

### 2. Systemd服务配置 (Systemd Service Configuration)

```bash
# 复制服务文件 (Copy service file)
sudo cp /var/www/tongcove/deployment/tongcove.service /etc/systemd/system/

# 重新加载systemd (Reload systemd)
sudo systemctl daemon-reload

# 启用并启动服务 (Enable and start service)
sudo systemctl enable tongcove.service
sudo systemctl start tongcove.service

# 检查服务状态 (Check service status)
sudo systemctl status tongcove.service
```

### 3. Nginx配置 (Nginx Configuration)

```bash
# 复制Nginx配置 (Copy Nginx configuration)
sudo cp /var/www/tongcove/deployment/nginx.conf /etc/nginx/sites-available/tongcove

# 编辑配置文件，更新域名 (Edit configuration file, update domain name)
sudo nano /etc/nginx/sites-available/tongcove

# 启用站点 (Enable site)
sudo ln -s /etc/nginx/sites-available/tongcove /etc/nginx/sites-enabled/

# 删除默认站点 (Remove default site)
sudo rm /etc/nginx/sites-enabled/default

# 测试Nginx配置 (Test Nginx configuration)
sudo nginx -t

# 重启Nginx (Restart Nginx)
sudo systemctl restart nginx
```

## SSL证书配置 (SSL Certificate Configuration)

### 1. Let's Encrypt证书 (Let's Encrypt Certificate)

```bash
# 获取SSL证书 (Obtain SSL certificate)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 测试自动续期 (Test automatic renewal)
sudo certbot renew --dry-run

# 设置自动续期 (Setup automatic renewal)
sudo crontab -e
# 添加以下行 (Add the following line):
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. 证书验证 (Certificate Verification)

```bash
# 检查证书状态 (Check certificate status)
sudo certbot certificates

# 测试SSL配置 (Test SSL configuration)
# 访问 https://www.ssllabs.com/ssltest/ 测试您的域名
```

## 监控和日志 (Monitoring and Logging)

### 1. 日志轮转配置 (Log Rotation Configuration)

```bash
# 创建日志轮转配置 (Create log rotation configuration)
sudo nano /etc/logrotate.d/tongcove
```

```
/var/www/tongcove/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 tongcove www-data
    postrotate
        systemctl reload tongcove.service
    endscript
}
```

### 2. 系统监控设置 (System Monitoring Setup)

```bash
# 创建监控脚本 (Create monitoring script)
sudo nano /usr/local/bin/tongcove-monitor.sh
```

```bash
#!/bin/bash
cd /var/www/tongcove
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=deployment.production_settings
python manage.py monitor_system dashboard --format json > /var/log/tongcove-monitor.log
```

```bash
# 设置执行权限 (Set execute permissions)
sudo chmod +x /usr/local/bin/tongcove-monitor.sh

# 添加到crontab (Add to crontab)
sudo crontab -e
# 添加以下行 (Add the following line):
# */5 * * * * /usr/local/bin/tongcove-monitor.sh
```

### 3. 告警配置 (Alert Configuration)

```bash
# 配置邮件告警 (Configure email alerts)
# 在.env.production中设置 (Set in .env.production):
SECURITY_ALERT_EMAIL=admin@yourdomain.com
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 安全配置 (Security Configuration)

### 1. Fail2Ban配置 (Fail2Ban Configuration)

```bash
# 创建Nginx jail配置 (Create Nginx jail configuration)
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
```

```bash
# 重启Fail2Ban (Restart Fail2Ban)
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

### 2. 系统安全加固 (System Security Hardening)

```bash
# 禁用不必要的服务 (Disable unnecessary services)
sudo systemctl disable apache2 2>/dev/null || true
sudo systemctl disable mysql 2>/dev/null || true

# 设置文件权限 (Set file permissions)
sudo chmod 600 /var/www/tongcove/.env.production
sudo chmod -R 644 /var/www/tongcove/static/
sudo chmod -R 755 /var/www/tongcove/media/

# 定期安全更新 (Regular security updates)
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 故障排除 (Troubleshooting)

### 常见问题和解决方案 (Common Issues and Solutions)

#### 1. 应用程序无法启动 (Application Won't Start)

```bash
# 检查服务状态 (Check service status)
sudo systemctl status tongcove.service

# 查看详细日志 (View detailed logs)
sudo journalctl -u tongcove.service -f

# 检查配置文件 (Check configuration files)
cd /var/www/tongcove
source .venv/bin/activate
export DJANGO_SETTINGS_MODULE=deployment.production_settings
python manage.py check --deploy
```

#### 2. 数据库连接问题 (Database Connection Issues)

```bash
# 测试数据库连接 (Test database connection)
sudo -u postgres psql -d tongcove_production -U tongcove_user

# 检查PostgreSQL状态 (Check PostgreSQL status)
sudo systemctl status postgresql

# 查看PostgreSQL日志 (View PostgreSQL logs)
sudo tail -f /var/log/postgresql/postgresql-12-main.log
```

#### 3. 静态文件问题 (Static Files Issues)

```bash
# 重新收集静态文件 (Re-collect static files)
cd /var/www/tongcove
source .venv/bin/activate
python manage.py collectstatic --clear --noinput

# 检查文件权限 (Check file permissions)
ls -la /var/www/tongcove/staticfiles/
```

#### 4. SSL证书问题 (SSL Certificate Issues)

```bash
# 检查证书状态 (Check certificate status)
sudo certbot certificates

# 手动续期证书 (Manually renew certificate)
sudo certbot renew

# 检查Nginx SSL配置 (Check Nginx SSL configuration)
sudo nginx -t
```

#### 5. 性能问题 (Performance Issues)

```bash
# 监控系统资源 (Monitor system resources)
cd /var/www/tongcove
source .venv/bin/activate
python manage.py monitor_system watch

# 检查数据库性能 (Check database performance)
sudo -u postgres psql -d tongcove_production -c "SELECT * FROM pg_stat_activity;"

# 检查Redis状态 (Check Redis status)
redis-cli info
```

### 日志文件位置 (Log File Locations)

- **应用程序日志**: `/var/www/tongcove/logs/`
- **Nginx日志**: `/var/log/nginx/`
- **系统日志**: `journalctl -u tongcove.service`
- **PostgreSQL日志**: `/var/log/postgresql/`
- **Redis日志**: `/var/log/redis/`

### 有用的命令 (Useful Commands)

```bash
# 重启所有服务 (Restart all services)
sudo systemctl restart tongcove.service nginx postgresql redis-server

# 查看实时日志 (View real-time logs)
sudo tail -f /var/www/tongcove/logs/django.log

# 检查端口使用情况 (Check port usage)
sudo netstat -tlnp | grep :8000

# 检查磁盘空间 (Check disk space)
df -h

# 检查内存使用 (Check memory usage)
free -h

# 检查进程 (Check processes)
ps aux | grep gunicorn
```

## 维护和更新 (Maintenance and Updates)

### 定期维护任务 (Regular Maintenance Tasks)

1. **系统更新** (System Updates)
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **应用程序更新** (Application Updates)
   ```bash
   cd /var/www/tongcove
   git pull origin main
   source .venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   sudo systemctl restart tongcove.service
   ```

3. **数据库备份** (Database Backup)
   ```bash
   sudo -u postgres pg_dump tongcove_production > /var/backups/tongcove/db_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

4. **日志清理** (Log Cleanup)
   ```bash
   sudo logrotate -f /etc/logrotate.d/tongcove
   ```

### 监控检查清单 (Monitoring Checklist)

- [ ] 应用程序服务运行正常
- [ ] 数据库连接正常
- [ ] Redis缓存工作正常
- [ ] SSL证书有效且未过期
- [ ] 磁盘空间充足（<80%使用率）
- [ ] 内存使用正常（<85%使用率）
- [ ] CPU使用正常（<80%使用率）
- [ ] 备份任务正常执行
- [ ] 安全告警正常工作
- [ ] 日志轮转正常工作

---

**注意**: 本指南提供了完整的部署流程，但请根据您的具体环境和需求进行调整。在生产环境中部署前，建议先在测试环境中完整测试整个部署流程。