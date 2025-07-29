# 数据库迁移指南 (Database Migration Guide)

## 从PostgreSQL迁移到SQLite3 (Migrating from PostgreSQL to SQLite3)

⚠️ **重要提醒**: 在进行任何数据库迁移之前，请务必备份你的数据！

### 选项1: 保持现有PostgreSQL数据库 (Keep existing PostgreSQL)

如果你想保持使用PostgreSQL，只需在生产环境的`.env.production`文件中添加：

```bash
# 启用PostgreSQL (Enable PostgreSQL)
USE_POSTGRESQL=true
DB_ENGINE=django.db.backends.postgresql
DB_NAME=your_existing_db_name
DB_USER=your_existing_db_user
DB_PASSWORD=your_existing_db_password
DB_HOST=localhost
DB_PORT=5432
```

### 选项2: 迁移到SQLite3 (Migrate to SQLite3)

#### 步骤1: 备份现有数据 (Backup existing data)

```bash
# 备份PostgreSQL数据 (Backup PostgreSQL data)
sudo -u postgres pg_dump your_database_name > /tmp/production_backup.sql

# 或者使用Django的dumpdata命令 (Or use Django's dumpdata command)
cd /var/www/tongcove
sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings .venv/bin/python manage.py dumpdata > /tmp/django_data_backup.json
```

#### 步骤2: 更新代码 (Update code)

```bash
# 运行安全更新脚本 (Run safe update script)
./deployment/update_to_sqlite_safe.sh
```

#### 步骤3: 配置SQLite3 (Configure SQLite3)

编辑 `/var/www/tongcove/.env.production`，确保没有设置 `USE_POSTGRESQL=true`：

```bash
# 注释掉或删除PostgreSQL配置 (Comment out or remove PostgreSQL config)
# USE_POSTGRESQL=true
# DB_ENGINE=django.db.backends.postgresql
# DB_NAME=...
```

#### 步骤4: 创建新的SQLite3数据库 (Create new SQLite3 database)

```bash
cd /var/www/tongcove

# 删除旧的SQLite数据库（如果存在）(Remove old SQLite database if exists)
sudo rm -f db.sqlite3

# 运行迁移创建新数据库 (Run migrations to create new database)
sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings .venv/bin/python manage.py migrate

# 创建超级用户 (Create superuser)
sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings .venv/bin/python manage.py createsuperuser
```

#### 步骤5: 导入数据 (Import data)

```bash
# 使用Django的loaddata命令导入数据 (Import data using Django's loaddata)
sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings .venv/bin/python manage.py loaddata /tmp/django_data_backup.json
```

#### 步骤6: 设置文件权限 (Set file permissions)

```bash
# 设置SQLite数据库权限 (Set SQLite database permissions)
sudo chmod 664 /var/www/tongcove/db.sqlite3
sudo chown www-data:www-data /var/www/tongcove/db.sqlite3
```

#### 步骤7: 启动服务 (Start service)

```bash
# 启动服务 (Start service)
sudo systemctl start tongcove
sudo systemctl status tongcove

# 检查日志 (Check logs)
sudo journalctl -u tongcove -f
```

### 验证迁移 (Verify migration)

1. **检查数据库连接**:
   ```bash
   sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings /var/www/tongcove/.venv/bin/python -c "
   from django.conf import settings
   from django.db import connection
   print('Database engine:', settings.DATABASES['default']['ENGINE'])
   print('Database name:', settings.DATABASES['default']['NAME'])
   cursor = connection.cursor()
   cursor.execute('SELECT COUNT(*) FROM django_migrations')
   print('Migrations count:', cursor.fetchone()[0])
   "
   ```

2. **访问网站**: 访问 https://afterclass.learnchineseperth.com.au

3. **检查管理界面**: 访问 https://afterclass.learnchineseperth.com.au/admin/

### 回滚计划 (Rollback plan)

如果迁移出现问题，可以快速回滚：

```bash
# 停止服务 (Stop service)
sudo systemctl stop tongcove

# 恢复备份 (Restore backup)
sudo rm -rf /var/www/tongcove
sudo cp -r /var/www/tongcove_backup_YYYYMMDD_HHMMSS /var/www/tongcove

# 启动服务 (Start service)
sudo systemctl start tongcove
```

### 注意事项 (Important notes)

1. **性能**: SQLite3适合中小型应用，如果你的应用有高并发需求，建议继续使用PostgreSQL
2. **备份**: SQLite3的备份更简单，只需复制`db.sqlite3`文件
3. **并发**: SQLite3的写入并发能力有限，读取性能良好
4. **文件权限**: 确保`db.sqlite3`文件有正确的权限设置
