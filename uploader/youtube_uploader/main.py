# -*- coding: utf-8 -*-
import pathlib
import asyncio
from playwright.async_api import async_playwright, Page
from pathlib import Path

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS, get_step_delay
from utils.base_social_media import set_init_script
from utils.log import youtube_logger
from myUtils.publish_history import get_publish_history
from myUtils.account_manager import get_current_account


class YouTubeUploader(object):
  def __init__(self, account_file, file: pathlib.Path, title, desc, tags, thumbnail_path=None):
    self.account_file = account_file
    self.file = file
    self.title = title
    self.desc = desc
    self.tags = tags
    self.thumbnail_path = thumbnail_path
    self.local_executable_path = LOCAL_CHROME_PATH
    self.headless = LOCAL_CHROME_HEADLESS
    self.step_delay = get_step_delay()

  async def upload(self):
    """使用 Playwright 上传视频到 YouTube"""
    async with async_playwright() as playwright:
      # 使用本地 Chrome 的用户数据目录，继承登录状态
      import os
      home_dir = os.path.expanduser('~')
      chrome_user_data_dir = os.path.join(home_dir, 'Library', 'Application Support', 'Google', 'Chrome')

      youtube_logger.info(f'   [-] 使用本地 Chrome 用户数据目录: {chrome_user_data_dir}')
      youtube_logger.warning('   ⚠️  请确保已关闭 Chrome 浏览器，否则会报错！')

      # 使用 launch_persistent_context 直接创建持久化上下文
      context = await playwright.chromium.launch_persistent_context(
        user_data_dir=chrome_user_data_dir,
        headless=self.headless,
        executable_path=self.local_executable_path,
        viewport={'width': 800, 'height': 600},
        locale='zh-CN',
        timezone_id='Asia/Shanghai',
        args=[
          '--disable-blink-features=AutomationControlled',
          '--disable-dev-shm-usage',
          '--no-sandbox',
          '--disable-setuid-sandbox'
        ]
      )

      context = await set_init_script(context)

      # 创建新页面
      page = await context.new_page()

      # 额外：覆盖 navigator.webdriver 等检测
      await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
          get: () => undefined
        });
        Object.defineProperty(navigator, 'plugins', {
          get: () => [1, 2, 3, 4, 5]
        });
        Object.defineProperty(navigator, 'languages', {
          get: () => ['zh-CN', 'zh', 'en-US', 'en']
        });
        Object.defineProperty(navigator, 'platform', {
          get: () => 'Win32'
        });
        window.chrome = {
          runtime: {}
        };
      """)

      # 访问 YouTube Studio 上传页
      youtube_logger.info(f'📹 正在上传: {self.file.name}')
      youtube_logger.info(f'   文件大小: {self.file.stat().st_size / (1024*1024):.1f} MB')
      youtube_logger.info(f'   标题: {self.title}')
      youtube_logger.info(f'   标签: {", ".join(self.tags) if self.tags else "无"}')

      youtube_logger.info(f'   正在打开 YouTube Studio...')
      await page.goto("https://studio.youtube.com/channel/videos/upload?d=ud", wait_until='networkidle')
      await asyncio.sleep(self.step_delay)

      # 等待页面完全加载
      youtube_logger.info('   [-] 等待页面加载完成...')
      await page.wait_for_load_state('networkidle', timeout=30000)
      await asyncio.sleep(self.step_delay)

      # 步骤1：选择视频文件
      youtube_logger.info('   [-] 步骤1: 选择视频文件...')
      await self._select_video_file(page)
      youtube_logger.success('   ✅ 视频文件已选择')

      # 等待跳转到上传详情页
      youtube_logger.info('   [-] 等待跳转到上传详情页...')
      await asyncio.sleep(3)
      await page.wait_for_load_state('networkidle', timeout=30000)

      # 步骤2：填写标题
      youtube_logger.info('   [-] 步骤2: 填写标题...')
      await self._fill_title(page)
      youtube_logger.success('   ✅ 标题已填写')

      # 步骤3：填写说明
      youtube_logger.info('   [-] 步骤3: 填写说明...')
      await self._fill_description(page)
      youtube_logger.success('   ✅ 说明已填写')

      # 步骤4：上传缩略图
      if self.thumbnail_path:
        youtube_logger.info('   [-] 步骤4: 上传缩略图...')
        await self._upload_thumbnail(page)
        youtube_logger.success('   ✅ 缩略图已上传')
      else:
        youtube_logger.info('   [-] 跳过缩略图上传')

      # 步骤5：选择"不，内容不是面向儿童的"
      youtube_logger.info('   [-] 步骤5: 设置儿童内容选项...')
      await self._set_not_made_for_kids(page)
      youtube_logger.success('   ✅ 已设置为非儿童内容')

      # 步骤6：点击"继续"按钮 3 次
      youtube_logger.info('   [-] 步骤6: 点击继续按钮...')
      await self._click_next_buttons(page)
      youtube_logger.success('   ✅ 已点击继续按钮')

      # 步骤7：设置公开范围
      youtube_logger.info('   [-] 步骤7: 设置公开范围...')
      await self._set_visibility_public(page)
      youtube_logger.success('   ✅ 已设置为公开')

      # 步骤8：发布视频
      youtube_logger.info('   [-] 步骤8: 发布视频...')
      await self._publish_video(page)
      youtube_logger.success('   ✅ 视频发布成功')

      # 保存 cookie（可选，因为使用本地 Chrome 数据目录）
      # await context.storage_state(path=self.account_file)

      # 关闭浏览器
      await context.close()
      youtube_logger.info('   [-] 浏览器已关闭')

      # 记录发布历史
      publish_history = get_publish_history()
      publish_history.add_record(
        platform_id='youtube',
        platform_name='YouTube',
        video_file=self.file.name,
        status='success',
        account=get_current_account()
      )

      return True

  async def _select_video_file(self, page: Page):
    """选择视频文件"""
    try:
      # 等待页面完全加载
      await asyncio.sleep(2)

      # 检查是否在首页，如果是则点击"创建"按钮
      create_button = page.locator('ytcp-button:has-text("创建"), button:has-text("创建")')
      if await create_button.count() > 0:
        youtube_logger.info('   [-] 检测到首页，点击"创建"按钮')
        await create_button.first.click()
        await asyncio.sleep(3)
        await page.wait_for_load_state('networkidle', timeout=30000)

      # 方法1：尝试直接查找文件输入框
      file_input = page.locator('input[type="file"]')
      if await file_input.count() > 0:
        youtube_logger.info('   [-] 找到文件输入框，直接设置文件')
        await file_input.set_input_files(str(self.file))
        await asyncio.sleep(self.step_delay)
        return

      # 方法2：点击"选择文件"按钮，使用 file chooser
      youtube_logger.info('   [-] 未找到文件输入框，尝试点击上传按钮')

      # 等待并点击"选择文件"按钮（尝试多个可能的选择器）
      upload_button_selectors = [
        'text="选择文件"',
        'text="SELECT FILE"',
        '#upload-button',
        'ytcp-button:has-text("选择文件")',
        'button:has-text("上传")',
        '[class*="upload"] button'
      ]

      button_clicked = False
      for selector in upload_button_selectors:
        try:
          button = page.locator(selector).first
          if await button.count() > 0 and await button.is_visible():
            youtube_logger.info(f'   [-] 找到上传按钮: {selector}')

            # 使用 file chooser API
            async with page.expect_file_chooser(timeout=5000) as fc_info:
              await button.click()

            file_chooser = await fc_info.value
            await file_chooser.set_files(str(self.file))
            youtube_logger.success(f'   [-] 已选择文件: {self.file.name}')
            button_clicked = True
            await asyncio.sleep(self.step_delay)
            break
        except Exception as e:
          youtube_logger.debug(f'   [-] 选择器 {selector} 失败: {e}')
          continue

      if not button_clicked:
        # 如果所有方法都失败，抛出异常
        raise Exception('无法找到文件上传按钮或输入框')

    except Exception as e:
      youtube_logger.error(f'   ❌ 选择视频文件失败: {e}')
      await page.screenshot(path='youtube_select_video_debug.png')
      raise

  async def _fill_title(self, page: Page):
    """填写标题"""
    try:
      # 等待标题输入框出现
      title_textbox = page.locator('#title-textarea #textbox[contenteditable="true"]')
      await title_textbox.wait_for(state='visible', timeout=10000)

      # 清空并填写标题
      await title_textbox.click()
      await asyncio.sleep(0.5)
      await page.keyboard.press('Control+A')
      await asyncio.sleep(0.3)
      await page.keyboard.type(self.title)
      await asyncio.sleep(self.step_delay)
    except Exception as e:
      youtube_logger.error(f'   ❌ 填写标题失败: {e}')
      await page.screenshot(path='youtube_title_debug.png')
      raise

  async def _fill_description(self, page: Page):
    """填写说明（标题 + 标签）"""
    try:
      # 等待说明输入框出现
      desc_textbox = page.locator('#description-textarea #textbox[contenteditable="true"]')
      await desc_textbox.wait_for(state='visible', timeout=10000)

      # 构建说明内容
      desc_content = self.title
      if self.tags:
        tags_str = ' '.join([f"#{tag}" for tag in self.tags])
        desc_content = f"{self.title}\n{tags_str}"

      # 填写说明
      await desc_textbox.click()
      await asyncio.sleep(0.5)
      await page.keyboard.type(desc_content)
      await asyncio.sleep(self.step_delay)
    except Exception as e:
      youtube_logger.error(f'   ❌ 填写说明失败: {e}')
      await page.screenshot(path='youtube_description_debug.png')
      raise

  async def _upload_thumbnail(self, page: Page):
    """上传缩略图"""
    try:
      # 查找"上传文件"按钮
      upload_button = page.locator('#select-button[aria-label="上传文件"]')

      if await upload_button.count() > 0:
        # 使用 file chooser API
        async with page.expect_file_chooser(timeout=10000) as fc_info:
          await upload_button.click()

        file_chooser = await fc_info.value
        await file_chooser.set_files(str(self.thumbnail_path))
        youtube_logger.success(f'   [-] 缩略图文件已选择: {self.thumbnail_path.name}')
        await asyncio.sleep(2)
      else:
        youtube_logger.warning('   [-] 未找到上传缩略图按钮')
    except Exception as e:
      youtube_logger.error(f'   ❌ 上传缩略图失败: {e}')
      await page.screenshot(path='youtube_thumbnail_debug.png')
      # 缩略图上传失败不影响主流程，继续执行

  async def _set_not_made_for_kids(self, page: Page):
    r'''设置"不，内容不是面向儿童的"'''
    try:
      # 等待单选框出现
      not_made_for_kids = page.locator('tp-yt-paper-radio-button[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')
      await not_made_for_kids.wait_for(state='visible', timeout=10000)

      # 点击"不，内容不是面向儿童的"
      await not_made_for_kids.click()
      await asyncio.sleep(self.step_delay)
    except Exception as e:
      youtube_logger.error(f'   ❌ 设置儿童内容选项失败: {e}')
      await page.screenshot(path='youtube_kids_debug.png')
      raise

  async def _click_next_buttons(self, page: Page):
    r'''点击"继续"按钮 3 次（每次间隔 2 秒）'''
    try:
      for i in range(3):
        youtube_logger.info(f'   [-] 点击继续按钮 {i+1}/3...')

        # 查找"继续"按钮（可能有多个选择器）
        next_button = page.locator('ytcp-button:has-text("继续")')

        if await next_button.count() == 0:
          next_button = page.locator('button:has-text("下一步")')

        if await next_button.count() == 0:
          next_button = page.locator('#next-button')

        if await next_button.count() > 0:
          await next_button.first.click()
          youtube_logger.success(f'   [-] 已点击继续按钮 {i+1}/3')
          await asyncio.sleep(2)
        else:
          youtube_logger.warning(f'   [-] 未找到继续按钮 {i+1}/3，可能已完成')
          await asyncio.sleep(1)
    except Exception as e:
      youtube_logger.error(f'   ❌ 点击继续按钮失败: {e}')
      await page.screenshot(path='youtube_next_debug.png')
      raise

  async def _set_visibility_public(self, page: Page):
    r'''设置公开范围为"公开"'''
    try:
      # 等待公开范围单选框出现
      public_radio = page.locator('tp-yt-paper-radio-button[name="PUBLIC"]')

      # 如果当前未选中，则点击"公开"
      if await public_radio.count() > 0:
        is_checked = await public_radio.get_attribute('aria-checked')
        if is_checked != 'true':
          await public_radio.click()
          youtube_logger.success('   [-] 已设置为公开')
          await asyncio.sleep(self.step_delay)
        else:
          youtube_logger.info('   [-] 已经是公开状态')
      else:
        youtube_logger.warning('   [-] 未找到公开选项，可能已默认公开')
    except Exception as e:
      youtube_logger.error(f'   ❌ 设置公开范围失败: {e}')
      await page.screenshot(path='youtube_visibility_debug.png')
      raise

  async def _publish_video(self, page: Page):
    """发布视频"""
    try:
      # 查找"发布"按钮
      publish_button = page.locator('ytcp-button:has-text("发布")')

      if await publish_button.count() == 0:
        publish_button = page.locator('button:has-text("发布")')

      if await publish_button.count() > 0:
        await publish_button.first.click()
        youtube_logger.success('   [-] 已点击发布按钮')
        await asyncio.sleep(3)

        # 等待发布完成（检查是否跳转到视频列表）
        try:
          await page.wait_for_url('**/channel/videos/**', timeout=30000)
          youtube_logger.success('   [-] 视频发布成功，已跳转到视频列表')
        except:
          youtube_logger.warning('   [-] 未检测到页面跳转，但发布按钮已点击')
      else:
        youtube_logger.error('   ❌ 未找到发布按钮')
        await page.screenshot(path='youtube_publish_debug.png')
    except Exception as e:
      youtube_logger.error(f'   ❌ 发布视频失败: {e}')
      await page.screenshot(path='youtube_publish_error_debug.png')
      raise
