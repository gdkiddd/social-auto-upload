#!/bin/bash
# Social Auto Upload 一键启动脚本 (Shell版本)

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=5409
FRONTEND_PORT=5173

# 打印函数
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}============================================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}============================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 清理端口
kill_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口 $port 已被占用，正在清理..."
        lsof -ti:$port | xargs kill -9 2>/dev/null
        sleep 2
    fi
}

# 清理函数
cleanup() {
    print_header "正在停止服务"
    jobs -p | xargs -r kill 2>/dev/null
    print_success "所有服务已停止"
    exit 0
}

# 捕获 Ctrl+C
trap cleanup SIGINT SIGTERM

# 主函数
main() {
    print_header "Social Auto Upload 一键启动"

    # 检查并清理端口
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT

    # 检查前端依赖
    if [ ! -d "$PROJECT_DIR/sau_frontend/node_modules" ]; then
        print_warning "前端依赖未安装，正在安装..."
        cd "$PROJECT_DIR/sau_frontend"
        npm install
        print_success "前端依赖安装完成"
        cd "$PROJECT_DIR"
    fi

    print_info "后端端口: $BACKEND_PORT"
    print_info "前端端口: $FRONTEND_PORT"

    # 启动后端
    print_info "正在启动后端服务器..."
    cd "$PROJECT_DIR"
    python sau_backend.py &
    BACKEND_PID=$!
    print_success "后端服务器已启动 (PID: $BACKEND_PID)"

    # 等待后端启动
    sleep 3

    # 启动前端
    print_info "正在启动前端开发服务器..."
    cd "$PROJECT_DIR/sau_frontend"
    npm run dev &
    FRONTEND_PID=$!
    print_success "前端开发服务器已启动 (PID: $FRONTEND_PID)"

    # 等待前端启动
    sleep 5

    # 打开浏览器
    print_header "打开浏览器"
    print_info "访问地址: http://localhost:$FRONTEND_PORT"
    if command -v open >/dev/null 2>&1; then
        open "http://localhost:$FRONTEND_PORT"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:$FRONTEND_PORT"
    fi
    print_success "浏览器已打开"

    # 显示运行信息
    print_header "系统运行中"
    print_info "后端地址: http://localhost:$BACKEND_PORT"
    print_info "前端地址: http://localhost:$FRONTEND_PORT"
    echo -e "${GREEN}按 Ctrl+C 停止所有服务${NC}"
    echo ""

    # 等待后台进程
    wait
}

# 运行主函数
main
