#!/bin/bash

# 服务监控脚本
# 使用方法: ./monitor.sh

echo "🔍 Extension Backend 服务监控"
echo "================================"

# 检查服务状态
echo "📊 服务状态:"
if systemctl is-active --quiet extension-backend.service; then
    echo "✅ 服务运行中"
else
    echo "❌ 服务未运行"
fi

# 检查端口
echo ""
echo "🌐 端口监听:"
if netstat -tlnp | grep :8000; then
    echo "✅ 端口8000正在监听"
else
    echo "❌ 端口8000未监听"
fi

# 检查进程
echo ""
echo "🔄 进程信息:"
if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
    echo "✅ Gunicorn进程运行中"
    pgrep -f "gunicorn.*extension_backend" | xargs ps -o pid,ppid,cmd --no-headers
else
    echo "❌ Gunicorn进程未运行"
fi

# 检查日志文件
echo ""
echo "📝 日志文件:"
if [ -f "/var/log/extension_backend/access.log" ]; then
    echo "✅ 访问日志存在"
    echo "   大小: $(du -h /var/log/extension_backend/access.log | cut -f1)"
else
    echo "❌ 访问日志不存在"
fi

if [ -f "/var/log/extension_backend/error.log" ]; then
    echo "✅ 错误日志存在"
    echo "   大小: $(du -h /var/log/extension_backend/error.log | cut -f1)"
else
    echo "❌ 错误日志不存在"
fi

# 检查系统资源
echo ""
echo "💻 系统资源:"
echo "CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "内存使用: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "磁盘使用: $(df -h / | tail -1 | awk '{print $5}')"

# 检查最近的错误日志
echo ""
echo "🚨 最近的错误日志 (最后10行):"
if [ -f "/var/log/extension_backend/error.log" ]; then
    tail -10 /var/log/extension_backend/error.log
else
    echo "无错误日志文件"
fi

# 检查服务日志
echo ""
echo "📋 最近的systemd日志 (最后5行):"
sudo journalctl -u extension-backend.service -n 5 --no-pager 