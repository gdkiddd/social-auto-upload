#!/bin/bash
# 清理 Python 缓存
echo "清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "✅ 缓存已清理"
echo "请重新运行: python3 run.py"
