#!/bin/bash

# SQLite3生产环境部署脚本 (SQLite3 Production Deployment Script)
# 用于设置使用SQLite3的生产环境 (Setup production environment with SQLite3)

set -e  # 遇到错误时退出 (Exit on error)

echo "🚀 Setting up Tongcove production environment with SQLite3..."

# 检查是否在正确的目录 (Check if in correct directory)
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# 创建必要的目录 (Create necessary directories)
echo "📁 Creating necessary directories..."
sudo mkdir -p /var/www/tongcove
sudo mkdir -p /var/www/tongcove/logs
sudo mkdir -p /var/www/tongcove/media
sudo mkdir -p /var/www/tongcove/staticfiles

# 复制项目文件 (Copy project files)
echo "📋 Copying project files..."
sudo cp -r . /var/www/tongcove/
sudo chown -R www-data:www-data /var/www/tongcove

# 设置虚拟环境 (Setup virtual environment)
echo "🐍 Setting up virtual environment..."
cd /var/www/tongcove
sudo -u www-data python3 -m venv .venv
sudo -u www-data .venv/bin/pip install --upgrade pip
sudo -u www-data .venv/bin/pip install -r requirements.txt

# 创建生产环境配置文件 (Create production environment file)
echo "⚙️ Creating production environment configuration..."
if [ ! -f "/var/www/tongcove/.env.production" ]; then
    sudo cp .env.production.sqlite /var/www/tongcove/.env.production
    echo "📝 Please edit /var/www/tongcove/.env.production with your actual values"
    echo "   Required changes:"
    echo "   - DJANGO_SECRET_KEY: Generate a secure secret key"
    echo "   - OPENAI_API_KEY: Your OpenAI API key"
    echo "   - GOOGLE_API_KEY: Your Google API key"
    echo "   - Email configuration"
fi

# 设置数据库 (Setup database)
echo "🗄️ Setting up SQLite3 database..."
cd /var/www/tongcove
sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings .venv/bin/python manage.py migrate

# 收集静态文件 (Collect static files)
echo "📦 Collecting static files..."
sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings .venv/bin/python manage.py collectstatic --noinput

# 创建超级用户 (Create superuser)
echo "👤 Creating superuser..."
echo "Please create a superuser account:"
sudo -u www-data DJANGO_SETTINGS_MODULE=deployment.production_settings .venv/bin/python manage.py createsuperuser

# 设置文件权限 (Set file permissions)
echo "🔒 Setting file permissions..."
sudo chmod 600 /var/www/tongcove/.env.production
sudo chown www-data:www-data /var/www/tongcove/.env.production
sudo chmod 664 /var/www/tongcove/db.sqlite3
sudo chown www-data:www-data /var/www/tongcove/db.sqlite3

# 安装systemd服务 (Install systemd service)
echo "🔧 Installing systemd service..."
sudo cp deployment/tongcove.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tongcove

# 安装nginx配置 (Install nginx configuration)
if [ -f "deployment/nginx.conf" ]; then
    echo "🌐 Installing nginx configuration..."
    sudo cp deployment/nginx.conf /etc/nginx/sites-available/tongcove
    sudo ln -sf /etc/nginx/sites-available/tongcove /etc/nginx/sites-enabled/
    sudo nginx -t
fi

echo "✅ Production setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit /var/www/tongcove/.env.production with your actual configuration"
echo "2. Start the service: sudo systemctl start tongcove"
echo "3. Check service status: sudo systemctl status tongcove"
echo "4. Restart nginx: sudo systemctl restart nginx"
echo "5. Check logs: sudo journalctl -u tongcove -f"
echo ""
echo "🌍 Your site should be available at: https://afterclass.learnchineseperth.com.au"
