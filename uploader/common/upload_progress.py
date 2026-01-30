# -*- coding: utf-8 -*-
"""
上传进度监控通用模块
提供统一的跨平台上传进度监控功能
"""

import asyncio
import re
from playwright.async_api import Page
from typing import Optional, List


def extract_percent(text: str) -> Optional[int]:
    """
    从文本中提取百分比数值

    Args:
        text: 包含百分号的文本，如 "1.13%", "50%"

    Returns:
        int: 百分比整数值，如 "1.13%" 返回 1，"50%" 返回 50
    """
    if not text or '%' not in text:
        return None

    # 优先匹配小数格式（如 1.13%），再匹配整数格式（如 13%）
    match = re.search(r'(\d+\.\d+)%', str(text))
    if match:
        return int(float(match.group(1)))  # 转换为浮点数再取整

    # 如果没有小数，尝试整数格式
    match = re.search(r'(\d+)%', str(text))
    if match:
        return int(match.group(1))

    return None


async def get_upload_progress(page: Page, custom_selectors: Optional[List[str]] = None) -> Optional[int]:
    """
    获取当前上传进度百分比

    Args:
        page: Playwright页面对象
        custom_selectors: 自定义进度选择器列表（可选）

    Returns:
        int: 进度百分比 (0-100)，如果无法获取则返回 None
    """
    try:
        # 方法1: 使用自定义选择器查找进度
        if custom_selectors:
            for selector in custom_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        text = await element.text_content()
                        if text and '%' in str(text):
                            percent = extract_percent(text)
                            if percent is not None:
                                return percent
                except:
                    continue

        # 方法2: 尝试查找包含百分号的文本元素
        progress_selectors = [
            'div[class*="progress"] span:has-text("%")',
            'div[class*="upload"] span:has-text("%")',
            'span[class*="progress"]:has-text("%")',
            '.upload-percent:has-text("%")',
            '.progress-text:has-text("%")',
            '[class*="percent"]:has-text("%")',
            # 直接搜索包含百分号的文本
            'text=/\\d+%/',
        ]

        for selector in progress_selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    text = await element.text_content()
                    if text and '%' in str(text):
                        # 提取百分比数字（支持小数格式如 1.13%）
                        percent = extract_percent(text)
                        if percent is not None:
                            return percent
            except:
                continue

        # 方法3: 尝试从进度条元素的宽度计算进度
        progress_bar_selectors = [
            'div[class*="progress"] div[class*="bar"]',
            'div[class*="upload"] div[class*="bar"]',
            '.progress-bar-inner',
            '[class*="progress-bar"]',
            '[role="progressbar"]',
        ]

        for selector in progress_bar_selectors:
            try:
                progress_bar = page.locator(selector).first
                if await progress_bar.count() > 0:
                    # 获取进度条的宽度或样式
                    style = await progress_bar.get_attribute('style')
                    if style and 'width' in style:
                        # 从style中提取宽度百分比（支持小数格式如 1.13%）
                        match = re.search(r'width\s*:\s*(\d+(?:\.\d+)?)%', style)
                        if match:
                            return int(float(match.group(1)))
            except:
                continue

        # 方法4: 尝试从页面上所有包含百分号的元素中查找
        all_elements = page.locator('*:has-text("%")')
        count = await all_elements.count()
        for i in range(min(count, 20)):  # 最多检查20个元素
            try:
                text = await all_elements.nth(i).text_content()
                if text and '%' in str(text):
                    # 查找类似 "50%", "1.13%", "上传中 50%", "进度：50%" 等格式
                    percent = extract_percent(text)
                    if percent is not None and 0 <= percent <= 100:
                        return percent
            except:
                continue

        return None

    except Exception as e:
        # 静默失败，避免干扰正常流程
        return None


async def wait_for_upload_with_progress(
    page: Page,
    logger,
    complete_indicators: List[str] = None,
    custom_progress_selectors: List[str] = None,
    check_interval: int = 2,
    max_wait_time: int = 600,
    progress_prefix: str = "📊 上传进度"
):
    """
    等待上传完成，并显示上传进度

    Args:
        page: Playwright页面对象
        logger: 日志记录器对象
        complete_indicators: 上传完成的标志选择器列表
        custom_progress_selectors: 自定义进度选择器列表（可选）
        check_interval: 检查间隔（秒）
        max_wait_time: 最大等待时间（秒）
        progress_prefix: 进度显示前缀
    """
    logger.info('   [-] 等待视频上传进度...')

    # 默认的上传完成标志
    if complete_indicators is None:
        complete_indicators = [
            'text="上传完成"',
            'text="上传完毕"',
            'div.upload-success:has-text("完成")',
            '.upload-finish:has-text("完成")',
            '[class*="success"]:has-text("上传")',
        ]

    wait_time = 0
    last_progress = 0  # 记录上次显示的进度，避免重复显示相同进度

    while wait_time < max_wait_time:
        try:
            # 检查是否有上传完成的标志
            for selector in complete_indicators:
                upload_complete = page.locator(selector)
                if await upload_complete.count() > 0:
                    logger.success('   [-] 视频上传完成')
                    await asyncio.sleep(check_interval)
                    return

            # 尝试获取上传进度百分比
            progress = await get_upload_progress(page, custom_progress_selectors)

            if progress is not None and progress != last_progress:
                # 显示进度百分比
                logger.info(f'   {progress_prefix}: {progress}%')
                last_progress = progress

            # 如果进度达到100%，说明上传完成
            if progress is not None and progress >= 100:
                logger.success('   [-] 视频上传完成')
                await asyncio.sleep(check_interval)
                return

            # 等待一段时间再检查
            await asyncio.sleep(check_interval)
            wait_time += check_interval

        except Exception as e:
            logger.warning(f'   [-] 等待上传时出错: {e}')
            await asyncio.sleep(check_interval)
            wait_time += check_interval

    logger.warning('   [-] 上传等待超时，继续后续步骤')
