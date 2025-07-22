FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    vnstat \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装Python包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY vnstat_traffic_exporter.py .

# 创建vnstat数据目录并设置权限
RUN mkdir -p /var/lib/vnstat && \
    chmod 755 /var/lib/vnstat

# 设置环境变量默认值
ENV WEBHOOK_PATH=/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae
ENV START_DAY=1
ENV PORT=50000

# 暴露端口
EXPOSE 50000

# 设置启动命令
CMD ["python3", "vnstat_traffic_exporter.py"] 