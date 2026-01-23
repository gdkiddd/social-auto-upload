#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilibili 简易登录 - 使用 Playwright 自动化登录
"""

import asyncio
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright
from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger


async def bilibili_simple_login(account_file):
    """
    使用 Playwright 自动化登录 Bilibili
    """
    bilibili_logger.info('[+] 正在启动浏览器...')

    async with async_playwright() as p:
        # 启动浏览器
        options = {
            'headless': False  # 必须显示浏览器窗口，方便扫码登录
        }

        if LOCAL_CHROME_PATH:
            options['executable_path'] = LOCAL_CHROME_PATH

        browser = await p.chromium.launch(**options)
        context = await browser.new_context()
        context = await set_init_script(context)
        page = await context.new_page()

        try:
            # 访问 Bilibili 登录页面
            await page.goto('https://passport.bilibili.com/login')

            bilibili_logger.info('[+] 浏览器已打开，请扫码登录')
            bilibili_logger.info('[+] 登录成功后，点击 Inspector 窗口的"继续"按钮')

            # 暂停并打开 Playwright Inspector，用户登录后点击"继续"
            await page.pause()

            # 保存 cookie（先创建目录）
            account_file.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=account_file)
            bilibili_logger.success(f'[+] Cookie 已保存到: {account_file}')

            await browser.close()
            return True

        except Exception as e:
            bilibili_logger.error(f'[-] 登录过程出错: {str(e)}')
            await browser.close()
            return False


if __name__ == '__main__':
    from myUtils.account_manager import get_current_account, get_account_cookie_path

    # 获取当前账号的 cookie 路径
    current_account = get_current_account()
    account_file = get_account_cookie_path(current_account, 'bilibili')

    print('Bilibili 登录')
    print(f'当前账号: {current_account}')
    print(f'Cookie 保存路径: {account_file}')
    print('=' * 60)
    print('操作步骤：')
    print('1. 浏览器会自动打开 Bilibili 登录页面')
    print('2. 同时会弹出 Playwright Inspector 窗口')
    print('3. 使用手机 Bilibili APP 扫码登录')
    print('4. 登录成功后，点击 Inspector 窗口的"继续"按钮（▶）')
    print('5. Cookie 会自动保存')
    print('=' * 60)

    success = asyncio.run(bilibili_simple_login(account_file))

    if success:
        print('\n✅ 登录成功！现在可以上传视频了')
        print(f'运行上传命令: python examples/upload_video_to_bilibili.py')
    else:
        print('\n❌ 登录失败，请重试')
        sys.exit(1)
