#!/bin/bash

# 生产环境启动脚本
# 使用方法: ./start_production.sh

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

# 检查函数
check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        log_success "命令 $1 可用"
        return 0
    else
        log_error "命令 $1 不可用"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        log_success "文件 $1 存在"
        return 0
    else
        log_error "文件 $1 不存在"
        return 1
    fi
}

check_directory() {
    if [ -d "$1" ]; then
        log_success "目录 $1 存在"
        return 0
    else
        log_error "目录 $1 不存在"
        return 1
    fi
}

# 开始启动
log_info "开始启动 Extension Backend 生产服务..."

# 项目根目录
PROJECT_DIR="/home/ubuntu/project/extension_backend"
log_info "项目目录: $PROJECT_DIR"

# 检查项目目录
if ! check_directory "$PROJECT_DIR"; then
    log_error "项目目录不存在，请检查路径"
    exit 1
fi

# 切换到项目目录
log_info "切换到项目目录..."
cd "$PROJECT_DIR"
if [ "$(pwd)" != "$PROJECT_DIR" ]; then
    log_error "切换目录失败"
    exit 1
fi
log_success "成功切换到项目目录: $(pwd)"

# 检查虚拟环境
log_info "检查虚拟环境..."
VENV_DIR="$PROJECT_DIR/venv"
if ! check_directory "$VENV_DIR"; then
    log_error "虚拟环境不存在，请先创建虚拟环境"
    exit 1
fi

# 检查虚拟环境中的Python
if ! check_file "$VENV_DIR/bin/python"; then
    log_error "虚拟环境中Python不存在"
    exit 1
fi

# 激活虚拟环境
log_info "激活虚拟环境..."
source venv/bin/activate
if [ -z "$VIRTUAL_ENV" ]; then
    log_error "虚拟环境激活失败"
    exit 1
fi
log_success "虚拟环境激活成功: $VIRTUAL_ENV"

# 检查Python版本
log_info "检查Python版本..."
PYTHON_VERSION=$(python --version 2>&1)
log_info "Python版本: $PYTHON_VERSION"

# 设置环境变量
log_info "设置环境变量..."
export PYTHONPATH="$PROJECT_DIR"
export ENVIRONMENT="production"
log_success "环境变量设置完成"
log_info "PYTHONPATH: $PYTHONPATH"
log_info "ENVIRONMENT: $ENVIRONMENT"

# 检查必要的Python包
log_info "检查必要的Python包..."
REQUIRED_PACKAGES=("fastapi" "uvicorn" "gunicorn" "faiss" "sentence_transformers")
for package in "${REQUIRED_PACKAGES[@]}"; do
    if python -c "import $package" 2>/dev/null; then
        log_success "包 $package 已安装"
    else
        log_error "包 $package 未安装"
        exit 1
    fi
done

# 检查配置文件
log_info "检查配置文件..."
if ! check_file "gunicorn.conf.py"; then
    log_error "Gunicorn配置文件不存在"
    exit 1
fi

if ! check_file "app/main.py"; then
    log_error "主应用文件不存在"
    exit 1
fi

# 创建日志目录
log_info "创建日志目录..."
LOG_DIR="/var/log/extension_backend"
if [ ! -d "$LOG_DIR" ]; then
    log_info "创建日志目录: $LOG_DIR"
    sudo mkdir -p "$LOG_DIR"
    if [ $? -eq 0 ]; then
        log_success "日志目录创建成功"
    else
        log_error "日志目录创建失败"
        exit 1
    fi
else
    log_success "日志目录已存在: $LOG_DIR"
fi

# 设置日志目录权限
log_info "设置日志目录权限..."
sudo chown ubuntu:ubuntu "$LOG_DIR"
if [ $? -eq 0 ]; then
    log_success "日志目录权限设置成功"
else
    log_error "日志目录权限设置失败"
    exit 1
fi

# 检查端口占用
log_info "检查端口占用..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "端口8000已被占用，正在停止现有进程..."
    PID=$(lsof -Pi :8000 -sTCP:LISTEN -t)
    log_info "找到占用端口的进程PID: $PID"
    
    # 尝试优雅停止
    sudo pkill -f "gunicorn.*extension_backend" || true
    sleep 2
    
    # 检查是否还有进程占用
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warning "优雅停止失败，强制终止进程..."
        sudo pkill -9 -f "gunicorn.*extension_backend" || true
        sleep 1
    fi
    
    # 最终检查
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_error "无法释放端口8000"
        exit 1
    else
        log_success "端口8000已释放"
    fi
else
    log_success "端口8000可用"
fi

# 检查PID文件
PID_FILE="/tmp/extension_backend.pid"
if [ -f "$PID_FILE" ]; then
    log_warning "发现旧的PID文件，正在清理..."
    rm -f "$PID_FILE"
    log_success "PID文件清理完成"
fi

# 检查模型文件
log_info "检查模型文件..."
MODEL_DIR="$PROJECT_DIR/models"
if ! check_directory "$MODEL_DIR"; then
    log_warning "模型目录不存在，服务可能无法正常工作"
else
    log_success "模型目录存在: $MODEL_DIR"
fi

# 检查FAISS索引
log_info "检查FAISS索引..."
INDEX_DIR="$PROJECT_DIR/faiss_indexes"
if ! check_directory "$INDEX_DIR"; then
    log_warning "FAISS索引目录不存在，服务可能无法正常工作"
else
    log_success "FAISS索引目录存在: $INDEX_DIR"
fi

# 启动Gunicorn
log_info "启动Extension Backend生产服务..."
log_info "使用配置文件: gunicorn.conf.py"
log_info "PID文件: $PID_FILE"
log_info "日志目录: $LOG_DIR"

# 启动服务
gunicorn app.main:app \
    --config gunicorn.conf.py \
    --pid "$PID_FILE" \
    --daemon

# 检查启动结果
log_info "等待服务启动..."
sleep 10

# 检查PID文件
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    log_info "PID文件创建成功，PID: $PID"
    
    # 等待进程启动
    TIMEOUT=30
    ELAPSED=0
    while [ $ELAPSED -lt $TIMEOUT ]; do
        if ps -p "$PID" > /dev/null 2>&1; then
            log_success "主进程启动成功，PID: $PID"
            break
        fi
        sleep 1
        ELAPSED=$((ELAPSED + 1))
        if [ $((ELAPSED % 5)) -eq 0 ]; then
            log_info "等待主进程启动... ($ELAPSED/$TIMEOUT 秒)"
        fi
    done
    
    if [ $ELAPSED -eq $TIMEOUT ]; then
        log_error "主进程启动超时"
        exit 1
    fi
else
    log_error "服务启动失败，PID文件未创建"
    exit 1
fi

# 等待工作进程启动
log_info "等待工作进程启动..."
sleep 3

# 检查端口监听
log_info "检查端口监听..."
TIMEOUT=30
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_success "端口8000开始监听"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [ $((ELAPSED % 5)) -eq 0 ]; then
        log_info "等待端口监听... ($ELAPSED/$TIMEOUT 秒)"
    fi
done

if [ $ELAPSED -eq $TIMEOUT ]; then
    log_error "端口监听超时"
    exit 1
fi

# 检查服务响应
log_info "检查服务响应..."
TIMEOUT=30
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "健康检查通过"
        break
    elif curl -s http://localhost:8000/ > /dev/null 2>&1; then
        log_success "根路径响应正常"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    if [ $((ELAPSED % 10)) -eq 0 ]; then
        log_info "等待服务响应... ($ELAPSED/$TIMEOUT 秒)"
    fi
done

if [ $ELAPSED -eq $TIMEOUT ]; then
    log_warning "服务响应检查超时，但进程运行正常"
else
    log_success "服务响应正常"
fi

# 显示最终状态
log_success "✅ Extension Backend 生产服务启动完成！✅"
log_info "服务地址: http://localhost:8000"
log_info "API文档: http://localhost:8000/docs"
log_info "健康检查: http://localhost:8000/health"

# 显示进程信息
if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
    PIDS=$(pgrep -f "gunicorn.*extension_backend")
    log_info "运行中的进程PID: $PIDS"
fi

# 显示端口信息
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_info "监听端口: 8000"
fi

# 显示日志文件位置
log_info "服务日志位置: $LOG_DIR"
log_info "可以通过以下命令查看日志:"
log_info "  tail -f $LOG_DIR/gunicorn.log"
log_info "  tail -f $LOG_DIR/access.log"
log_info "  tail -f $LOG_DIR/error.log" 