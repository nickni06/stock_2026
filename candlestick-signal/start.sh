#!/bin/bash
set -e

cd /workspace/candlestick-signal

# 自动安装缺失的依赖
pip install -q -r requirements.txt 2>/dev/null || true

exec python app.py 2>&1