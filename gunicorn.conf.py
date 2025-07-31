# Gunicorn配置文件 - 生产环境
import multiprocessing
import os

# 服务器配置
bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"

# 进程配置
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# 日志配置
accesslog = "/var/log/extension_backend/access.log"
errorlog = "/var/log/extension_backend/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 进程命名
proc_name = "extension_backend"

# 预加载应用
preload_app = True

# 环境变量
raw_env = [
    "PYTHONPATH=/home/ubuntu/project/extension_backend",
]


def when_ready(server):
    """服务器启动完成后的回调"""
    server.log.info("Extension Backend is ready to serve requests!")


def worker_int(worker):
    """工作进程中断时的回调"""
    worker.log.info("Worker received INT or QUIT signal")


def pre_fork(server, worker):
    """fork工作进程前的回调"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def post_fork(server, worker):
    """fork工作进程后的回调"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def post_worker_init(worker):
    """工作进程初始化后的回调"""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)
