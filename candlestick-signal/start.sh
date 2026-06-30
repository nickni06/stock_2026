#!/bin/bash
cd /workspace/candlestick-signal
pip install -r requirements.txt -q 2>/dev/null
python app.py 2>&1