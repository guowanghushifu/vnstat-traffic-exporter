#!/bin/bash

# vnstat流量导出器启动脚本

# 设置默认环境变量（可以根据需要修改）
export WEBHOOK_PATH="${WEBHOOK_PATH:-/webhook/secret-0c68fb14-bb0d-41ca-a53f-a8ba0ea08fae}"
export START_DAY="${START_DAY:-19}"
export PORT="${PORT:-50000}"

# 检查Python3是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到python3，请先安装Python3"
    exit 1
fi

# 检查vnstat是否安装
if ! command -v vnstat &> /dev/null; then
    echo "错误: 未找到vnstat，请先安装vnstat"
    echo "Ubuntu/Debian: sudo apt-get install vnstat"
    echo "CentOS/RHEL: sudo yum install vnstat"
    echo "macOS: brew install vnstat"
    exit 1
fi

# 检查Flask是否安装
if ! python3 -c "import flask" 2>/dev/null; then
    echo "正在安装Python依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败"
        exit 1
    fi
fi

echo "=== vnstat流量导出器 ==="
echo "Webhook路径: $WEBHOOK_PATH"
echo "起始日期: 每月${START_DAY}号"
echo "服务端口: $PORT"
echo "========================"
echo ""

# 启动脚本
python3 vnstat_traffic_exporter.py 