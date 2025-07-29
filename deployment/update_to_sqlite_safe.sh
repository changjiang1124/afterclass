#!/bin/bash

# 安全更新生产环境到SQLite3 (Safe update production to SQLite3)
# 不会覆盖现有数据库和配置文件 (Won't overwrite existing database and config files)

set -e  # 遇到错误时退出 (Exit on error)

echo "🔄 Safely updating Tongcove production environment to use SQLite3..."
echo "⚠️  This script will NOT overwrite your existing database or .env.production file"

# 检查是否在正确的目录 (Check if in correct directory)
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# 检查生产环境是否存在 (Check if production environment exists)
if [ ! -d "/var/www/tongcove" ]; then
    echo "❌ Error: Production environment not found at /var/www/tongcove"
    echo "   Please run the full setup script first"
    exit 1
fi

# 备份当前生产环境 (Backup current production environment)
echo "💾 Creating backup of current production environment..."
BACKUP_DIR="/var/www/tongcove_backup_$(date +%Y%m%d_%H%M%S)"
sudo cp -r /var/www/tongcove "$BACKUP_DIR"
echo "✅ Backup created at: $BACKUP_DIR"

# 停止服务 (Stop service)
echo "🛑 Stopping tongcove service..."
sudo systemctl stop tongcove || echo "Service was not running"

# 只更新代码文件，保护数据和配置 (Update only code files, protect data and config)
echo "📋 Updating code files (preserving database and config)..."

# 创建临时目录 (Create temporary directory)
TEMP_DIR="/tmp/tongcove_update_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_DIR"

# 复制需要更新的文件到临时目录 (Copy files to update to temp directory)
cp -r tongcove "$TEMP_DIR/"
cp -r accounts "$TEMP_DIR/"
cp -r assignments "$TEMP_DIR/"
cp -r chatbots "$TEMP_DIR/"
cp -r dashboard "$TEMP_DIR/"
cp -r namegen "$TEMP_DIR/"
cp -r pinyinit "$TEMP_DIR/"
cp -r speak_practice "$TEMP_DIR/"
cp -r stories "$TEMP_DIR/"
cp -r typingchinese "$TEMP_DIR/"
cp -r templates "$TEMP_DIR/"
cp -r static "$TEMP_DIR/"
cp -r deployment "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"
cp manage.py "$TEMP_DIR/"

# 更新生产环境的代码文件 (Update production code files)
sudo cp -r "$TEMP_DIR"/* /var/www/tongcove/

# 保持原有的权限 (Maintain original permissions)
sudo chown -R www-data:www-data /var/www/tongcove
sudo chmod 755 /var/www/tongcove

# 保护重要文件的权限 (Protect important file permissions)
if [ -f "/var/www/tongcove/.env.production" ]; then
    sudo chmod 600 /var/www/tongcove/.env.production
    sudo chown www-data:www-data /var/www/tongcove/.env.production
fi

if [ -f "/var/www/tongcove/db.sqlite3" ]; then
    sudo chmod 664 /var/www/tongcove/db.sqlite3
    sudo chown www-data:www-data /var/www/tongcove/db.sqlite3
fi

# 更新Python依赖 (Update Python dependencies)
echo "🐍 Updating Python dependencies..."
cd /var/www/tongcove
sudo -u www-data .venv/bin/pip install --upgrade pip
sudo -u www-data .venv/bin/pip install -r requirements.txt

# 收集静态文件 (Collect static files)
echo "📦 Collecting static files..."
sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings .venv/bin/python manage.py collectstatic --noinput

# 更新systemd服务文件 (Update systemd service file)
echo "🔧 Updating systemd service..."
sudo cp deployment/tongcove.service /etc/systemd/system/
sudo systemctl daemon-reload

# 清理临时文件 (Clean up temporary files)
rm -rf "$TEMP_DIR"

echo "✅ Code update complete!"
echo ""
echo "⚠️  IMPORTANT: Your database and .env.production file were NOT modified"
echo ""
echo "📋 Next steps:"
echo "1. Check your current database type:"
echo "   sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings /var/www/tongcove/.venv/bin/python -c \"from django.conf import settings; print('Database:', settings.DATABASES['default']['ENGINE'])\""
echo ""
echo "2. If you want to migrate from PostgreSQL to SQLite3:"
echo "   - First backup your PostgreSQL data: pg_dump your_db > backup.sql"
echo "   - Then run: sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings /var/www/tongcove/.venv/bin/python manage.py migrate"
echo ""
echo "3. Start the service: sudo systemctl start tongcove"
echo "4. Check service status: sudo systemctl status tongcove"
echo "5. Check logs: sudo journalctl -u tongcove -f"
echo ""
echo "🔙 If something goes wrong, restore from backup: $BACKUP_DIR"
