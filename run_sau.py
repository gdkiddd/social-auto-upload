#!/usr/bin/env python3
"""
Social Auto Upload 一键启动脚本
同时启动后端服务器和前端开发服务器，并自动打开浏览器
"""
import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path
from multiprocessing import Process
import signal

# 项目根目录
BASE_DIR = Path(__file__).parent.resolve()

# 配置
BACKEND_PORT = 5409
FRONTEND_PORT = 5173
FRONTEND_DEV_URL = f"http://localhost:{FRONTEND_PORT}"

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    """打印成功信息"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_info(text):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def print_warning(text):
    """打印警告"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    """打印错误"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def check_port_in_use(port):
    """检查端口是否被占用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result == 0

def kill_process_on_port(port):
    """杀死占用端口的进程"""
    try:
        if sys.platform == 'darwin':  # macOS
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    subprocess.run(['kill', '-9', pid])
                    print_info(f"已杀死端口 {port} 的进程 (PID: {pid})")
        elif sys.platform.startswith('linux'):
            result = subprocess.run(
                ['fuser', '-k', f'{port}/tcp'],
                capture_output=True
            )
    except Exception as e:
        print_warning(f"清理端口 {port} 失败: {e}")

def start_backend():
    """启动后端服务器"""
    print_header("启动后端服务器")

    # 检查端口
    if check_port_in_use(BACKEND_PORT):
        print_warning(f"端口 {BACKEND_PORT} 已被占用，尝试清理...")
        kill_process_on_port(BACKEND_PORT)
        time.sleep(2)

    print_info(f"后端端口: {BACKEND_PORT}")
    print_info(f"数据库: {BASE_DIR / 'db' / 'database.db'}")

    # 启动后端
    backend_cmd = [sys.executable, 'sau_backend.py']
    print_info(f"启动命令: {' '.join(backend_cmd)}")

    process = subprocess.Popen(
        backend_cmd,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

    # 实时打印后端日志
    for line in process.stdout:
        print(f"  {line}", end='')
        if 'Running on' in line:
            print_success(f"后端服务器已启动: http://localhost:{BACKEND_PORT}")
            break

    return process

def start_frontend():
    """启动前端开发服务器"""
    print_header("启动前端开发服务器")

    # 检查端口
    if check_port_in_use(FRONTEND_PORT):
        print_warning(f"端口 {FRONTEND_PORT} 已被占用，尝试清理...")
        kill_process_on_port(FRONTEND_PORT)
        time.sleep(2)

    frontend_dir = BASE_DIR / 'sau_frontend'

    # 检查 node_modules
    if not (frontend_dir / 'node_modules').exists():
        print_warning("node_modules 不存在，正在安装依赖...")
        subprocess.run(
            ['npm', 'install'],
            cwd=frontend_dir,
            check=True
        )
        print_success("依赖安装完成")

    print_info(f"前端端口: {FRONTEND_PORT}")
    print_info(f"启动命令: npm run dev")

    # 启动前端
    process = subprocess.Popen(
        ['npm', 'run', 'dev'],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )

    return process

def open_browser():
    """打开浏览器"""
    time.sleep(3)  # 等待服务器启动

    print_header("打开浏览器")
    print_info(f"访问地址: {FRONTEND_DEV_URL}")

    webbrowser.open(FRONTEND_DEV_URL)
    print_success("浏览器已打开")

def main():
    """主函数"""
    print_header("Social Auto Upload 一键启动")

    # 存储子进程
    processes = []

    try:
        # 1. 启动后端
        backend_process = start_backend()
        processes.append(('Backend', backend_process))

        # 等待后端启动
        time.sleep(2)

        # 2. 启动前端
        frontend_process = start_frontend()
        processes.append(('Frontend', frontend_process))

        # 3. 打开浏览器
        open_browser()

        # 4. 显示运行信息
        print_header("系统运行中")
        print_info(f"后端地址: http://localhost:{BACKEND_PORT}")
        print_info(f"前端地址: {FRONTEND_DEV_URL}")
        print(f"\n{Colors.GREEN}按 Ctrl+C 停止所有服务{Colors.END}\n")

        # 等待进程
        backend_process.wait()

    except KeyboardInterrupt:
        print_header("正在停止服务")

        # 停止所有进程
        for name, process in processes:
            try:
                print_info(f"停止 {name}...")
                process.terminate()
                process.wait(timeout=5)
                print_success(f"{name} 已停止")
            except subprocess.TimeoutExpired:
                print_warning(f"{name} 未能正常停止，强制杀死...")
                process.kill()
            except Exception as e:
                print_error(f"停止 {name} 时出错: {e}")

        print_success("所有服务已停止")
        sys.exit(0)

    except Exception as e:
        print_error(f"启动失败: {e}")
        # 清理进程
        for name, process in processes:
            try:
                process.kill()
            except:
                pass
        sys.exit(1)

if __name__ == '__main__':
    main()
