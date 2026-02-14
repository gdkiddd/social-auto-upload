# -*- coding: utf-8 -*-
"""
浏览器初始化和管理工具
"""

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script


async def init_browser_context(playwright, account_file: str,
                                local_executable_path: str = None,
                                user_data_dir: str = None,
                                headless: bool = None):
    """
    初始化浏览器上下文

    Args:
        playwright: Playwright 实例
        account_file: Cookie 文件路径
        local_executable_path: 本地 Chrome 路径（可选）
        user_data_dir: 用户数据目录（可选，用于持久化浏览器数据）
        headless: 是否无头模式（可选，默认使用配置文件中的值）

    Returns:
        (browser, context, page) 元组
    """
    # 准备浏览器启动选项
    launch_options = {
        'headless': headless if headless is not None else LOCAL_CHROME_HEADLESS,
    }

    # 设置可执行路径（如果提供了本地路径）
    executable_path = local_executable_path or LOCAL_CHROME_PATH
    if executable_path:
        launch_options['executable_path'] = executable_path

    # 设置用户数据目录（如果提供）
    if user_data_dir:
        launch_options['args'] = [f'--user-data-dir={user_data_dir}']

    browser = await playwright.chromium.launch(**launch_options)

    # 创建上下文
    context_options = {
        'viewport': {'width': 1024, 'height': 768},
        'storage_state': account_file,
    }

    # 如果提供了用户数据目录，添加到上下文选项
    if user_data_dir:
        context_options['user_data_dir'] = user_data_dir

    context = await browser.new_context(**context_options)
    context = await set_init_script(context)

    page = await context.new_page()

    return browser, context, page
