# 简单生产环境更新指南 (Simple Production Update Guide)

## 当前生产环境 (Current Production Environment)
- **路径**: `/var/www/afterclass`
- **数据库**: SQLite3 (`db.sqlite3`)
- **配置**: `tongcove/settings.py` + `.env`
- **系统**: Ubuntu 24.04.2 LTS, Python 3.12.3

## 🚀 **快速更新步骤** (Quick Update Steps)

### 1. 备份数据库 (Backup Database)
```bash
cd /var/www/afterclass
sudo cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)
```

### 2. 更新代码 (Update Code)
```bash
# 检查当前版本
git log --oneline -1

# 拉取最新代码
sudo -u www-data git pull origin main

# 确认更新成功
git log --oneline -1
```

### 3. 安装新依赖 (Install New Dependencies)
```bash
# 安装系统依赖 (libmagic for file type detection)
sudo apt-get update
sudo apt-get install -y libmagic1

# 更新Python依赖
sudo -u www-data .venv/bin/pip install --upgrade pip
sudo -u www-data .venv/bin/pip install -r requirements.txt
```

### 4. 数据库迁移 (Database Migration)
```bash
# 检查待执行的迁移
sudo -u www-data .venv/bin/python manage.py showmigrations

# 执行迁移
sudo -u www-data .venv/bin/python manage.py migrate

# 如果有数据迁移命令
sudo -u www-data .venv/bin/python manage.py migrate_message_content
```

### 5. 收集静态文件 (Collect Static Files)
```bash
sudo -u www-data .venv/bin/python manage.py collectstatic --noinput
```

### 6. 重启服务 (Restart Service)
```bash
# 找到实际的服务名
sudo systemctl list-units --type=service | grep -E "(afterclass|tongcove|django)"

# 重启服务 (替换为实际服务名)
sudo systemctl restart [your-service-name]

# 检查服务状态
sudo systemctl status [your-service-name]
```

## 🔍 **验证更新** (Verify Update)

### 1. 检查网站
- 访问: https://afterclass.learnchineseperth.com.au
- 测试登录功能
- 测试语音练习功能

### 2. 检查日志
```bash
# 查看应用日志
sudo journalctl -u [your-service-name] --since "5 minutes ago"

# 查看nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 3. 检查数据库
```bash
# 确认迁移成功
sudo -u www-data .venv/bin/python manage.py showmigrations | grep -E "\[X\]"
```

## 🚨 **如果出现问题** (If Problems Occur)

### 快速回滚数据库
```bash
# 停止服务
sudo systemctl stop [your-service-name]

# 恢复数据库备份
sudo cp db.sqlite3.backup.YYYYMMDD_HHMMSS db.sqlite3

# 回滚代码 (如果需要)
sudo -u www-data git checkout 021af48

# 重启服务
sudo systemctl start [your-service-name]
```

## 📋 **更新检查清单** (Update Checklist)

- [ ] 数据库已备份
- [ ] 代码已更新
- [ ] 系统依赖已安装 (libmagic1)
- [ ] Python依赖已更新
- [ ] 数据库迁移已完成
- [ ] 静态文件已收集
- [ ] 服务已重启
- [ ] 网站可以正常访问
- [ ] 功能测试通过
- [ ] 日志无错误

## 💡 **提示** (Tips)

1. **在低峰时段更新**: 避免影响用户使用
2. **逐步验证**: 每个步骤完成后都检查状态
3. **保留备份**: 至少保留最近3次的数据库备份
4. **监控日志**: 更新后持续观察日志几分钟
