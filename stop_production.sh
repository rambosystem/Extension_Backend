#!/bin/bash

# 生产环境停止脚本
# 使用方法: ./stop_production.sh

set -e

echo "停止Extension Backend服务..."

# 方法1: 通过PID文件停止
if [ -f /tmp/extension_backend.pid ]; then
    PID=$(cat /tmp/extension_backend.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "通过PID文件停止进程 $PID..."
        kill -TERM "$PID"
        sleep 5
        
        # 如果进程还在运行，强制杀死
        if kill -0 "$PID" 2>/dev/null; then
            echo "强制停止进程 $PID..."
            kill -KILL "$PID"
        fi
    else
        echo "PID文件存在但进程不存在，清理PID文件..."
    fi
    rm -f /tmp/extension_backend.pid
fi

# 方法2: 通过进程名停止
echo "检查并停止所有相关进程..."
sudo pkill -f "gunicorn.*extension_backend" || true
sudo pkill -f "uvicorn.*app.main:app" || true

# 等待进程完全停止
sleep 3

# 检查是否还有进程在运行
if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
    echo "警告: 仍有相关进程在运行"
    pgrep -f "gunicorn.*extension_backend"
else
    echo "✅ Extension Backend服务已停止"
fi 