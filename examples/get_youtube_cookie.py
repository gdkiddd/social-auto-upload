#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Cookie 保存工具 - 简化版

使用方法：
1. 先在 Chrome 浏览器中登录 YouTube Studio
2. 运行此脚本，输入 'yes' 读取 cookie 并保存
"""

import sqlite3
import shutil
import tempfile
from pathlib import Path
import json
import sys

from myUtils.account_manager import get_current_account, get_account_cookie_path


def get_chrome_cookie_path():
    """获取 Chrome 的 cookie 数据库路径"""
    system = sys.platform

    if system == 'darwin':  # macOS
        possible_paths = [
            Path.home() / 'Library/Application Support/Google/Chrome/Default/Cookies',
            Path.home() / 'Library/Application Support/Google/Chrome/Profile 1/Cookies',
            Path.home() / 'Library/Application Support/Google/Chrome/Profile 2/Cookies',
        ]
    elif system == 'win32':
        possible_paths = [
            Path.home() / 'AppData/Local/Google/Chrome/User Data/Default/Cookies',
            Path.home() / 'AppData/Local/Google/Chrome/User Data/Profile 1/Cookies',
        ]
    else:  # Linux
        possible_paths = [
            Path.home() / '.config/google-chrome/Default/Cookies',
            Path.home() / '.config/google-chrome/Profile 1/Cookies',
        ]

    # 找到第一个存在的路径
    for path in possible_paths:
        if path.exists():
            return path

    return None


def read_cookies_from_db(cookie_db_path):
    """从 Chrome cookie 数据库中读取 YouTube 相关的 cookie"""
    print(f"📂 正在读取 Chrome cookie...")
    print(f"   路径: {cookie_db_path}")

    # 创建临时数据库副本
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db_path = Path(temp_db.name)

    try:
        shutil.copy2(cookie_db_path, temp_db_path)
        print("✅ Cookie 数据库复制成功")
    except Exception as e:
        print(f"❌ 复制数据库失败: {e}")
        print()
        print("💡 可能的原因：")
        print("   1. Chrome 浏览器正在运行")
        print("   2. 请完全关闭 Chrome 浏览器后重试")
        return None

    # 连接到数据库
    try:
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # 先检查表结构
        cursor.execute("PRAGMA table_info(cookies)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"   数据库列: {', '.join(columns)}")

        # 根据列名构建查询
        if 'host_key' in columns:
            # Chrome 新版本使用 host_key
            query = """
                SELECT name, value, host_key, path,
                       creation_utc, expires_utc, is_secure, is_httponly, samesite
                FROM cookies
                WHERE host_key LIKE '%youtube%' OR host_key LIKE '%google%'
                ORDER BY creation_utc DESC
            """
            use_host_key = True
        elif 'host' in columns:
            # 旧版本可能使用 host
            query = """
                SELECT name, value, host, path,
                       creation_utc, expires_utc, is_secure, is_httponly, samesite
                FROM cookies
                WHERE host LIKE '%youtube%' OR host LIKE '%google%'
                ORDER BY creation_utc DESC
            """
            use_host_key = False
        else:
            print("❌ 无法识别数据库结构")
            return None

        cursor.execute(query)
        rows = cursor.fetchall()

        cookies = []
        seen_cookies = set()  # 用于去重

        for row in rows:
            if use_host_key:
                name, value, host_key, path, creation_utc, expires_utc, is_secure, is_httponly, samesite = row
                # 转换 host_key 为域名
                try:
                    # host_key 格式: *.youtube.com 或 *.google.com
                    if host_key.startswith('.'):
                        domain = host_key
                    else:
                        # 如果是编码的 host_key，尝试提取域名
                        parts = host_key.split('.')
                        if len(parts) > 1:
                            domain = '.'.join(parts[1:])  # 去掉前缀
                        else:
                            domain = host_key
                except:
                    domain = host_key
            else:
                name, value, host, path, creation_utc, expires_utc, is_secure, is_httponly, samesite = row
                domain = host

            # 去重：使用 (name, domain) 作为唯一标识
            cookie_id = (name, domain)
            if cookie_id in seen_cookies:
                continue
            seen_cookies.add(cookie_id)

            # 处理过期时间（转换为整数）
            expires = -1
            if expires_utc and expires_utc > 0:
                expires = int(expires_utc)

            # 处理 sameSite
            same_site = 'None'
            if samesite:
                if isinstance(samesite, int):
                    if samesite == 0:
                        same_site = 'Strict'
                    elif samesite == 1:
                        same_site = 'Lax'
                    elif samesite == 2:
                        same_site = 'None'
                elif isinstance(samesite, str):
                    same_site = samesite

            cookie = {
                'name': name,
                'value': value,
                'domain': domain,
                'path': path,
                'expires': expires,
                'httpOnly': bool(is_httponly),
                'secure': bool(is_secure),
                'sameSite': same_site
            }
            cookies.append(cookie)

        conn.close()
        print(f"✅ 读取到 {len(cookies)} 个 cookie（已去重）")
        return cookies

    except Exception as e:
        print(f"❌ 读取数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # 删除临时文件
        try:
            temp_db_path.unlink()
        except:
            pass


def save_cookies(cookies, account_file):
    """保存 cookie 到 JSON 文件"""
    if not cookies or len(cookies) == 0:
        print("❌ 没有找到任何 cookie")
        return False

    cookie_data = {
        'cookies': cookies,
        'origins': [
            {
                'origin': 'https://studio.youtube.com',
                'localStorage': [],
                'sessionStorage': []
            },
            {
                'origin': 'https://www.youtube.com',
                'localStorage': [],
                'sessionStorage': []
            }
        ]
    }

    try:
        # 确保目录存在
        account_file.parent.mkdir(parents=True, exist_ok=True)

        # 写入 JSON 文件
        with open(account_file, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, indent=2, ensure_ascii=False)

        print()
        print("=" * 60)
        print(f"✅ Cookie 已保存到: {account_file}")
        print(f"📊 共保存 {len(cookies)} 个 cookie")
        print("=" * 60)
        print()
        print("💡 下一步：")
        print("   python examples/upload_video_to_youtube.py")
        print()
        return True

    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    current_account = get_current_account()
    account_file = get_account_cookie_path(current_account, 'youtube')

    print("=" * 60)
    print("YouTube Cookie 保存工具")
    print("=" * 60)
    print()
    print(f"📋 当前账号: {current_account}")
    print(f"📁 保存路径: {account_file}")
    print()
    print("使用说明：")
    print("=" * 60)
    print("1. 请确保已在 Chrome 浏览器中登录 YouTube Studio")
    print("   https://studio.youtube.com")
    print()
    print("2. 如果未登录，请先登录，然后再运行此脚本")
    print()
    print("3. 如果 Chrome 正在运行，请先完全关闭 Chrome")
    print("=" * 60)
    print()

    # 检查用户是否要继续
    try:
        choice = input("是否继续读取 cookie？(yes/no): ").strip().lower()
    except KeyboardInterrupt:
        print()
        print("❌ 已取消操作")
        return False

    if choice not in ['yes', 'y']:
        print("❌ 已取消操作")
        return False

    # 获取 Chrome cookie 路径
    cookie_db_path = get_chrome_cookie_path()

    if not cookie_db_path:
        print()
        print("❌ 未找到 Chrome cookie 数据库")
        print()
        print("💡 请确保：")
        print("   1. 已安装 Chrome 浏览器")
        print("   2. 至少登录过一次 YouTube Studio")
        return False

    # 读取 cookie
    cookies = read_cookies_from_db(cookie_db_path)

    if cookies is None or len(cookies) == 0:
        print()
        print("❌ 未找到任何 YouTube 相关 cookie")
        print()
        print("💡 建议：")
        print("   1. 在 Chrome 中重新登录 YouTube Studio")
        print("   2. 确保完全登录成功")
        print("   3. 完全关闭 Chrome 后重试")
        return False

    # 保存到 JSON
    return save_cookies(cookies, account_file)


if __name__ == '__main__':
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print()
        print("❌ 用户取消操作")
        exit(1)
    except Exception as e:
        print()
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
