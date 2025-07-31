#!/bin/bash

# 生产环境状态检查脚本
# 使用方法: ./status_production.sh

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${CYAN}=== $1 ===${NC}"
}

# 检查函数
check_service_status() {
    local service_name="$1"
    local pattern="$2"
    
    if pgrep -f "$pattern" > /dev/null; then
        local pids=$(pgrep -f "$pattern")
        log_success "$service_name 运行中 (PID: $pids)"
        return 0
    else
        log_error "$service_name 未运行"
        return 1
    fi
}

check_port_status() {
    local port="$1"
    local service_name="$2"
    
    if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pids=$(lsof -Pi :"$port" -sTCP:LISTEN -t | tr '\n' ' ')
        log_success "$service_name 端口 $port 监听中 (PID: $pids)"
        return 0
    else
        log_error "$service_name 端口 $port 未监听"
        return 1
    fi
}

# 开始状态检查
echo
log_header "Extension Backend 生产环境状态检查"
echo "检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo

# 系统信息
log_header "系统信息"
log_info "主机名: $(hostname)"
log_info "操作系统: $(lsb_release -d | cut -f2)"
log_info "内核版本: $(uname -r)"
log_info "CPU架构: $(uname -m)"
log_info "当前用户: $(whoami)"
log_info "当前目录: $(pwd)"

# CPU和内存使用情况
log_header "系统资源"
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEMORY_INFO=$(free -h | grep Mem)
MEMORY_TOTAL=$(echo $MEMORY_INFO | awk '{print $2}')
MEMORY_USED=$(echo $MEMORY_INFO | awk '{print $3}')
MEMORY_FREE=$(echo $MEMORY_INFO | awk '{print $4}')

log_info "CPU使用率: ${CPU_USAGE}%"
log_info "内存使用: $MEMORY_USED / $MEMORY_TOTAL (可用: $MEMORY_FREE)"

# 磁盘使用情况
log_header "磁盘使用"
ROOT_USAGE=$(df -h / | tail -1 | awk '{print $3 " / " $2 " (" $5 " 使用率)"}')
log_info "根目录: $ROOT_USAGE"
HOME_USAGE=$(df -h /home | tail -1 | awk '{print $3 " / " $2 " (" $5 " 使用率)"}')
log_info "Home目录: $HOME_USAGE"

# 项目目录信息
log_header "项目信息"
PROJECT_DIR="/home/ubuntu/project/extension_backend"
if [ -d "$PROJECT_DIR" ]; then
    log_success "项目目录存在: $PROJECT_DIR"
    PROJECT_SIZE=$(du -sh "$PROJECT_DIR" | cut -f1)
    log_info "项目大小: $PROJECT_SIZE"
    
    # 检查关键文件
    if [ -f "$PROJECT_DIR/app/main.py" ]; then
        log_success "主应用文件存在"
    else
        log_error "主应用文件不存在"
    fi
    
    if [ -f "$PROJECT_DIR/gunicorn.conf.py" ]; then
        log_success "Gunicorn配置文件存在"
    else
        log_error "Gunicorn配置文件不存在"
    fi
else
    log_error "项目目录不存在: $PROJECT_DIR"
fi

# 虚拟环境信息
log_header "虚拟环境"
VENV_DIR="$PROJECT_DIR/venv"
if [ -d "$VENV_DIR" ]; then
    log_success "虚拟环境存在: $VENV_DIR"
    if [ -f "$VENV_DIR/bin/python" ]; then
        PYTHON_VERSION=$("$VENV_DIR/bin/python" --version 2>&1)
        log_info "Python版本: $PYTHON_VERSION"
    else
        log_error "虚拟环境中Python不存在"
    fi
else
    log_error "虚拟环境不存在: $VENV_DIR"
fi

# 模型和索引文件
log_header "模型和索引"
MODEL_DIR="$PROJECT_DIR/models"
INDEX_DIR="$PROJECT_DIR/faiss_indexes"

if [ -d "$MODEL_DIR" ]; then
    MODEL_COUNT=$(find "$MODEL_DIR" -type f -name "*.bin" -o -name "*.safetensors" | wc -l)
    log_success "模型目录存在: $MODEL_DIR (文件数: $MODEL_COUNT)"
else
    log_warning "模型目录不存在: $MODEL_DIR"
fi

if [ -d "$INDEX_DIR" ]; then
    INDEX_COUNT=$(find "$INDEX_DIR" -type f -name "*.index" | wc -l)
    log_success "FAISS索引目录存在: $INDEX_DIR (索引数: $INDEX_COUNT)"
else
    log_warning "FAISS索引目录不存在: $INDEX_DIR"
fi

# 服务状态
log_header "服务状态"

# 检查Extension Backend进程
SERVICE_RUNNING=false
if check_service_status "Extension Backend" "gunicorn.*extension_backend"; then
    SERVICE_RUNNING=true
fi

# 检查端口
PORT_LISTENING=false
if check_port_status "8000" "Extension Backend"; then
    PORT_LISTENING=true
fi

# PID文件检查
PID_FILE="/tmp/extension_backend.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        log_success "PID文件存在且有效: $PID"
    else
        log_warning "PID文件存在但进程不存在: $PID"
    fi
else
    log_warning "PID文件不存在: $PID_FILE"
fi

# 服务响应检查
log_header "服务响应"
if [ "$SERVICE_RUNNING" = true ] && [ "$PORT_LISTENING" = true ]; then
    log_info "检查服务响应..."
    
    # 健康检查
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        log_success "健康检查通过: http://localhost:8000/health"
    else
        log_warning "健康检查失败"
    fi
    
    # 根路径检查
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        log_success "根路径响应正常: http://localhost:8000/"
    else
        log_warning "根路径响应失败"
    fi
    
    # API文档检查
    if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
        log_success "API文档可访问: http://localhost:8000/docs"
    else
        log_warning "API文档不可访问"
    fi
    
    # Term Match接口检查
    if curl -s http://localhost:8000/term-match/stats > /dev/null 2>&1; then
        log_success "Term Match接口可访问: http://localhost:8000/term-match/stats"
    else
        log_warning "Term Match接口不可访问"
    fi
else
    log_error "服务未运行或端口未监听，跳过响应检查"
fi

# 日志文件检查
log_header "日志文件"
LOG_DIR="/var/log/extension_backend"
if [ -d "$LOG_DIR" ]; then
    log_success "日志目录存在: $LOG_DIR"
    
    # 检查各种日志文件
    for log_file in "gunicorn.log" "access.log" "error.log"; do
        if [ -f "$LOG_DIR/$log_file" ]; then
            LOG_SIZE=$(du -h "$LOG_DIR/$log_file" | cut -f1)
            LOG_LINES=$(wc -l < "$LOG_DIR/$log_file")
            log_success "$log_file 存在 (大小: $LOG_SIZE, 行数: $LOG_LINES)"
        else
            log_warning "$log_file 不存在"
        fi
    done
    
    # 显示最近的错误日志
    if [ -f "$LOG_DIR/error.log" ]; then
        log_info "最近的错误日志 (最后5行):"
        tail -5 "$LOG_DIR/error.log" | while read line; do
            echo "  $line"
        done
    fi
else
    log_error "日志目录不存在: $LOG_DIR"
fi

# 网络连接检查
log_header "网络连接"
log_info "检查网络连接状态..."
if netstat -tuln | grep ":8000" > /dev/null; then
    log_success "端口8000正在监听"
    netstat -tuln | grep ":8000" | while read line; do
        echo "  $line"
    done
else
    log_error "端口8000未监听"
fi

# 进程详细信息
log_header "进程详细信息"
if pgrep -f "gunicorn.*extension_backend" > /dev/null; then
    PIDS=$(pgrep -f "gunicorn.*extension_backend")
    log_info "Extension Backend进程信息:"
    for pid in $PIDS; do
        echo "  PID: $pid"
        ps -p "$pid" -o pid,ppid,cmd,etime,pcpu,pmem --no-headers | while read line; do
            echo "    $line"
        done
    done
else
    log_error "未找到Extension Backend进程"
fi

# 总结
log_header "状态总结"
if [ "$SERVICE_RUNNING" = true ] && [ "$PORT_LISTENING" = true ]; then
    log_success "✅ Extension Backend 服务运行正常"
    log_info "服务地址: http://localhost:8000"
    log_info "API文档: http://localhost:8000/docs"
    log_info "健康检查: http://localhost:8000/health"
else
    log_error "❌ Extension Backend 服务运行异常"
    log_info "建议执行: ./restart_production.sh"
fi

echo
log_info "检查完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo 