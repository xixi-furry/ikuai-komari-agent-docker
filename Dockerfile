# 使用官方Python运行时作为基础镜像
FROM python:3.9-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 设置工作目录
WORKDIR /app

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建日志目录并设置权限
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 设置默认环境变量
ENV IKUAI_BASE_URL="http://192.168.1.1" \
    IKUAI_USERNAME="admin" \
    IKUAI_PASSWORD="admin" \
    IKUAI_TIMEOUT="10" \
    KOMARI_ENDPOINT="https://komari.server.com" \
    KOMARI_TOKEN="your_token_here" \
    KOMARI_WEBSOCKET_INTERVAL="1.0" \
    KOMARI_BASIC_INFO_INTERVAL="5" \
    KOMARI_IGNORE_UNSAFE_CERT="False" \
    LOG_LEVEL="INFO" \
    LOG_FILE="/app/logs/ikuai_agent.log" \
    LOG_MAX_BYTES="10485760" \
    LOG_BACKUP_COUNT="3"

# 启动命令
CMD ["python", "ikuai_komari_agent.py"]
