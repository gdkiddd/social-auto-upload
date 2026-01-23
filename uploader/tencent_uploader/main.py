# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import tencent_logger
from myUtils.publish_history import get_publish_history
from myUtils.account_manager import get_current_account
from pathlib import Path


def format_str_for_short_title(origin_title: str) -> str:
    # 定义允许的特殊字符
    allowed_special_chars = "《》“”:+?%°"

    # 移除不允许的特殊字符
    filtered_chars = [char if char.isalnum() or char in allowed_special_chars else ' ' if char == ',' else '' for
                      char in origin_title]
    formatted_string = ''.join(filtered_chars)

    # 调整字符串长度
    if len(formatted_string) > 16:
        # 截断字符串
        formatted_string = formatted_string[:16]
    elif len(formatted_string) < 6:
        # 使用空格来填充字符串
        formatted_string += ' ' * (6 - len(formatted_string))

    return formatted_string


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=LOCAL_CHROME_HEADLESS
        )
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        try:
            await page.wait_for_selector('div.title-name:has-text("微信小店")', timeout=5000)  # 等待5秒
            tencent_logger.error("[+] 等待5秒 cookie 失效")
            return False
        except:
            tencent_logger.success("[+] cookie 有效")
            return True


async def get_tencent_cookie(account_file):
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(
            **options
        )
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        # Pause the page, and start recording manually.
        context = await set_init_script(context)
        page = await context.new_page()
        await page.goto("https://channels.weixin.qq.com")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


async def weixin_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, "tencent_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            # Todo alert message
            return False
        tencent_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await get_tencent_cookie(account_file)
    return True


class TencentVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, category=None, is_draft=False, thumbnail_path=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.category = category
        self.headless = LOCAL_CHROME_HEADLESS
        self.is_draft = is_draft  # 是否保存为草稿
        self.local_executable_path = LOCAL_CHROME_PATH or None
        self.thumbnail_path = thumbnail_path  # 封面图片路径

    async def set_schedule_time_tencent(self, page, publish_date):
        label_element = page.locator("label").filter(has_text="定时").nth(1)
        await label_element.click()

        await page.click('input[placeholder="请选择发表时间"]')

        str_month = str(publish_date.month) if publish_date.month > 9 else "0" + str(publish_date.month)
        current_month = str_month + "月"
        # 获取当前的月份
        page_month = await page.inner_text('span.weui-desktop-picker__panel__label:has-text("月")')

        # 检查当前月份是否与目标月份相同
        if page_month != current_month:
            await page.click('button.weui-desktop-btn__icon__right')

        # 获取页面元素
        elements = await page.query_selector_all('table.weui-desktop-picker__table a')

        # 遍历元素并点击匹配的元素
        for element in elements:
            if 'weui-desktop-picker__disabled' in await element.evaluate('el => el.className'):
                continue
            text = await element.inner_text()
            if text.strip() == str(publish_date.day):
                await element.click()
                break

        # 输入小时部分（假设选择11小时）
        await page.click('input[placeholder="请选择时间"]')
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date.hour))

        # 选择标题栏（令定时时间生效）
        await page.locator("div.input-editor").click()

    async def handle_upload_error(self, page):
        tencent_logger.info("视频出错了，重新上传中")
        await page.locator('div.media-status-content div.tag-inner:has-text("删除")').click()
        await page.get_by_role('button', name="删除", exact=True).click()
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(self.file_path)

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium (这里使用系统内浏览器，用chromium 会造成h264错误

        # 准备浏览器启动选项
        launch_options = {
            'headless': self.headless,
        }

        if self.local_executable_path:
            launch_options['executable_path'] = self.local_executable_path

        browser = await playwright.chromium.launch(
            **launch_options
        )
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(
            viewport={"width": 1500, "height": 1200},
            storage_state=f"{self.account_file}"
        )
        context = await set_init_script(context)

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://channels.weixin.qq.com/platform/post/create")
        tencent_logger.info(f'[+]正在上传-------{self.title}.mp4')
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        await page.wait_for_url("https://channels.weixin.qq.com/platform/post/create")
        # await page.wait_for_selector('input[type="file"]', timeout=10000)
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(self.file_path)
        # 填充标题和话题
        await self.add_title_tags(page)
        await asyncio.sleep(1)
        # 添加商品
        # await self.add_product(page)
        # 合集功能
        await self.add_collection(page)
        # 原创选择
        await self.add_original(page)
        await asyncio.sleep(1)
        # 检测上传状态
        await self.detect_upload_status(page)
        await asyncio.sleep(1)
        # 上传封面
        await self.upload_thumbnail(page)
        await asyncio.sleep(1)
        if self.publish_date != 0:
            await self.set_schedule_time_tencent(page, self.publish_date)
            await asyncio.sleep(1)
        # 添加短标题
        await self.add_short_title(page)
        await asyncio.sleep(1)

        await self.click_publish(page)

        await context.storage_state(path=f"{self.account_file}")  # 保存cookie
        tencent_logger.success('  [-]cookie更新完毕！')
        tencent_logger.success('  [-]视频已成功发布，浏览器即将关闭')

        # 关闭浏览器
        await context.close()
        await browser.close()
        tencent_logger.info('  [-] 浏览器已关闭')

    async def add_short_title(self, page):
        short_title_element = page.get_by_text("短标题", exact=True).locator("..").locator(
            "xpath=following-sibling::div").locator(
            'span input[type="text"]')
        if await short_title_element.count():
            short_title = format_str_for_short_title(self.title)
            await short_title_element.fill(short_title)
            await asyncio.sleep(1)

    async def click_publish(self, page):
        while True:
            try:
                if self.is_draft:
                    # 点击"保存草稿"按钮
                    draft_button = page.locator('div.form-btns button:has-text("保存草稿")')
                    if await draft_button.count():
                        await draft_button.click()
                    # 等待跳转到草稿箱页面或确认保存成功
                    await page.wait_for_url("**/post/list**", timeout=5000)  # 使用通配符匹配包含post/list的URL
                    tencent_logger.success("  [-]视频草稿保存成功")
                    # 记录发布历史
                    publish_history = get_publish_history()
                    publish_history.add_record(
                        platform_id='tencent',
                        platform_name='视频号',
                        video_file=Path(self.file_path).name,
                        status='success',
                        account=get_current_account()
                    )
                else:
                    # 点击"发表"按钮
                    publish_button = page.locator('div.form-btns button:has-text("发表")')
                    if await publish_button.count():
                        await publish_button.click()
                    await page.wait_for_url("https://channels.weixin.qq.com/platform/post/list", timeout=5000)
                    tencent_logger.success("  [-]视频发布成功")
                    # 记录发布历史
                    publish_history = get_publish_history()
                    publish_history.add_record(
                        platform_id='tencent',
                        platform_name='视频号',
                        video_file=Path(self.file_path).name,
                        status='success',
                        account=get_current_account()
                    )
                break
            except Exception as e:
                current_url = page.url
                if self.is_draft:
                    # 检查是否在草稿相关的页面
                    if "post/list" in current_url or "draft" in current_url:
                        tencent_logger.success("  [-]视频草稿保存成功")
                        # 记录发布历史
                        publish_history = get_publish_history()
                        publish_history.add_record(
                            platform_id='tencent',
                            platform_name='视频号',
                            video_file=Path(self.file_path).name,
                            status='success',
                            account=get_current_account()
                        )
                        break
                else:
                    # 检查是否在发布列表页面
                    if "https://channels.weixin.qq.com/platform/post/list" in current_url:
                        tencent_logger.success("  [-]视频发布成功")
                        # 记录发布历史
                        publish_history = get_publish_history()
                        publish_history.add_record(
                            platform_id='tencent',
                            platform_name='视频号',
                            video_file=Path(self.file_path).name,
                            status='success',
                            account=get_current_account()
                        )
                        break
                tencent_logger.exception(f"  [-] Exception: {e}")
                tencent_logger.info("  [-] 视频正在发布中...")
                await asyncio.sleep(0.5)

    async def detect_upload_status(self, page):
        while True:
            # 匹配删除按钮，代表视频上传完毕，如果不存在，代表视频正在上传，则等待
            try:
                # 匹配删除按钮，代表视频上传完毕
                if "weui-desktop-btn_disabled" not in await page.get_by_role("button", name="发表").get_attribute(
                        'class'):
                    tencent_logger.info("  [-]视频上传完毕")
                    break
                else:
                    tencent_logger.info("  [-] 正在上传视频中...")
                    await asyncio.sleep(2)
                    # 出错了视频出错
                    if await page.locator('div.status-msg.error').count() and await page.locator(
                            'div.media-status-content div.tag-inner:has-text("删除")').count():
                        tencent_logger.error("  [-] 发现上传出错了...准备重试")
                        await self.handle_upload_error(page)
            except:
                tencent_logger.info("  [-] 正在上传视频中...")
                await asyncio.sleep(2)

    async def add_title_tags(self, page):
        await page.locator("div.input-editor").click()
        await asyncio.sleep(1)
        await page.keyboard.type(self.title)
        await asyncio.sleep(1)
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)
        for index, tag in enumerate(self.tags, start=1):
            await page.keyboard.type("#" + tag)
            await page.keyboard.press("Space")
            await asyncio.sleep(0.3)
        tencent_logger.info(f"成功添加hashtag: {len(self.tags)}")

    async def add_collection(self, page):
        collection_elements = page.get_by_text("添加到合集").locator("xpath=following-sibling::div").locator(
            '.option-list-wrap > div')
        if await collection_elements.count() > 1:
            await page.get_by_text("添加到合集").locator("xpath=following-sibling::div").click()
            await asyncio.sleep(1)
            await collection_elements.first.click()
            await asyncio.sleep(1)

    async def upload_thumbnail(self, page):
        """上传封面图片"""
        if not self.thumbnail_path:
            tencent_logger.info("  [-] 未指定封面图片，跳过封面上传")
            return

        try:
            tencent_logger.info(f"  [-] 正在上传封面: {self.thumbnail_path.name}")

            # 等待封面预览加载完成
            tencent_logger.info("  [-] 等待封面预览加载...")
            await asyncio.sleep(2)

            # 步骤1: 点击"编辑"按钮
            tencent_logger.info("  [-] 步骤1: 查找并点击封面编辑按钮...")

            # 尝试多个选择器来定位编辑按钮
            edit_button = page.locator('div.edit-btn.edit-btn-zIndex')

            # 等待编辑按钮出现（最多等待10秒）
            try:
                await edit_button.first.wait_for(state='visible', timeout=10000)
                tencent_logger.info("  [-] 找到编辑按钮，正在点击...")

                # 使用 force=True 强制点击，因为按钮可能被图片遮挡
                try:
                    await edit_button.first.click(force=True)
                    tencent_logger.success("  [-] 已点击编辑按钮（force=True）")
                except:
                    # 如果 force=True 也失败，使用 JavaScript 直接点击
                    tencent_logger.warning("  [-] 强制点击失败，使用 JavaScript 点击...")
                    await edit_button.first.evaluate('el => el.click()')
                    tencent_logger.success("  [-] 已点击编辑按钮（JavaScript）")

                await asyncio.sleep(1)
            except:
                # 备用方案：尝试其他选择器
                tencent_logger.warning("  [-] 未找到编辑按钮（选择器1），尝试其他方式...")
                edit_button_alt = page.locator('div[class*="edit-btn"]')

                if await edit_button_alt.count() > 0:
                    tencent_logger.info("  [-] 使用备用选择器找到编辑按钮")
                    try:
                        await edit_button_alt.first.click(force=True)
                    except:
                        await edit_button_alt.first.evaluate('el => el.click()')
                    tencent_logger.success("  [-] 已点击编辑按钮")
                    await asyncio.sleep(1)
                else:
                    # 最后备用方案：点击封面区域
                    tencent_logger.warning("  [-] 仍未找到编辑按钮，尝试点击封面区域...")
                    cover_edit_area = page.locator('div.vertical-img-wrap')
                    if await cover_edit_area.count() > 0:
                        await cover_edit_area.click()
                        tencent_logger.success("  [-] 已点击封面区域")
                        await asyncio.sleep(1)
                    else:
                        tencent_logger.error("  ❌ 未找到封面编辑区域，跳过封面上传")
                        return

            # 步骤2: 点击"上传封面"按钮，并等待文件选择器
            tencent_logger.info("  [-] 步骤2: 点击'上传封面'按钮...")
            upload_thumbnail_button = page.locator('div.wrap:has-text("上传封面")')

            # 等待上传封面按钮出现
            try:
                await upload_thumbnail_button.first.wait_for(state='visible', timeout=5000)
            except:
                tencent_logger.warning("  [-] 等待'上传封面'按钮超时，继续尝试...")

            # 使用 Playwright 的 file chooser API
            async with page.expect_file_chooser(timeout=10000) as fc_info:
                await upload_thumbnail_button.click()

            file_chooser = await fc_info.value
            await file_chooser.set_files(str(self.thumbnail_path))
            tencent_logger.success(f"  [-] 图片文件已选择: {self.thumbnail_path.name}")

            # 等待图片预览加载
            await asyncio.sleep(2)

            # 步骤3: 点击确认按钮
            tencent_logger.info("  [-] 步骤3: 等待确认按钮出现...")

            # 等待确认按钮出现（最多等待10秒）
            try:
                await page.wait_for_selector('button.weui-desktop-btn.weui-desktop-btn_primary.weui-desktop-btn_mini:has-text("确认")', timeout=10000)
                tencent_logger.info("  [-] 确认按钮已出现")
            except:
                tencent_logger.warning("  ⚠️  等待确认按钮超时，尝试直接点击")

            # 使用多种选择器尝试点击确认按钮
            confirm_button = page.locator('button.weui-desktop-btn.weui-desktop-btn_primary.weui-desktop-btn_mini:has-text("确认")')

            # 如果找不到，尝试更通用的选择器
            if await confirm_button.count() == 0:
                tencent_logger.info("  [-] 尝试备用选择器...")
                confirm_button = page.locator('button.weui-desktop-btn_primary:has-text("确认")')

            # 如果还是找不到，尝试最通用的选择器
            if await confirm_button.count() == 0:
                tencent_logger.info("  [-] 尝试最通用选择器...")
                confirm_button = page.locator('button:has-text("确认")')

            # 点击确认按钮
            button_count = await confirm_button.count()
            if button_count > 0:
                tencent_logger.info(f"  [-] 找到 {button_count} 个确认按钮，正在点击第一个...")
                await confirm_button.first.click()
                tencent_logger.success(f"  [-] 封面上传成功: {self.thumbnail_path.name}")

                # 等待封面预览加载和页面返回
                await asyncio.sleep(2)
            else:
                tencent_logger.error("  ❌ 未找到确认按钮")
                # 截图以便调试
                await page.screenshot(path="debug_confirm_button.png")
                tencent_logger.info("  [-] 已保存截图到 debug_confirm_button.png")

        except Exception as e:
            tencent_logger.error(f"  ❌ 封面上传失败: {str(e)}")
            # 封面上传失败不影响视频发布，继续执行

    async def add_original(self, page):
        if await page.get_by_label("视频为原创").count():
            await page.get_by_label("视频为原创").check()
        # 检查 "我已阅读并同意 《视频号原创声明使用条款》" 元素是否存在
        label_locator = await page.locator('label:has-text("我已阅读并同意 《视频号原创声明使用条款》")').is_visible()
        if label_locator:
            await page.get_by_label("我已阅读并同意 《视频号原创声明使用条款》").check()
            await page.get_by_role("button", name="声明原创").click()
        # 2023年11月20日 wechat更新: 可能新账号或者改版账号，出现新的选择页面
        if await page.locator('div.label span:has-text("声明原创")').count() and self.category:
            # 因处罚无法勾选原创，故先判断是否可用
            if not await page.locator('div.declare-original-checkbox input.ant-checkbox-input').is_disabled():
                await page.locator('div.declare-original-checkbox input.ant-checkbox-input').click()
                if not await page.locator(
                        'div.declare-original-dialog label.ant-checkbox-wrapper.ant-checkbox-wrapper-checked:visible').count():
                    await page.locator('div.declare-original-dialog input.ant-checkbox-input:visible').click()
            if await page.locator('div.original-type-form > div.form-label:has-text("原创类型"):visible').count():
                await page.locator('div.form-content:visible').click()  # 下拉菜单
                await page.locator(
                    f'div.form-content:visible ul.weui-desktop-dropdown__list li.weui-desktop-dropdown__list-ele:has-text("{self.category}")').first.click()
                await page.wait_for_timeout(1000)
            if await page.locator('button:has-text("声明原创"):visible').count():
                await page.locator('button:has-text("声明原创"):visible').click()

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)
