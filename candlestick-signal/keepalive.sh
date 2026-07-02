#!/bin/bash
# 保活脚本 - 每3分钟访问一次 Flask 服务，防止沙箱空闲回收；服务挂了自动重启
URL="http://localhost:5000/api/patterns"
APP_DIR="/workspace/candlestick-signal"
APP_FILE="$APP_DIR/app.py"
LOG_FILE="/tmp/flask.log"
PACKAGES=("flask" "flask-cors" "pandas" "numpy" "akshare" "requests")

while true; do
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null)

    if [ "$http_code" != "200" ]; then
        # 服务挂了，先杀旧进程
        pkill -f "app.py" 2>/dev/null
        sleep 1

        # 检查并安装缺失的包
        for pkg in "${PACKAGES[@]}"; do
            python3 -c "import $pkg" 2>/dev/null || pip install "$pkg" --quiet
        done

        # 重启 Flask
        cd "$APP_DIR" && python app.py > "$LOG_FILE" 2>&1 &
        sleep 3
    fi

    sleep 180
done