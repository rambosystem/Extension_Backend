# Extension Backend 生产环境脚本使用说明

## 概述

本目录包含了一套完整的生产环境管理脚本，用于管理 Extension Backend 服务的启动、停止、重启和状态监控。

## 脚本列表

| 脚本名称 | 功能 | 使用场景 |
|----------|------|----------|
| `start_production.sh` | 启动生产服务 | 首次部署、服务停止后重启 |
| `stop_production.sh` | 停止生产服务 | 维护、更新、故障处理 |
| `restart_production.sh` | 重启生产服务 | 配置更新、故障恢复 |
| `status_production.sh` | 检查服务状态 | 日常监控、故障诊断 |

## 使用方法

### 1. 启动服务

```bash
./start_production.sh
```

**功能特性:**
- ✅ 详细的启动日志和检查
- ✅ 自动检查依赖和环境
- ✅ 智能端口冲突处理
- ✅ 服务启动验证
- ✅ 彩色日志输出

**启动流程:**
1. 检查项目目录和虚拟环境
2. 验证Python包依赖
3. 检查配置文件和模型文件
4. 创建日志目录并设置权限
5. 处理端口冲突
6. 启动Gunicorn服务
7. 验证服务响应

### 2. 停止服务

```bash
./stop_production.sh
```

**功能特性:**
- ✅ 优雅停止（SIGTERM）
- ✅ 强制停止（SIGKILL）
- ✅ 进程清理和PID文件管理
- ✅ 端口释放检查

**停止流程:**
1. 检查PID文件和进程状态
2. 发送优雅停止信号
3. 等待进程停止（最多30秒）
4. 强制终止超时进程
5. 清理PID文件
6. 验证端口释放

### 3. 重启服务

```bash
./restart_production.sh
```

**功能特性:**
- ✅ 完整的停止-启动流程
- ✅ 服务状态验证
- ✅ 用户确认机制
- ✅ 详细的进度日志

**重启流程:**
1. 停止现有服务
2. 等待服务完全停止
3. 检查端口释放
4. 启动新服务
5. 验证服务状态
6. 检查服务响应

### 4. 检查状态

```bash
./status_production.sh
```

**功能特性:**
- ✅ 全面的系统状态检查
- ✅ 服务运行状态监控
- ✅ 资源使用情况
- ✅ 网络连接检查
- ✅ 日志文件分析

**检查项目:**
- 系统信息（主机名、OS、内核版本）
- 资源使用（CPU、内存、磁盘）
- 项目文件完整性
- 虚拟环境状态
- 模型和索引文件
- 服务进程状态
- 端口监听状态
- 服务响应检查
- 日志文件状态
- 网络连接状态

## 日志系统

### 日志级别

| 级别 | 颜色 | 说明 |
|------|------|------|
| INFO | 蓝色 | 一般信息 |
| SUCCESS | 绿色 | 成功操作 |
| WARNING | 黄色 | 警告信息 |
| ERROR | 红色 | 错误信息 |

### 日志文件位置

```
/var/log/extension_backend/
├── gunicorn.log    # Gunicorn主日志
├── access.log      # 访问日志
└── error.log       # 错误日志
```

### 查看日志命令

```bash
# 实时查看主日志
tail -f /var/log/extension_backend/gunicorn.log

# 实时查看访问日志
tail -f /var/log/extension_backend/access.log

# 实时查看错误日志
tail -f /var/log/extension_backend/error.log

# 查看最近的错误
tail -20 /var/log/extension_backend/error.log
```

## 故障排除

### 常见问题

#### 1. 端口被占用

**现象:** 启动时提示端口8000被占用

**解决方案:**
```bash
# 查看占用端口的进程
lsof -i :8000

# 停止占用端口的进程
sudo pkill -f "进程名"

# 或者重启服务
./restart_production.sh
```

#### 2. 虚拟环境问题

**现象:** 提示虚拟环境不存在或Python包缺失

**解决方案:**
```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 3. 权限问题

**现象:** 无法创建日志目录或写入文件

**解决方案:**
```bash
# 创建日志目录
sudo mkdir -p /var/log/extension_backend

# 设置权限
sudo chown ubuntu:ubuntu /var/log/extension_backend
```

#### 4. 模型文件缺失

**现象:** 服务启动但Term Match功能不可用

**解决方案:**
```bash
# 检查模型目录
ls -la models/

# 下载模型文件
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-en-v1.5')"
```

### 诊断命令

```bash
# 检查服务状态
./status_production.sh

# 检查进程
ps aux | grep gunicorn

# 检查端口
netstat -tuln | grep 8000

# 检查日志
tail -f /var/log/extension_backend/gunicorn.log

# 测试服务响应
curl http://localhost:8000/health
```

## 性能监控

### 系统资源监控

```bash
# 查看CPU和内存使用
htop

# 查看磁盘使用
df -h

# 查看网络连接
netstat -tuln
```

### 服务性能监控

```bash
# 查看Gunicorn进程状态
ps aux | grep gunicorn

# 查看服务统计信息
curl http://localhost:8000/term-match/stats

# 监控日志文件大小
watch -n 5 'ls -lh /var/log/extension_backend/'
```

## 安全建议

### 1. 文件权限

```bash
# 设置脚本权限
chmod 755 *.sh

# 设置项目目录权限
chmod 755 /home/ubuntu/project/extension_backend

# 保护配置文件
chmod 600 gunicorn.conf.py
```

### 2. 网络安全

```bash
# 配置防火墙
sudo ufw allow 8000

# 限制访问IP（可选）
sudo ufw allow from 192.168.1.0/24 to any port 8000
```

### 3. 日志轮转

```bash
# 创建logrotate配置
sudo tee /etc/logrotate.d/extension_backend << EOF
/var/log/extension_backend/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        kill -USR1 \$(cat /tmp/extension_backend.pid)
    endscript
}
EOF
```

## 自动化部署

### 1. 系统服务配置

```bash
# 创建systemd服务文件
sudo tee /etc/systemd/system/extension-backend.service << EOF
[Unit]
Description=Extension Backend Service
After=network.target

[Service]
Type=forking
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/project/extension_backend
ExecStart=/home/ubuntu/project/extension_backend/start_production.sh
ExecStop=/home/ubuntu/project/extension_backend/stop_production.sh
ExecReload=/home/ubuntu/project/extension_backend/restart_production.sh
PIDFile=/tmp/extension_backend.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
sudo systemctl enable extension-backend
sudo systemctl start extension-backend
```

### 2. 监控脚本

```bash
# 创建监控脚本
cat > monitor.sh << 'EOF'
#!/bin/bash
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "$(date): Service down, restarting..." >> /var/log/extension_backend/monitor.log
    ./restart_production.sh
fi
EOF

chmod +x monitor.sh

# 添加到crontab
echo "*/5 * * * * /home/ubuntu/project/extension_backend/monitor.sh" | crontab -
```

## 更新和维护

### 1. 代码更新

```bash
# 停止服务
./stop_production.sh

# 更新代码
git pull origin main

# 更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 重启服务
./restart_production.sh
```

### 2. 配置更新

```bash
# 编辑配置文件
vim gunicorn.conf.py

# 重启服务
./restart_production.sh
```

### 3. 日志清理

```bash
# 清理旧日志
find /var/log/extension_backend -name "*.log.*" -mtime +30 -delete

# 压缩日志
gzip /var/log/extension_backend/*.log
```

## 联系支持

如果遇到问题，请：

1. 运行 `./status_production.sh` 获取详细状态信息
2. 查看相关日志文件
3. 检查系统资源使用情况
4. 联系技术支持团队并提供错误信息 