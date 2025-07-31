#!/bin/bash

# 生产环境部署脚本
# 使用方法: ./deploy_production.sh

set -e

echo "🚀 开始部署Extension Backend到生产环境..."

# 项目根目录
PROJECT_DIR="/home/ubuntu/project/extension_backend"
cd "$PROJECT_DIR"

# 1. 停止现有服务
echo "📦 停止现有服务..."
./stop_production.sh || true

# 2. 激活虚拟环境并安装依赖
echo "📦 安装/更新依赖..."
source venv/bin/activate
pip install -r requirements.txt

# 3. 创建必要的目录
echo "📁 创建必要目录..."
sudo mkdir -p /var/log/extension_backend
sudo chown ubuntu:ubuntu /var/log/extension_backend

# 4. 设置脚本权限
echo "🔐 设置脚本权限..."
chmod +x start_production.sh
chmod +x stop_production.sh

# 5. 安装systemd服务
echo "🔧 安装systemd服务..."
sudo cp extension-backend.service /etc/systemd/system/
sudo systemctl daemon-reload

# 6. 安装日志轮转配置
echo "📝 安装日志轮转配置..."
sudo cp extension-backend /etc/logrotate.d/
sudo chmod 644 /etc/logrotate.d/extension-backend

# 7. 启用开机启动
echo "🔌 启用开机启动..."
sudo systemctl enable extension-backend.service

# 8. 启动服务
echo "🚀 启动服务..."
sudo systemctl start extension-backend.service

# 9. 检查服务状态
echo "✅ 检查服务状态..."
sleep 5
sudo systemctl status extension-backend.service --no-pager

# 10. 检查端口
echo "🌐 检查端口监听..."
if netstat -tlnp | grep :8000; then
    echo "✅ 服务已成功启动在端口8000"
else
    echo "❌ 服务启动失败，请检查日志"
    sudo journalctl -u extension-backend.service -n 20
    exit 1
fi

echo "🎉 部署完成！"
echo "📋 常用命令："
echo "  启动服务: sudo systemctl start extension-backend.service"
echo "  停止服务: sudo systemctl stop extension-backend.service"
echo "  重启服务: sudo systemctl restart extension-backend.service"
echo "  查看状态: sudo systemctl status extension-backend.service"
echo "  查看日志: sudo journalctl -u extension-backend.service -f"
echo "  查看访问日志: tail -f /var/log/extension_backend/access.log"
echo "  查看错误日志: tail -f /var/log/extension_backend/error.log" 