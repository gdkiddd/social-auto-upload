# -*- coding: utf-8 -*-
import random
from datetime import datetime

from playwright.async_api import Playwright, async_playwright, Page
import os
import time
import asyncio

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS, get_step_delay
from utils.base_social_media import set_init_script
from utils.log import baijiahao_logger
from utils.network import async_retry
from myUtils.account_manager import get_current_account
from pathlib import Path
# 引入通用工具模块


async def baijiahao_cookie_gen(account_file):
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
        context = await set_init_script(context)
        # Pause the page, and start recording manually.
        page = await context.new_page()
        await page.goto("https://baijiahao.baidu.com/builder/theme/bjh/login")
        await page.pause()
        # 点击调试器的继续，保存cookie
        await context.storage_state(path=account_file)
        baijiahao_logger.success("cookie saved")


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
        await page.goto("https://baijiahao.baidu.com/builder/rc/home")
        await page.wait_for_timeout(timeout=5000)

        if await page.get_by_text('注册/登录百家号').count():
            baijiahao_logger.error("等待5秒 cookie 失效")
            return False
        else:
            baijiahao_logger.success("[+] cookie 有效")
            return True


async def baijiahao_setup(account_file, handle=False):
    if not os.path.exists(account_file) or not await cookie_auth(account_file):
        if not handle:
            return False
        baijiahao_logger.error("cookie文件不存在或已失效，即将自动打开浏览器，请扫码登录，登陆后会自动生成cookie文件")
        await baijiahao_cookie_gen(account_file)
    return True

class BaiJiaHaoVideo(object):
    def __init__(self, title, file_path, tags, publish_date: datetime, account_file, proxy_setting=None):
        self.title = title  # 视频标题
        self.file_path = file_path
        self.tags = tags
        self.publish_date = publish_date
        self.account_file = account_file
        self.date_format = '%Y年%m月%d日 %H:%M'
        self.local_executable_path = LOCAL_CHROME_PATH
        self.headless = LOCAL_CHROME_HEADLESS
        self.proxy_setting = proxy_setting
        self.step_delay = get_step_delay()  # 获取步骤延迟时间

    async def set_schedule_time(self, page, publish_date):
        """
        设置定时发布的时间
        todo 时间选择，日后在处理 百家号的时间选择不准确，目前是随机
        """
        publish_date_day = f"{publish_date.month}月{publish_date.day}日" if publish_date.day >9  else f"{publish_date.month}月0{publish_date.day}日"
        publish_date_hour = f"{publish_date.hour}点"
        publish_date_min = f"{publish_date.minute}分"

        baijiahao_logger.info(f"设置发布日期: {publish_date_day}")
        await page.wait_for_selector('div.select-wrap', timeout=5000)
        for _ in range(3):
            try:
                await page.locator('div.select-wrap').nth(0).click()
                await page.wait_for_selector('div.rc-virtual-list  div.cheetah-select-item', timeout=5000)
                break
            except:
                await page.locator('div.select-wrap').nth(0).click()
        await asyncio.sleep(self.step_delay)
        await page.locator(f'div.rc-virtual-list  div.cheetah-select-item >> text={publish_date_day}').click()
        await asyncio.sleep(self.step_delay)
        baijiahao_logger.success(f"日期设置成功: {publish_date_day}")

        # 改为随机点击一个 hour
        baijiahao_logger.info("设置发布时间（小时）...")
        for _ in range(3):
            try:
                await page.locator('div.select-wrap').nth(1).click()
                await page.wait_for_selector('div.rc-virtual-list div.rc-virtual-list-holder-inner:visible', timeout=5000)
                break
            except:
                await page.locator('div.select-wrap').nth(1).click()
        await asyncio.sleep(self.step_delay)
        current_choice_hour = await page.locator('div.rc-virtual-list:visible div.cheetah-select-item-option').count()
        await asyncio.sleep(self.step_delay)
        hour_index = random.randint(1, max(2, current_choice_hour-3))
        await page.locator('div.rc-virtual-list:visible div.cheetah-select-item-option').nth(hour_index).click()
        # 2024.08.05 current_choice_hour的获取可能有问题，页面有7，这里获取了10，暂时硬编码至6

        await asyncio.sleep(self.step_delay)

        # 最终确认点击"定时发布"按钮
        # 这个是确认按钮，使用主要样式（cheetah-btn-primary）
        baijiahao_logger.info("正在确认定时发布...")
        confirm_button = page.locator("button.cheetah-btn-primary:has-text('定时发布'), button.cheetah-btn-solid:has-text('定时发布')")
        if await confirm_button.count() > 0:
            await confirm_button.first.click()
            baijiahao_logger.success("定时发布确认成功")
        else:
            baijiahao_logger.error("未找到定时发布确认按钮")
            raise Exception("未找到定时发布确认按钮")


    async def handle_upload_error(self, page):
        # 日后实现，目前没遇到
        return
        print("视频出错了，重新上传中")

    async def upload(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例

        # 准备浏览器启动选项
        launch_options = {
            'headless': self.headless,
        }

        if self.local_executable_path:
            launch_options['executable_path'] = self.local_executable_path

        if self.proxy_setting:
            launch_options['proxy'] = self.proxy_setting

        browser = await playwright.chromium.launch(
            **launch_options
        )
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(
            viewport={"width": 800, "height": 600},
            storage_state=f"{self.account_file}",
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.4324.150 Safari/537.36'
        )
        # context = await set_init_script(context)
        await context.grant_permissions(['geolocation'])

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://baijiahao.baidu.com/builder/rc/edit?type=videoV2", timeout=60000)
        baijiahao_logger.info(f"正在上传-------{self.title}.mp4")
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        baijiahao_logger.info('正在打开主页...')
        await page.wait_for_url("https://baijiahao.baidu.com/builder/rc/edit?type=videoV2", timeout=60000)

        # 点击 "上传视频" 按钮
        await page.locator("div[class^='video-main-container'] input").set_input_files(self.file_path)

        # 等待页面跳转到指定的 URL
        while True:
            # 判断是是否进入视频发布页面，没进入，则自动等待到超时
            try:
                await page.wait_for_selector("div#formMain:visible")
                break
            except:
                baijiahao_logger.info("正在等待进入视频发布页面...")
                await asyncio.sleep(0.1)

        # 填充标题和话题
        await asyncio.sleep(self.step_delay)
        baijiahao_logger.info("正在填充标题和话题...")
        await self.add_title_tags(page)

        upload_status = await self.uploading_video(page)
        if not upload_status:
            baijiahao_logger.error(f"发现上传出错了... 文件:{self.file_path}")
            raise

        # 设置封面
        await self.set_cover(page)

        # 判断视频封面图是否生成成功
        while True:
            baijiahao_logger.info("正在确认封面完成, 准备去点击定时/发布...")
            if await page.locator("div.cheetah-spin-container img").count():
                baijiahao_logger.info("封面已完成，点击定时/发布...")
                break
            else:
                baijiahao_logger.info("等待封面生成...")
                await asyncio.sleep(self.step_delay)

        await self.publish_video(page, self.publish_date)
        await asyncio.sleep(self.step_delay)

        # 检查是否出现验证
        if await page.locator('div.passMod_dialog-container >> text=百度安全验证:visible').count():
            baijiahao_logger.warning("⚠️  检测到百度安全验证")
            baijiahao_logger.info("🔓 请手动完成验证操作")
            baijiahao_logger.warning("⚠️  需要人工介入，跳过此平台")
            # 验证需要人工处理，直接返回失败
            await context.close()
            await browser.close()
            return

        # 等待发布完成（不强制要求URL跳转）
        try:
            await page.wait_for_url("https://baijiahao.baidu.com/builder/rc/clue**", timeout=3000)
        except:
            # URL可能不跳转，检查是否有成功提示
            pass

        baijiahao_logger.success("视频发布成功")
        # 使用通用工具记录发布历史
        record_publish_history(
            platform_id='baijiahao',
            platform_name='百家号',
            video_file_path=self.file_path,
            status='success'
        )

        await context.storage_state(path=self.account_file)  # 保存cookie
        baijiahao_logger.info('cookie更新完毕！')
        baijiahao_logger.success('  [-]视频已成功发布，浏览器即将关闭')

        # 关闭浏览器
        await context.close()
        await browser.close()
        baijiahao_logger.info('  [-] 浏览器已关闭')


    @async_retry(timeout=300)  # 例如，最多重试3次，超时时间为180秒
    async def uploading_video(self, page):
        # 使用通用上传进度监控模块
        # 百家号的上传完成标志：没有"上传中"文本
        await wait_for_upload_with_progress(
            page=page,
            logger=baijiahao_logger,
            complete_indicators=[],  # 使用空列表，通过自定义逻辑判断完成
            check_interval=2,
            max_wait_time=300,
            progress_prefix="📊 上传进度"
        )

        # 再次检查是否真的完成了（百家号特殊处理）
        while True:
            upload_failed = await page.locator('div .cover-overlay:has-text("上传失败")').count()
            if upload_failed:
                baijiahao_logger.error("发现上传出错了...")
                return False

            uploading = await page.locator('div .cover-overlay:has-text("上传中")').count()
            if uploading:
                await asyncio.sleep(2)  # 等待2秒再次检查
                continue

            # 检查上传是否成功
            if not uploading and not upload_failed:
                baijiahao_logger.success("视频上传完毕")
                return True

    async def set_schedule_publish(self, page, publish_date):
        """点击定时发布按钮并设置发布时间"""
        baijiahao_logger.info("正在点击定时发布按钮（打开设置页面）...")
        while True:
            try:
                # 定位次要样式的定时发布按钮（cheetah-btn-default）
                # 这个按钮用于打开定时设置弹窗
                schedule_button = page.locator("button.cheetah-btn-default:has-text('定时发布'), button:has-text('定时发布').cheetah-btn-outlined")
                if await schedule_button.count() > 0:
                    await schedule_button.first.click()
                    baijiahao_logger.success("定时发布按钮点击成功")

                    # 等待时间选择器出现
                    await page.wait_for_selector('div.select-wrap:visible', timeout=5000)
                    await asyncio.sleep(self.step_delay)

                    baijiahao_logger.info("开始设置定时发布时间...")
                    await self.set_schedule_time(page, publish_date)
                    break
                else:
                    baijiahao_logger.error("未找到定时发布按钮")
                    raise Exception("未找到定时发布按钮")
            except Exception as e:
                baijiahao_logger.error(f"定时发布失败: {e}")
                raise  # 重新抛出异常，让重试装饰器捕获

    @async_retry(timeout=300)  # 例如，最多重试3次，超时时间为180秒
    async def publish_video(self, page: Page, publish_date):
        if publish_date != 0:
            # 定时发布
            await self.set_schedule_publish(page, publish_date)
        else:
            # 立即发布
            await self.direct_publish(page)

    async def direct_publish(self, page):
        try:
            # 使用 exact=True 精确匹配"发布"按钮，避免匹配到"定时发布"
            publish_button = page.get_by_text("发布", exact=True)
            if await publish_button.count() > 0:
                await publish_button.click()
                baijiahao_logger.info("已点击发布按钮")
                await asyncio.sleep(self.step_delay)
            else:
                baijiahao_logger.error("未找到发布按钮")
                raise Exception("未找到发布按钮")
        except Exception as e:
            baijiahao_logger.error(f"直接发布视频失败: {e}")
            raise  # 重新抛出异常，让重试装饰器捕获

    async def set_cover(self, page):
        """设置视频封面"""
        baijiahao_logger.info("  [-] 开始设置封面...")

        try:
            # 等待封面元素出现
            await asyncio.sleep(self.step_delay)

            # 点击"编辑封面"按钮 - 使用 first 避免匹配到多个元素
            cover_wrapper = page.locator('div[class*="coverWrapper"]').first
            if await cover_wrapper.count() == 0:
                baijiahao_logger.info("  [-] 未找到封面元素，跳过封面设置")
                return

            await cover_wrapper.click()
            await asyncio.sleep(self.step_delay)

            # 使用通用工具查找封面图片
            cover_file = find_cover_image(self.file_path)

            if not cover_file:
                baijiahao_logger.info("  [-] 未找到封面图片，跳过封面设置")
                return

            baijiahao_logger.info(f"  [-] 找到封面图片: {cover_file.name}")

            # 点击"本地上传"按钮并使用 file chooser API 选择文件
            local_upload_button = page.locator('div._28b32fc37e18461a-noimg:has-text("本地上传")')
            if await local_upload_button.count() == 0:
                baijiahao_logger.info("  [-] 未找到本地上传按钮，跳过封面设置")
                return

            # 使用 file chooser API
            async with page.expect_file_chooser() as fc_info:
                await local_upload_button.click()

            file_chooser = await fc_info.value
            await file_chooser.set_files(str(cover_file))
            baijiahao_logger.success(f"  [-] 封面图片已选择: {cover_file.name}")
            await asyncio.sleep(self.step_delay)

            # 点击"确定"
            confirm_button = page.locator('button:has-text("确定")')
            if await confirm_button.count() > 0:
                # 找到第一个可点击的确定按钮
                await confirm_button.first.click()
                baijiahao_logger.success("  [-] 封面设置成功")
                await asyncio.sleep(self.step_delay)
            else:
                baijiahao_logger.warning("  [-] 未找到确定按钮")

        except Exception as e:
            baijiahao_logger.error(f"  ❌ 封面设置失败: {str(e)}")
            # 封面设置失败不影响视频发布

    async def add_title_tags(self, page):
        """填充标题和话题标签"""
        # 填充标题
        title_container = page.get_by_placeholder('添加标题获得更多推荐')
        if len(self.title) <= 8:
            self.title += " 你不知道的"
        await title_container.fill(self.title[:30])
        await asyncio.sleep(self.step_delay)

        # 填充话题标签
        if self.tags:
            baijiahao_logger.info("  [-] 正在添加话题标签...")

            # 查找话题输入框
            topic_input = page.locator('input.edit-video-topic-input')
            if await topic_input.count() > 0:
                # 将标签转换为 #标签1 #标签2 格式
                tags_text = ' '.join([f"#{tag}" for tag in self.tags[:5]])  # 最多5个标签
                await topic_input.fill(tags_text)
                baijiahao_logger.success(f"  [-] 话题标签已添加: {tags_text}")
                await asyncio.sleep(self.step_delay)
            else:
                baijiahao_logger.info("  [-] 未找到话题输入框，跳过标签添加")

    async def main(self):
        async with async_playwright() as playwright:
            await self.upload(playwright)



    # 使用 AI成片 功能
    async def ai2video(self, playwright: Playwright) -> None:
        # 使用 Chromium 浏览器启动一个浏览器实例

        # 准备浏览器启动选项
        launch_options = {
            'headless': self.headless,
        }

        if self.local_executable_path:
            launch_options['executable_path'] = self.local_executable_path

        if self.proxy_setting:
            launch_options['proxy'] = self.proxy_setting

        browser = await playwright.chromium.launch(
            **launch_options
        )
        # 创建一个浏览器上下文，使用指定的 cookie 文件
        context = await browser.new_context(
            viewport={"width": 800, "height": 600},
            storage_state=f"{self.account_file}",
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.4324.150 Safari/537.36'
        )
        # context = await set_init_script(context)
        await context.grant_permissions(['geolocation'])

        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://aigc.baidu.com/make", timeout=60000)
        # 等待页面跳转到指定的 URL，没进入，则自动等待到超时
        baijiahao_logger.info('正在打开主页...')
        await page.wait_for_url("https://aigc.baidu.com/make", timeout=60000)

        # 点击"全网"标签
        await page.locator('div.rounded-lg.border:has-text("全网")').click()
        await asyncio.sleep(1)  # 这里延迟是为了方便眼睛直观的观看

        # 点击 "上传视频" 按钮
        # await page.locator("div[class^='video-main-container'] input").set_input_files(self.file_path)

        # region 操作处

        # 生成日期时间键名（格式：ai2video_YYYYMMDDHHMM）
        now = datetime.now()
        datetime_str = now.strftime("%Y%m%d%H%M")
        processed_key = "ai2video_processed_titles"
        batch_key = f"ai2video_{datetime_str}"

        # 初始化LocalStorage
        await page.evaluate(f"""
                   if (!localStorage.getItem("{processed_key}")) {{
                       localStorage.setItem("{processed_key}", JSON.stringify([]));                   
                   }}
                   if (!localStorage.getItem("{batch_key}")) {{
                       localStorage.setItem("{batch_key}", JSON.stringify([]));                   
                   }}
               """)

        # 定位新闻列表容器（转义特殊CSS字符）
        container_selector = r'.overflow-auto.flex-grow.h-0.saas-scrollbar.mt\-\[-4px\].pl\-\[24px\].pr\-\[10px\].pb\-\[18px\]'
        news_items = await page.locator(container_selector).locator(r'div.py\-\[6px\].group.cursor-pointer').all()

        for item in news_items:
            try:
                # 获取新闻标题
                title_elem = item.locator(r'div.flex.text-gray-darker.items-center.relative.pr\-\[56px\] > span')
                title = await title_elem.text_content()
                if not title:
                    continue

                # 检查是否已处理过
                is_processed = await page.evaluate(
                    f"""title => {{
                               const processedList = JSON.parse(localStorage.getItem("{processed_key}") || "[]");
                               return processedList.includes(title);
                           }}""",
                    title
                )

                if is_processed:
                    print(f"[跳过] {title}")
                    continue

                # 悬停显示按钮（根据HTML结构，按钮在悬停时显示）
                await item.hover()

                # 点击生成文案按钮
                button = item.locator('button:has-text("生成文案")')
                await button.click()
                print(f"[点击] {title}")

                # 等待30秒
                # await page.wait_for_timeout(30000)
                print(f"[等待完成] {title}")
                
                # 监听"一键成片"按钮
                print(f"[开始监听] 一键成片按钮")
                should_exit_while_loop = False  # 添加标志变量
                while True:
                    # 定位"一键成片"按钮
                    one_key_button = page.locator("button:has-text('一键成片')")
                    
                    # 检查按钮是否存在
                    if await one_key_button.count() > 0:
                        # 检查按钮是否有disabled属性
                        is_disabled = await one_key_button.get_attribute("disabled")
                        
                        if is_disabled is None:
                            # 按钮不再被禁用，点击它
                            print(f"[发现可点击按钮] 一键成片")
                            await one_key_button.click()  # 先点击一键成片按钮
                            
                            # 等待可能出现的"温馨提示"窗口
                            print(f"[检查] 是否出现温馨提示窗口")
                            await page.wait_for_timeout(2000)  # 等待2秒，让窗口有时间显示
                            
                            try:
                                # 检查是否存在"温馨提示"窗口，设置较短的超时时间
                                tip_window = page.locator("div:has-text('温馨提示') >> visible=true")
                                if await tip_window.count() > 0:
                                    print(f"[发现] 温馨提示窗口")
                                    
                                    # 定位并点击"知道了"按钮，设置较短的超时时间
                                    know_button = page.locator("button:has-text('知道了')")
                                    if await know_button.count() > 0:
                                        try:
                                            # 设置较短的超时时间进行点击
                                            await know_button.click(timeout=5000)
                                            print(f"[已点击] 知道了按钮")
                                        except Exception as e:
                                            print(f"[警告] 点击知道了按钮时出错: {str(e)}")
                                    else:
                                        print(f"[警告] 未找到知道了按钮")
                                else:
                                    print(f"[信息] 未出现温馨提示窗口，继续执行")
                            except Exception as e:
                                print(f"[警告] 处理温馨提示窗口时出错: {str(e)}")
                                # 继续执行，不要因为这个错误中断流程
                                
                            # 记录到LocalStorage前打印日志
                            print(f"[开始记录] 准备将标题 '{title}' 记录到LocalStorage")
                            
                            # 记录到LocalStorage
                            await page.evaluate(
                                f"""
                                        (title, processedKey, batchKey) => {{
                                            // 更新已处理列表
                                            const processedList = JSON.parse(localStorage.getItem(processedKey) || "[]");
                                            if (!processedList.includes(title)) {{
                                                processedList.push(title);
                                                localStorage.setItem(processedKey, JSON.stringify(processedList));
                                            }}

                                            // 更新当前批次记录
                                            const batchList = JSON.parse(localStorage.getItem(batchKey) || "[]");
                                            if (!batchList.includes(title)) {{
                                                batchList.push(title);
                                                localStorage.setItem(batchKey, JSON.stringify(batchList));
                                            }}
                                        }}
                                        """,
                                title, processed_key, batch_key
                            )
                            
                            # 记录完成后打印日志
                            print(f"[记录完成] 标题 '{title}' 已成功记录到LocalStorage")

                            print(f"[记录完成] {title}")
                            
                            # 监听新打开的标签页
                            print(f"[监听] 等待新标签页打开")
                            # 获取当前所有页面
                            current_pages = context.pages
                            current_page_count = len(current_pages)
                            
                            # 等待新标签页打开（最多等待10秒）
                            new_page = None
                            max_wait_time = 10  # 最大等待时间（秒）
                            start_time = time.time()
                            
                            while time.time() - start_time < max_wait_time:
                                # 获取最新的页面列表
                                pages = context.pages
                                # 如果页面数量增加，说明新标签页已打开
                                if len(pages) > current_page_count:
                                    # 获取最新打开的页面（通常是列表中的最后一个）
                                    new_page = pages[-1]
                                    print(f"[发现] 新标签页已打开")
                                    break
                                # 短暂等待后再次检查
                                await asyncio.sleep(0.5)
                            
                            # 如果找到新标签页，获取其标题和URL并保存
                            if new_page:
                                # 等待页面加载完成
                                try:
                                    await new_page.wait_for_load_state("domcontentloaded", timeout=5000)
                                    # 获取页面标题和URL
                                    page_title = await new_page.title()
                                    page_url = new_page.url
                                    
                                    print(f"[获取] 标题: {page_title}")
                                    print(f"[获取] URL: {page_url}")
                                    
                                    # 将标题和URL保存到url.txt文件
                                    with open("url.txt", "a", encoding="utf-8") as f:
                                        f.write(f"{page_title}\n{page_url}\n\n")
                                    
                                    print(f"[保存] 标题和URL已保存到url.txt")
                                    
                                    # 等待5秒后关闭新标签页
                                    print(f"[等待] 5秒后将关闭新标签页")
                                    await asyncio.sleep(5)
                                    await new_page.close()
                                    print(f"[关闭] 新标签页已关闭")
                                except Exception as e:
                                    print(f"[错误] 处理新标签页时出错: {str(e)}")
                                    try:
                                        # 尝试关闭页面，即使出错
                                        await new_page.close()
                                        print(f"[关闭] 新标签页已关闭（出错后）")
                                    except:
                                        pass
                            else:
                                print(f"[警告] 未检测到新标签页打开")
                            
                            # 跳出整个while循环
                            print(f"[操作] 跳出所有循环，不再处理其他新闻")
                            should_exit_while_loop = True  # 设置标志变量
                            break  # 跳出while循环
                    
                    # 检查是否需要跳出while循环
                    if should_exit_while_loop:
                        break
                        
                    # 每秒检查一次按钮状态
                    await page.wait_for_timeout(1000)
                
                # 检查是否需要跳出for循环
                if should_exit_while_loop:
                    print(f"[操作] 跳出for循环，完全结束处理")
                    break  # 跳出for循环
            except Exception as e:
                print(f"处理新闻时出错: {str(e)}")
                continue


        # endregion 操作处

        print(f"[循环完成] 准备关闭浏览器")

        # 退出前保存 storage 信息
        await context.storage_state(path=self.account_file)  # 保存cookie
        baijiahao_logger.info('cookie更新完毕！')
        baijiahao_logger.success('  [-]视频已成功发布，浏览器即将关闭')

        # 关闭浏览器
        await context.close()
        await browser.close()
        baijiahao_logger.info('  [-] 浏览器已关闭')


    async def mainAi(self):
        async with async_playwright() as playwright:
            await self.ai2video(playwright)
