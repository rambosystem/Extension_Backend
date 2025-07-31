#!/bin/bash

# 生产环境启动脚本
# 使用方法: ./start_production.sh

set -e

# 项目根目录
PROJECT_DIR="/home/ubuntu/project/extension_backend"
cd "$PROJECT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 设置环境变量
export PYTHONPATH="$PROJECT_DIR"
export ENVIRONMENT="production"

# 创建日志目录
sudo mkdir -p /var/log/extension_backend
sudo chown ubuntu:ubuntu /var/log/extension_backend

# 检查端口是否被占用
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "端口8000已被占用，正在停止现有进程..."
    sudo pkill -f "gunicorn.*extension_backend" || true
    sleep 2
fi

# 启动Gunicorn
echo "启动Extension Backend生产服务..."
exec gunicorn app.main:app \
    --config gunicorn.conf.py \
    --pid /tmp/extension_backend.pid \
    --daemon 