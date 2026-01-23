# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import kuaishou_logger
from myUtils.publish_history import get_publish_history
from myUtils.account_manager import get_current_account
from pathlib import Path
import glob


async def cookie_auth(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        try:
            await page.wait_for_selector("div.names div.container div.name:text('机构服务')", timeout=5000)  # 等待5秒

            kuaishou_logger.info("[+] 等待5秒 cookie 失效")
            return False
        except:
            kuaishou_logger.success("[+] cookie 有效")
            return True


async def ks_setup(account_file, handle=False):
    account_file = get_absolute_path(account_file, "ks_uploader")
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            return False
        kuaishou_logger.info('[+] cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件')
        await get_ks_cookie(account_file)
    return True


async def get_ks_cookie(account_file):
    async with async_playwright() as playwright:
        options = {
            'args': [
                '--lang en-GB'
            ],
            'headless': LOCAL_CHROME_HEADLESS,  # Set headless option here
        }
        # Make sure to run headed.
        browser = await playwright.chromium.launch(**options)
        # Setup context however you like.
        context = await browser.new_context()  # Pass any options
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://cp.kuaishou.com")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)


class KSVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y-%m-%d %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS

    async def handle_upload_error(self, page):
        kuaishou_logger.error("视频出错了，重新上传中")
        await page.locator('div.progress-div [class^="upload-btn-input"]').set_input_files(self.file_path)

    async def set_cover(self, page):
        """设置视频封面"""
        kuaishou_logger.info("  [-] 开始设置封面...")

        try:
            # 1. 点击"封面设置"
            cover_setting_button = page.locator('div._default-cover_ps02t_86 div:has-text("封面设置")')
            if await cover_setting_button.count() == 0:
                kuaishou_logger.info("  [-] 未找到封面设置按钮，跳过封面设置")
                return

            await cover_setting_button.click()
            await asyncio.sleep(1)

            # 2. 点击"上传封面"
            upload_cover_button = page.locator('div._header-title-item_2t3fe_27:has-text("上传封面")')
            if await upload_cover_button.count() == 0:
                kuaishou_logger.info("  [-] 未找到上传封面按钮")
                return

            await upload_cover_button.click()
            await asyncio.sleep(1)

            # 3. 点击"上传图片"按钮并选择文件
            upload_img_button = page.locator('button._upload-btn_1i0wh_73:has-text("上传图片")')
            if await upload_img_button.count() == 0:
                kuaishou_logger.info("  [-] 未找到上传图片按钮")
                return

            # 查找封面图片
            video_file = Path(self.file_path)
            videos_dir = video_file.parent

            # 尝试多种封面图片格式
            cover_extensions = ['.png', '.PNG', '.jpg', '.jpeg', '.JPG', '.JPEG']
            cover_file = None

            for ext in cover_extensions:
                potential_cover = video_file.with_suffix(ext)
                if potential_cover.exists():
                    cover_file = potential_cover
                    break

            if not cover_file:
                # 如果找不到同名的封面图，尝试查找 videos 目录下的第一个图片
                videos_dir = Path("videos")
                if videos_dir.exists():
                    # 查找所有图片文件
                    image_patterns = ['*.png', '*.PNG', '*.jpg', '*.jpeg', '*.JPG', '*.JPEG']
                    for pattern in image_patterns:
                        images = list(videos_dir.glob(pattern))
                        if images:
                            cover_file = images[0]
                            break

            if cover_file:
                kuaishou_logger.info(f"  [-] 找到封面图片: {cover_file.name}")

                # 使用 file chooser API 上传文件
                async with page.expect_file_chooser() as fc_info:
                    await upload_img_button.click()

                file_chooser = await fc_info.value
                await file_chooser.set_files(str(cover_file))

                kuaishou_logger.success(f"  [-] 封面图片已选择: {cover_file.name}")
                await asyncio.sleep(2)
            else:
                kuaishou_logger.info("  [-] 未找到封面图片，跳过封面设置")
                # 点击返回取消封面设置
                return

            # 4. 点击"确认"按钮
            confirm_button = page.locator('button:has-text("确认")')
            if await confirm_button.count() > 0:
                await confirm_button.click()
                kuaishou_logger.success("  [-] 封面设置成功")
                await asyncio.sleep(1)
            else:
                kuaishou_logger.warning("  [-] 未找到确认按钮")

            # 5. 在互动设置中，取消勾选"允许下载此作品"
            await self.disable_download_option(page)

        except Exception as e:
            kuaishou_logger.error(f"  ❌ 封面设置失败: {str(e)}")
            # 封面设置失败不影响视频发布，继续执行

    async def disable_download_option(self, page):
        """在互动设置中取消勾选'允许下载此作品'"""
        try:
            kuaishou_logger.info("  [-] 设置互动选项...")

            # 直接查找包含"允许下载此作品"文字的 checkbox wrapper
            checkbox_wrapper = page.locator('label.ant-checkbox-wrapper:has-text("允许下载此作品")')

            if await checkbox_wrapper.count() == 0:
                kuaishou_logger.info("  [-] 未找到'允许下载此作品'选项，可能已默认关闭")
                return

            # 检查是否已勾选
            class_list = await checkbox_wrapper.get_attribute('class') or ''
            is_checked = 'ant-checkbox-wrapper-checked' in class_list

            kuaishou_logger.info(f"  [-] Checkbox class: {class_list}")
            kuaishou_logger.info(f"  [-] 是否已勾选: {is_checked}")

            if is_checked:
                # 点击整个 wrapper 来切换状态
                await checkbox_wrapper.click()
                kuaishou_logger.success("  [-] 已取消勾选'允许下载此作品'")
            else:
                kuaishou_logger.info("  [-] '允许下载此作品' 未勾选")

            await asyncio.sleep(1)

        except Exception as e:
            kuaishou_logger.warning(f"  ⚠️  设置互动选项时出错: {str(e)}")
            import traceback
            kuaishou_logger.warning(traceback.format_exc())
            # 互动设置失败不影响视频发布

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        print(self.local_executable_path)

        # 准备浏览器启动选项
        launch_options = {
            'headless': self.headless,
        }

        if self.local_executable_path:
            launch_options['executable_path'] = self.local_executable_path

        browser = await playwright.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": 1250, "height": 1250},
            storage_state=f"{self.account_file}"
        )
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://cp.kuaishou.com/article/publish/video")
        kuaishou_logger.info('正在上传-------{}.mp4'.format(self.title))
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        kuaishou_logger.info('正在打开主页...')
        await page.wait_for_url("https://cp.kuaishou.com/article/publish/video")
        # 点击 "上传视频" 按钮
        upload_button = page.locator("button[class^='_upload-btn']")
        await upload_button.wait_for(state='visible')  # 确保按钮可见

        async with page.expect_file_chooser() as fc_info:
            await upload_button.click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(self.file_path)

        await asyncio.sleep(2)

        # if not await page.get_by_text("封面编辑").count():
        #     raise Exception("似乎没有跳转到到编辑页面")

        await asyncio.sleep(1)

        # 等待按钮可交互
        new_feature_button = page.locator('button[type="button"] span:text("我知道了")')
        if await new_feature_button.count() > 0:
            await new_feature_button.click()

        kuaishou_logger.info("正在填充标题和话题...")
        await page.get_by_text("描述").locator("xpath=following-sibling::div").click()
        kuaishou_logger.info("clear existing title")
        await page.keyboard.press("Backspace")
        await page.keyboard.press("Control+KeyA")
        await page.keyboard.press("Delete")
        kuaishou_logger.info("filling new  title")
        await page.keyboard.type(self.title)
        await page.keyboard.press("Enter")

        # 快手只能添加3个话题
        for index, tag in enumerate(self.tags[:3], start=1):
            kuaishou_logger.info("正在添加第%s个话题" % index)
            await page.keyboard.type(f"#{tag} ")
            await asyncio.sleep(2)

        max_retries = 60  # 设置最大重试次数,最大等待时间为 2 分钟
        retry_count = 0

        while retry_count < max_retries:
            try:
                # 获取包含 '上传中' 文本的元素数量
                number = await page.locator("text=上传中").count()

                if number == 0:
                    kuaishou_logger.success("视频上传完毕")
                    break
                else:
                    if retry_count % 5 == 0:
                        kuaishou_logger.info("正在上传视频中...")
                    await asyncio.sleep(2)
            except Exception as e:
                kuaishou_logger.error(f"检查上传状态时发生错误: {e}")
                await asyncio.sleep(2)  # 等待 2 秒后重试
            retry_count += 1

        if retry_count == max_retries:
            kuaishou_logger.warning("超过最大重试次数，视频上传可能未完成。")

        # 上传封面
        await self.set_cover(page)
        await asyncio.sleep(1)

        # 定时任务
        if self.publish_date != 0:
            await self.set_schedule_time(page, self.publish_date)

        # 判断视频是否发布成功
        while True:
            try:
                publish_button = page.get_by_text("发布", exact=True)
                if await publish_button.count() > 0:
                    await publish_button.click()

                await asyncio.sleep(1)
                confirm_button = page.get_by_text("确认发布")
                if await confirm_button.count() > 0:
                    await confirm_button.click()

                # 等待页面跳转，确认发布成功
                await page.wait_for_url(
                    "https://cp.kuaishou.com/article/manage/video?status=2&from=publish",
                    timeout=5000,
                )
                kuaishou_logger.success("视频发布成功")
                # 记录发布历史
                publish_history = get_publish_history()
                publish_history.add_record(
                    platform_id='kuaishou',
                    platform_name='快手',
                    video_file=Path(self.file_path).name,
                    status='success',
                    account=get_current_account()
                )
                break
            except Exception as e:
                kuaishou_logger.info(f"视频正在发布中... 错误: {e}")
                await page.screenshot(full_page=True)
                await asyncio.sleep(1)

        await context.storage_state(path=self.account_file)  # 保存cookie
        kuaishou_logger.info('cookie更新完毕！')
        kuaishou_logger.success('  [-]视频已成功发布，浏览器窗口将保持打开状态，请手动关闭')
        await asyncio.sleep(3600)  # 保持浏览器打开 1 小时，方便手动操作

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)

    async def set_schedule_time(self, page, publish_date):
        kuaishou_logger.info("click schedule")
        publish_date_hour = publish_date.strftime("%Y-%m-%d %H:%M:%S")
        await page.locator("label:text('发布时间')").locator('xpath=following-sibling::div').locator(
            '.ant-radio-input').nth(1).click()
        await asyncio.sleep(1)

        await page.locator('div.ant-picker-input input[placeholder="选择日期时间"]').click()
        await asyncio.sleep(1)

        await page.keyboard.press("Control+KeyA")
        await page.keyboard.type(str(publish_date_hour))
        await page.keyboard.press("Enter")
        await asyncio.sleep(1)
