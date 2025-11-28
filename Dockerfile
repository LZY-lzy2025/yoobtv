FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# PYTHONUNBUFFERED=1: 确保日志直接输出，不被缓存，方便排查报错
# PYTHONPATH=/app: 确保 Python 能找到 base 模块
# PORT=8080: 设置默认端口，如果 Zeabur 没有提供 PORT 变量，则默认使用 8080
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY app/ /app/

# 暴露端口 (仅作声明)
EXPOSE 8080

# 启动命令 (直接在这里写，避免 Windows 换行符问题)
# 使用 shell 格式 (不带中括号)，以便读取 $PORT 变量
CMD gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 --access-logfile - --error-logfile - main:app
