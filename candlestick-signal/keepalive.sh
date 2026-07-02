#!/bin/bash
# 保活脚本 - 每3分钟访问一次 Flask 服务，防止沙箱空闲回收
URL="http://localhost:5000/api/patterns"
while true; do
    curl -s -o /dev/null -w "%{http_code}" "$URL" > /dev/null 2>&1
    sleep 180
done