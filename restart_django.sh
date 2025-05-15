#!/bin/bash

# 设置错误处理
set -e

# 设置工作目录
WORKSPACE_DIR="/var/www/afterclass"
cd $WORKSPACE_DIR

echo "当前工作目录: $(pwd)"

# 激活虚拟环境
source .venv/bin/activate
echo "已激活虚拟环境"

# 收集静态文件
echo "正在收集静态文件..."
python manage.py collectstatic --noinput

# 创建数据库迁移
echo "正在创建数据库迁移..."
python manage.py makemigrations

# 应用数据库迁移
echo "正在应用数据库迁移..."
python manage.py migrate

# 重启Gunicorn服务
echo "正在重启Gunicorn服务..."
sudo systemctl restart afterclass

# 检查服务状态
echo "检查服务状态..."
sudo systemctl status afterclass --no-pager

echo "Django项目重启完成！" 