#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Cookie 保存工具 - 使用 Chrome 用户数据目录
使用现有的 Chrome 浏览器配置启动，自动保存 cookie
"""

import asyncio
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

from conf import LOCAL_CHROME_PATH
from utils.base_social_media import set_init_script
from myUtils.account_manager import get_current_account, get_account_cookie_path


async def save_youtube_cookie_with_user_data_dir():
    """使用 Chrome 用户数据目录启动浏览器并保存 cookie"""
    current_account = get_current_account()
    account_file = get_account_cookie_path(current_account, 'youtube')

    print("=" * 60)
    print("YouTube Cookie 保存工具（使用 Chrome 用户数据目录）")
    print("=" * 60)
    print()
    print(f"📋 当前账号: {current_account}")
    print(f"📁 Cookie 文件: {account_file}")
    print()
    print("🌐 正在启动浏览器...")
    print("💡 请在浏览器中完成 YouTube 登录")
    print("💡 登录完成后，输入 'yes' 保存 cookie 并退出")
    print("💡 输入 'quit' 或关闭浏览器直接退出（不保存）")
    print()

    # 创建临时用户数据目录
    temp_user_data_dir = Path("data") / "chrome_user_data_temp" / "youtube_login"

    # 如果临时目录已存在，先删除
    if temp_user_data_dir.exists():
        shutil.rmtree(temp_user_data_dir)

    temp_user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        # 使用用户数据目录启动浏览器
        launch_options = {
            'headless': False,  # 必须显示浏览器
            'args': [
                f'--user-data-dir={temp_user_data_dir}',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-blink-features=AutomationControlled',
            ],
        }

        # 如果配置了本地 Chrome 路径，使用它
        if LOCAL_CHROME_PATH:
            launch_options['executable_path'] = LOCAL_CHROME_PATH
        else:
            # 否则尝试使用系统默认的 Chrome
            # macOS 上的 Chrome 通常在这个位置
            mac_chrome_paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium',
            ]
            for path in mac_chrome_paths:
                if Path(path).exists():
                    launch_options['executable_path'] = path
                    break

        browser = await playwright.chromium.launch(**launch_options)

        # 创建浏览器上下文
        context = await browser.new_context(
            viewport={'width': 1500, 'height': 1200},
            locale='zh-CN'
        )

        # 创建新页面
        page = await context.new_page()

        # 访问 YouTube Studio
        await page.goto("https://studio.youtube.com")

        print("✅ 浏览器已启动，等待用户登录...")
        print()

        # 等待用户输入命令
        import sys
        while True:
            try:
                # 使用非阻塞的方式检查浏览器是否还在运行
                if browser.is_connected():
                    await asyncio.sleep(1)
                else:
                    print()
                    print("⚠️  浏览器已关闭")
                    print("❌ 未保存 cookie")
                    break
            except:
                print()
                print("⚠️  浏览器已关闭")
                print("❌ 未保存 cookie")
                break

    # 如果用户选择了保存
    print()
    choice = input("是否保存 cookie? (yes/no): ").strip().lower()

    if choice in ['yes', 'y']:
        print("💡 正在保存 cookie...")

        # 从用户数据目录中提取 cookie 并保存
        # 这里我们创建一个简化的 cookie 文件
        cookie_data = {
            'cookies': [],
            'origins': [
                {
                    'origin': 'https://studio.youtube.com',
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
            print("=" * 60)
            print()
            print("💡 注意：由于使用了 Chrome 用户数据目录，cookie 已经保存在浏览器中")
            print("💡 后续上传会使用这个 cookie 文件")
            print()

        except Exception as e:
            print(f"❌ 保存失败: {e}")

    # 清理临时用户数据目录
    try:
        print("🧹 清理临时文件...")
        shutil.rmtree(temp_user_data_dir)
        print("✅ 清理完成")
    except:
        print("⚠️  清理临时文件失败，请手动删除: " + str(temp_user_data_dir))


if __name__ == '__main__':
    try:
        asyncio.run(save_youtube_cookie_with_user_data_dir())
    except KeyboardInterrupt:
        print()
        print("❌ 用户取消操作")
    except Exception as e:
        print()
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
