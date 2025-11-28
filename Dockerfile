FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 环境变量：确保日志打印，并把当前目录加入 Python 路径
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有代码
COPY app/ /app/

# 明确告诉 Zeabur 我们用 5000 端口
EXPOSE 5000

# 启动命令：
# 1. bind 0.0.0.0:5000 -> 强制监听 5000
# 2. --log-level debug -> 开启调试日志，万一报错能看清
# 3. --timeout 120 -> 防止爬虫跑太久超时
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "--log-level", "debug", "main:app"]
