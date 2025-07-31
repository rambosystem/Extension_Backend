#!/bin/bash

# 生产环境重启脚本
# 使用方法: ./restart_production.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 开始重启
log_info "开始重启 Extension Backend 生产服务..."

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log_info "脚本目录: $SCRIPT_DIR"

# 检查停止脚本
STOP_SCRIPT="$SCRIPT_DIR/stop_production.sh"
if [ ! -f "$STOP_SCRIPT" ]; then
    log_error "停止脚本不存在: $STOP_SCRIPT"
    exit 1
fi

# 检查启动脚本
START_SCRIPT="$SCRIPT_DIR/start_production.sh"
if [ ! -f "$START_SCRIPT" ]; then
    log_error "启动脚本不存在: $START_SCRIPT"
    exit 1
fi

# 第一步：停止服务
log_info "第一步：停止现有服务..."
if bash "$STOP_SCRIPT"; then
    log_success "服务停止成功"
else
    log_warning "服务停止过程中出现警告，继续重启流程"
fi

# 等待一段时间确保服务完全停止
log_info "等待服务完全停止..."
sleep 5

# 检查是否还有进程在运行
if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
    log_warning "仍有进程在运行，强制终止..."
    sudo pkill -9 -f "gunicorn.*extension_backend" || true
    sleep 2
fi

# 检查端口是否释放
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "端口8000仍被占用，可能被其他服务使用"
    PORT_PID=$(lsof -Pi :8000 -sTCP:LISTEN -t)
    log_info "占用端口的进程PID: $PORT_PID"
    
    # 询问是否继续
    read -p "是否继续重启？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "用户取消重启"
        exit 0
    fi
fi

# 第二步：启动服务
log_info "第二步：启动服务..."
if bash "$START_SCRIPT"; then
    log_success "服务启动成功"
else
    log_error "服务启动失败"
    exit 1
fi

# 第三步：验证服务状态
log_info "第三步：验证服务状态..."
sleep 3

# 检查进程
if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
    PIDS=$(pgrep -f "gunicorn.*extension_backend")
    log_success "服务进程运行正常，PID: $PIDS"
else
    log_error "服务进程未运行"
    exit 1
fi

# 检查端口
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_success "服务端口监听正常"
else
    log_error "服务端口未监听"
    exit 1
fi

# 检查服务响应
log_info "检查服务响应..."
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "服务健康检查通过"
        break
    elif curl -s http://localhost:8000/ > /dev/null 2>&1; then
        log_success "服务响应正常"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_info "等待服务启动... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_warning "服务响应检查超时，但进程运行正常"
fi

# 显示服务信息
log_success "Extension Backend 生产服务重启完成！"
log_info "服务地址: http://localhost:8000"
log_info "API文档: http://localhost:8000/docs"
log_info "健康检查: http://localhost:8000/health"

# 显示进程信息
PIDS=$(pgrep -f "gunicorn.*extension_backend")
log_info "运行中的进程PID: $PIDS"

# 显示端口信息
log_info "监听端口: 8000"

# 显示日志文件位置
LOG_DIR="/var/log/extension_backend"
log_info "日志文件位置: $LOG_DIR"
log_info "查看日志命令:"
log_info "  tail -f $LOG_DIR/gunicorn.log"
log_info "  tail -f $LOG_DIR/access.log"
log_info "  tail -f $LOG_DIR/error.log" 