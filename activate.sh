#!/bin/bash
# 激活项目虚拟环境（Mac兼容版本）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# 检查虚拟环境是否存在
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ 虚拟环境不存在: $VENV_DIR"
    echo "请先运行: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

echo "✅ 虚拟环境已激活"

# 显示Python版本
if command -v python &> /dev/null; then
    echo "Python: $(python --version 2>&1)"
    echo "Python路径: $(which python)"
elif command -v python3 &> /dev/null; then
    echo "Python: $(python3 --version 2>&1)"
    echo "Python路径: $(which python3)"
    echo "ℹ️  提示: 本系统使用 'python3' 命令"
else
    echo "❌ 未找到Python命令"
fi

echo "项目目录: $SCRIPT_DIR"
echo ""
echo "现在可以运行项目命令："
echo "  python auto_upload.py"
echo "  python run.py"
echo ""
echo "或者（如果python命令不可用）:"
echo "  python3 auto_upload.py"
echo "  python3 run.py"
echo ""
echo "退出虚拟环境: deactivate"
