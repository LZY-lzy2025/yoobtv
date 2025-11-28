FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 关键：设置 Python 环境变量
# PYTHONUNBUFFERED=1 确保日志直接输出，方便 Zeabur 调试
# PYTHONPATH=/app 确保脚本能找到 base.spider
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY app/ /app/

# 给启动脚本执行权限
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露端口 (Zeabur 会优先读取这个，但实际绑定由 entrypoint 处理)
EXPOSE 8080

# 使用 Shell 脚本启动，以便处理环境变量
ENTRYPOINT ["/entrypoint.sh"]
