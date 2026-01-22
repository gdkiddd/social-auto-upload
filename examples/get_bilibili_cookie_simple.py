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
            bilibili_logger.info('[+] 登录成功后，按 Ctrl+C 或关闭窗口继续...')

            # 等待用户手动登录 - 等待跳转到个人主页或等待特定时间
            try:
                # 等待 URL 变化（登录成功后会跳转）
                await page.wait_for_url(
                    ['https://www.bilibili.com/*', 'https://space.bilibili.com/*'],
                    timeout=120000  # 等待 2 分钟
                )
                bilibili_logger.success('[+] 检测到登录成功！')
            except:
                # 如果没有跳转，给用户 30 秒时间手动登录
                bilibili_logger.info('[+] 请在 30 秒内完成扫码登录...')
                await asyncio.sleep(30)

            # 保存 cookie
            await context.storage_state(path=account_file)
            bilibili_logger.success(f'[+] Cookie 已保存到: {account_file}')

            await browser.close()
            return True

        except Exception as e:
            bilibili_logger.error(f'[-] 登录过程出错: {str(e)}')
            await browser.close()
            return False


if __name__ == '__main__':
    account_file = Path(__file__).parent.parent / "cookies" / "bilibili_uploader" / "account.json"

    print('Bilibili 简易登录 - macOS 版本')
    print(f'Cookie 保存路径: {account_file}')
    print('=' * 60)
    print('说明：')
    print('1. 浏览器会自动打开 Bilibili 登录页面')
    print('2. 使用手机 Bilibili APP 扫码登录')
    print('3. 登录成功后，Cookie 会自动保存')
    print('=' * 60)

    success = asyncio.run(bilibili_simple_login(account_file))

    if success:
        print('\n✅ 登录成功！现在可以上传视频了')
        print(f'运行上传命令: python examples/upload_video_to_bilibili.py')
    else:
        print('\n❌ 登录失败，请重试')
        sys.exit(1)
