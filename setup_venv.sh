#!/bin/bash
# 创建并激活 Python 虚拟环境的脚本

set -e  # 遇到错误立即退出

echo "🐍 Python 虚拟环境设置"
echo "========================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 虚拟环境路径
VENV_DIR="$SCRIPT_DIR/venv"

# 检查 Python 3.13
if ! command -v python3.13 &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ 未找到 Python 3，请先安装 Python${NC}"
        echo "建议: brew install python@3.13"
        exit 1
    fi
    PYTHON_CMD=python3
else
    PYTHON_CMD=python3.13
fi

echo -e "${GREEN}✅ 使用 Python: $PYTHON_CMD${NC}"
$PYTHON_CMD --version
echo ""

# 检查是否已存在虚拟环境
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境已存在: $VENV_DIR${NC}"
    read -p "是否删除并重新创建? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "删除旧虚拟环境..."
        rm -rf "$VENV_DIR"
    else
        echo "使用现有虚拟环境"
    fi
fi

# 创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ 虚拟环境创建成功${NC}"
fi

# 激活虚拟环境
echo ""
echo "激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 升级 pip
echo ""
echo "升级 pip 到最新版本..."
pip install --upgrade pip setuptools wheel

# 安装依赖
echo ""
echo "安装项目依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${YELLOW}⚠️  未找到 requirements.txt${NC}"
fi

# 安装 playwright 浏览器（如果需要）
if command -v playwright &> /dev/null; then
    echo ""
    echo "安装 Playwright 浏览器..."
    playwright install chromium
    echo -e "${GREEN}✅ Playwright 浏览器安装完成${NC}"
fi

# 保存激活脚本
echo ""
echo "创建便捷激活脚本..."

# Zsh 激活脚本
cat > activate.sh << 'EOF'
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
EOF

chmod +x activate.sh
echo -e "${GREEN}✅ 激活脚本已创建: ./activate.sh${NC}"

# 显示总结
echo ""
echo "======================================"
echo -e "${GREEN}🎉 设置完成！${NC}"
echo "======================================"
echo ""
echo "虚拟环境位置: $VENV_DIR"
echo ""
echo "接下来的步骤："
echo ""
echo "1️⃣  激活虚拟环境："
echo "   source venv/bin/activate"
echo "   或者"
echo "   ./activate.sh"
echo ""
echo "2️⃣  运行项目："
echo "   python auto_upload.py"
echo ""
echo "3️⃣  退出虚拟环境："
echo "   deactivate"
echo ""
echo "======================================"
