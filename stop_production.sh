#!/bin/bash

# 生产环境停止脚本
# 使用方法: ./stop_production.sh

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

# 开始停止
log_info "开始停止 Extension Backend 生产服务..."

# PID文件路径
PID_FILE="/tmp/extension_backend.pid"

# 检查PID文件
if [ ! -f "$PID_FILE" ]; then
    log_warning "PID文件不存在: $PID_FILE"
    
    # 检查是否有相关进程在运行
    if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
        log_info "发现运行中的Gunicorn进程，尝试停止..."
        PIDS=$(pgrep -f "gunicorn.*extension_backend")
        log_info "找到进程PID: $PIDS"
    else
        log_success "没有发现运行中的Extension Backend进程"
        exit 0
    fi
else
    PID=$(cat "$PID_FILE")
    log_info "从PID文件读取进程ID: $PID"
    
    # 检查进程是否存在
    if ! ps -p "$PID" > /dev/null 2>&1; then
        log_warning "PID文件中的进程不存在，清理PID文件..."
        rm -f "$PID_FILE"
        
        # 检查是否有其他相关进程
        if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
            log_info "发现其他运行中的Gunicorn进程，尝试停止..."
            PIDS=$(pgrep -f "gunicorn.*extension_backend")
            log_info "找到进程PID: $PIDS"
        else
            log_success "没有发现运行中的Extension Backend进程"
            exit 0
        fi
    else
        log_info "确认进程存在，PID: $PID"
        PIDS="$PID"
    fi
fi

# 优雅停止进程
log_info "尝试优雅停止进程..."
for pid in $PIDS; do
    log_info "发送SIGTERM信号到进程 $pid..."
    kill -TERM "$pid" 2>/dev/null || true
done

# 等待进程停止
log_info "等待进程优雅停止..."
TIMEOUT=30
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if ! pgrep -f "gunicorn.*extension_backend" > /dev/null; then
        log_success "所有进程已优雅停止"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [ $((ELAPSED % 5)) -eq 0 ]; then
        log_info "等待中... ($ELAPSED/$TIMEOUT 秒)"
    fi
done

# 检查是否还有进程在运行
if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
    log_warning "优雅停止超时，强制终止进程..."
    PIDS=$(pgrep -f "gunicorn.*extension_backend")
    for pid in $PIDS; do
        log_info "强制终止进程 $pid..."
        kill -KILL "$pid" 2>/dev/null || true
    done
    
    # 等待强制终止
    sleep 2
    if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
        log_error "无法强制终止进程"
        exit 1
    else
        log_success "进程已强制终止"
    fi
fi

# 清理PID文件
if [ -f "$PID_FILE" ]; then
    log_info "清理PID文件..."
    rm -f "$PID_FILE"
    log_success "PID文件已清理"
fi

# 检查端口是否释放
log_info "检查端口释放..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "端口8000仍被占用，可能被其他进程使用"
    PORT_PID=$(lsof -Pi :8000 -sTCP:LISTEN -t)
    log_info "占用端口的进程PID: $PORT_PID"
else
    log_success "端口8000已释放"
fi

# 检查进程状态
log_info "最终检查进程状态..."
if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
    log_error "仍有Extension Backend进程在运行"
    PIDS=$(pgrep -f "gunicorn.*extension_backend")
    log_info "仍在运行的进程PID: $PIDS"
    exit 1
else
    log_success "所有Extension Backend进程已停止"
fi

log_success "Extension Backend 生产服务停止完成！" 