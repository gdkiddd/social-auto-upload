#!/bin/bash
# 激活项目虚拟环境

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"

echo "✅ 虚拟环境已激活"
echo "Python: $(python --version)"
echo "项目目录: $SCRIPT_DIR"
echo ""
echo "现在可以运行项目命令："
echo "  python auto_upload.py"
echo "  python run.py"
echo ""
echo "退出虚拟环境: deactivate"
