#!/bin/bash
set -e

cd /workspace/candlestick-signal

# 云沙箱环境每次重置会清空 pip 包，需要重新安装
pip install -q flask flask-cors akshare pandas numpy 2>/dev/null

# 清理旧进程，确保端口释放
fuser -k 5000/tcp 2>/dev/null || true
sleep 1

exec python app.py 2>&1