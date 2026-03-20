# -*- coding: utf-8 -*-
from datetime import datetime

from playwright.async_api import Playwright, async_playwright
import os
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS
from utils.base_social_media import set_init_script
from utils.files_times import get_absolute_path
from utils.log import kuaishou_logger
from myUtils.account_manager import get_current_account
from uploader.common import find_cover_image, record_publish_history, get_upload_progress
from pathlib import Path
import glob
# 引入通用工具模块


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
            'proxy': None,  # 禁用代理，避免 ERR_PROXY_CONNECTION_FAILED 错误
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

    async def dismiss_onboarding_dialog(self, page):
        """处理首次登录新手导览弹窗，检测到则自动跳过。"""
        selectors = [
            'div._close_d7f44_29[title="Skip"]',
            'div._close_d7f44_29[aria-label="Skip"][data-action="skip"]',
            'div[role="button"][title="Skip"][data-action="skip"]',
        ]
        for selector in selectors:
            try:
                skip_btn = page.locator(selector).first
                if await skip_btn.count() > 0 and await skip_btn.is_visible():
                    await skip_btn.click()
                    kuaishou_logger.info("  [-] 检测到新手导览，已自动点击跳过")
                    await asyncio.sleep(0.5)
                    return True
            except Exception:
                continue
        return False

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

            # 使用通用工具查找封面图片
            cover_file = find_cover_image(self.file_path)

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

    async def _is_publish_button_ready(self, page):
        """发布按钮可点击时，视为上传已基本完成。"""
        publish_button = page.get_by_text("发布", exact=True).first
        if await publish_button.count() == 0:
            return False

        disabled = await publish_button.get_attribute("disabled")
        aria_disabled = await publish_button.get_attribute("aria-disabled")
        classes = (await publish_button.get_attribute("class")) or ""
        return not disabled and aria_disabled != "true" and "disabled" not in classes.lower()

    async def wait_upload_complete(self, page):
        """
        快手上传完成判定：
        1) 上传中提示消失
        2) 上传进度到 100%
        3) 发布按钮可点击
        4) 额外等待确保上传完全完成
        """
        kuaishou_logger.info("  [-] 等待快手上传完成...")
        wait_time = 0
        max_wait_time = 600  # 增加到10分钟
        check_interval = 2
        last_progress = -1
        stuck_100_count = 0

        while wait_time < max_wait_time:
            try:
                if await page.locator("text=上传失败").count() > 0:
                    kuaishou_logger.error("  [-] 检测到上传失败")
                    return False

                # 获取上传进度
                progress = await get_upload_progress(page)
                if progress is not None and progress != last_progress:
                    kuaishou_logger.info(f"  📊 上传进度: {progress}%")
                    last_progress = progress

                # 检查上传中提示
                uploading_count = await page.locator("text=上传中").count()

                # 检查上传完成标志
                upload_complete_count = await page.locator("text=上传完成").count()
                uploading_finished_count = await page.locator("text=上传完毕").count()

                # 如果进度达到100%且上传中提示消失，说明上传完成
                if progress is not None and progress >= 100:
                    stuck_100_count += 1
                    if stuck_100_count >= 3:  # 连续3次检测到100%，约6秒
                        kuaishou_logger.success("  [-] 上传进度达到100%")
                        # 额外等待5秒确保上传完全完成
                        kuaishou_logger.info("  [-] 额外等待5秒确保上传完全完成...")
                        await asyncio.sleep(5)
                        return True
                elif progress is not None and progress >= 99:
                    # 99%时也要等待，但计数器可以少一点
                    stuck_100_count += 0.5
                    if stuck_100_count >= 5:  # 约10秒
                        kuaishou_logger.warning("  [-] 进度长期停留 99-100%，继续后续流程")
                        await asyncio.sleep(3)
                        return True
                else:
                    stuck_100_count = 0

                # 如果上传中提示消失且有上传完成标志
                if uploading_count == 0 and (upload_complete_count > 0 or uploading_finished_count > 0):
                    kuaishou_logger.success("  [-] 上传中提示已消失，检测到完成标志")
                    await asyncio.sleep(2)
                    return True

                # 如果上传中提示消失且发布按钮可点击
                if uploading_count == 0 and await self._is_publish_button_ready(page):
                    kuaishou_logger.success("  [-] 上传中提示已消失，发布按钮可点击")
                    await asyncio.sleep(2)
                    return True

                await asyncio.sleep(check_interval)
                wait_time += check_interval
            except Exception as e:
                kuaishou_logger.warning(f"  [-] 上传状态检测异常: {e}")
                await asyncio.sleep(check_interval)
                wait_time += check_interval

        kuaishou_logger.warning("  [-] 上传等待超时，检查发布按钮状态")
        # 超时时再检查一次发布按钮是否可用
        if await self._is_publish_button_ready(page):
            kuaishou_logger.info("  [-] 发布按钮可点击，继续后续流程")
            return True
        return False

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例
        print(self.local_executable_path)

        # 准备浏览器启动选项
        launch_options = {
            'headless': self.headless,
            'proxy': None,  # 禁用代理，避免 ERR_PROXY_CONNECTION_FAILED 错误
        }

        if self.local_executable_path:
            launch_options['executable_path'] = self.local_executable_path

        browser = await playwright.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": 1024, "height": 768},
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
        await self.dismiss_onboarding_dialog(page)
        new_feature_button = page.locator('button[type="button"] span:text("我知道了")')
        if await new_feature_button.count() > 0:
            await new_feature_button.click()

        # 再次兜底，避免填充前弹窗盖住输入区域
        await self.dismiss_onboarding_dialog(page)
        kuaishou_logger.info("正在填充标题和话题...")
        try:
            await page.get_by_text("描述").locator("xpath=following-sibling::div").click()
        except Exception:
            await self.dismiss_onboarding_dialog(page)
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
            await asyncio.sleep(0.3)

        await self.wait_upload_complete(page)

        # 上传封面
        await self.set_cover(page)
        await asyncio.sleep(1)

        # 定时任务
        if self.publish_date != 0:
            await self.set_schedule_time(page, self.publish_date)

        # 判断视频是否发布成功
        kuaishou_logger.info("  [-] 开始发布视频...")
        max_attempts = 30  # 最多尝试30次
        attempt = 0

        while attempt < max_attempts:
            try:
                # 检查是否已经在发布后的页面
                current_url = page.url
                if "article/manage/video" in current_url and "status=2" in current_url:
                    kuaishou_logger.success("  [-] 视频发布成功")
                    record_publish_history(
                        platform_id='kuaishou',
                        platform_name='快手',
                        video_file_path=self.file_path,
                        status='success'
                    )
                    break

                # 尝试点击发布按钮
                publish_button = page.get_by_text("发布", exact=True)
                if await publish_button.count() > 0:
                    # 检查发布按钮是否可点击
                    disabled = await publish_button.get_attribute("disabled")
                    aria_disabled = await publish_button.get_attribute("aria-disabled")
                    classes = (await publish_button.get_attribute("class")) or ""

                    if not disabled and aria_disabled != "true" and "disabled" not in classes.lower():
                        await publish_button.click()
                        kuaishou_logger.info("  [-] 已点击发布按钮")

                await asyncio.sleep(1)

                # 检查是否有确认发布按钮
                confirm_button = page.get_by_text("确认发布")
                if await confirm_button.count() > 0:
                    await confirm_button.click()
                    kuaishou_logger.info("  [-] 已点击确认发布按钮")

                # 等待页面跳转，确认发布成功
                try:
                    await page.wait_for_url(
                        "https://cp.kuaishou.com/article/manage/video?status=2&from=publish",
                        timeout=5000,
                    )
                    kuaishou_logger.success("  [-] 视频发布成功")
                    record_publish_history(
                        platform_id='kuaishou',
                        platform_name='快手',
                        video_file_path=self.file_path,
                        status='success'
                    )
                    break
                except:
                    # 等待跳转超时，继续循环
                    pass

                attempt += 1
                kuaishou_logger.info(f"  [-] 发布中... ({attempt}/{max_attempts})")

            except Exception as e:
                kuaishou_logger.info(f"  [-] 发布进度检查... ({attempt}/{max_attempts})")
                attempt += 1
                await asyncio.sleep(1)

        if attempt >= max_attempts:
            kuaishou_logger.error("  ❌ 发布超时，请手动检查是否发布成功")
            await page.screenshot(path="kuaishou_publish_timeout.png")

        await context.storage_state(path=self.account_file)  # 保存cookie
        kuaishou_logger.info('cookie更新完毕！')
        kuaishou_logger.success('  [-]视频已成功发布，浏览器即将关闭')

        # 关闭浏览器
        await context.close()
        await browser.close()
        kuaishou_logger.info('  [-] 浏览器已关闭')

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
