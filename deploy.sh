#!/bin/bash

# 设置错误处理
set -e

# 设置工作目录和备份参数
WORKSPACE_DIR="/var/www/afterclass"
BACKUP_DIR="/var/backups/afterclass"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="afterclass_backup_$TIMESTAMP.tar.gz"

cd $WORKSPACE_DIR

echo "当前工作目录: $(pwd)"

# 步骤 1: 创建当前状态的备份
echo "正在创建备份..."
# 使用 .gitignore 排除文件，并额外排除 .git 目录
tar --exclude-from=.gitignore --exclude=".git" -czf $BACKUP_DIR/$BACKUP_NAME .
echo "备份完成: $BACKUP_DIR/$BACKUP_NAME"

# 步骤 2: 从 Git 拉取最新代码
# 用 fetch + reset --hard 而非 git pull：部署目标应始终与 origin/main 完全一致，
# 避免本地改动/分叉导致 pull 因需要合并而中断（不会删除未跟踪文件）。
# (Deploy target must mirror origin/main exactly; reset --hard never stalls on divergence.)
echo "正在从 Git 拉取最新代码..."
git fetch origin main
git reset --hard origin/main

# 步骤 3: 部署流程
# 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate
echo "已激活虚拟环境"

# 安装/更新依赖 (Install/update dependencies so new requirements are picked up)
echo "正在安装依赖..."
pip install -r requirements.txt

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

echo "Django项目部署完成！"