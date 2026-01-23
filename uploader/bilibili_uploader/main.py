# -*- coding: utf-8 -*-
import pathlib
import asyncio
from playwright.async_api import async_playwright, Page
from pathlib import Path

from conf import LOCAL_CHROME_PATH, LOCAL_CHROME_HEADLESS, get_step_delay
from utils.base_social_media import set_init_script
from utils.log import bilibili_logger
from myUtils.publish_history import get_publish_history
from myUtils.account_manager import get_current_account


class BilibiliUploader(object):
  def __init__(self, account_file, file: pathlib.Path, title, desc, tid, tags, dtime):
    self.account_file = account_file
    self.file = file
    self.title = title
    self.desc = desc
    self.tid = tid
    self.tags = tags
    self.dtime = dtime
    self.local_executable_path = LOCAL_CHROME_PATH
    self.headless = LOCAL_CHROME_HEADLESS
    self.step_delay = get_step_delay()

  async def upload(self):
    """使用 Playwright 上传视频到 Bilibili"""
    async with async_playwright() as playwright:
      # 准备浏览器启动选项
      launch_options = {
        'headless': self.headless,
      }

      if self.local_executable_path:
        launch_options['executable_path'] = self.local_executable_path

      browser = await playwright.chromium.launch(**launch_options)

      # 创建浏览器上下文，使用 cookie 文件
      context = await browser.new_context(
        viewport={"width": 1250, "height": 1250},
        storage_state=f"{self.account_file}"
      )
      context = await set_init_script(context)

      # 创建新页面
      page = await context.new_page()

      # 访问 Bilibili 创作中心
      bilibili_logger.info(f'📹 正在上传: {self.file.name}')
      bilibili_logger.info(f'   文件大小: {self.file.stat().st_size / (1024*1024):.1f} MB')
      bilibili_logger.info(f'   标题: {self.title}')
      bilibili_logger.info(f'   标签: {", ".join(self.tags) if self.tags else "无"}')
      bilibili_logger.info(f'   分区: tid={self.tid}')

      bilibili_logger.info(f'   正在打开 Bilibili 创作中心...')
      await page.goto("https://member.bilibili.com/platform/upload/video/frame")
      await asyncio.sleep(self.step_delay)

      # 点击上传视频按钮，选择视频文件
      bilibili_logger.info(f'   正在选择视频文件...')

      # 等待页面完全加载
      bilibili_logger.info('   [-] 等待页面加载完成...')
      await page.wait_for_load_state('networkidle', timeout=10000)
      await asyncio.sleep(self.step_delay)

      # 调试：检查页面元素
      file_inputs = page.locator('input[type="file"]')
      input_count = await file_inputs.count()
      bilibili_logger.info(f'   [-] 找到 {input_count} 个文件输入框')

      # 方法1：直接设置 file input（即使隐藏的也可以工作）
      upload_video_input = page.locator('input[type="file"][accept=".mp4"]')
      if await upload_video_input.count() > 0:
        bilibili_logger.info('   [-] 找到 mp4 上传输入框，直接设置文件')
        await upload_video_input.set_input_files(str(self.file))
        bilibili_logger.success(f'   ✅ 视频文件已选择（直接设置）')
      else:
        # 方法2：点击上传区域触发文件选择
        bilibili_logger.info('   [-] 未找到 mp4 输入框，尝试点击上传区域...')

        # 尝试多个可能的上传区域选择器
        upload_area_selectors = [
          'div.upload-area',
          'div.bcc-upload-wrapper',
          'div.bcc-upload',
          '.upload-area'
        ]

        upload_area = None
        for selector in upload_area_selectors:
          test_area = page.locator(selector)
          if await test_area.count() > 0:
            bilibili_logger.info(f'   [-] 找到上传区域: {selector}')
            upload_area = test_area
            break

        if upload_area:
          try:
            async with page.expect_file_chooser(timeout=5000) as fc_info:
              await upload_area.first.click()

            file_chooser = await fc_info.value
            await file_chooser.set_files(str(self.file))
            bilibili_logger.success(f'   ✅ 视频文件已选择（通过点击）')
          except Exception as e:
            bilibili_logger.error(f'   ❌ 点击上传区域失败: {e}')
            # 截图调试
            await page.screenshot(path='bilibili_upload_debug.png')
            bilibili_logger.info('   [-] 已保存截图: bilibili_upload_debug.png')
            return False
        else:
          bilibili_logger.error('   ❌ 未找到上传区域')
          # 截图调试
          await page.screenshot(path='bilibili_upload_debug.png')
          bilibili_logger.info('   [-] 已保存截图: bilibili_upload_debug.png')
          return False

      await asyncio.sleep(self.step_delay)

      # 等待视频上传完成
      bilibili_logger.info(f'   正在等待视频上传...')
      await self._wait_video_upload(page)
      bilibili_logger.success(f'   ✅ 视频上传完成')

      # 填充视频信息
      await self._fill_video_info(page)
      bilibili_logger.success(f'   ✅ 视频信息已填充')

      # 设置封面
      await self._set_cover(page)

      # 提交视频
      await self._submit_video(page)

      # 保存 cookie
      await context.storage_state(path=self.account_file)
      bilibili_logger.success('   ✅ Cookie 已更新')

      # 保持浏览器打开一段时间，方便手动操作
      bilibili_logger.info('   💡 浏览器将保持打开 5 分钟，方便手动操作')
      await asyncio.sleep(300)

      await context.close()
      await browser.close()

      return True

  async def _wait_video_upload(self, page: Page):
    """等待视频上传完成"""
    bilibili_logger.info('   [-] 等待视频上传进度...')

    # 等待上传进度条消失或上传完成标志出现
    max_wait_time = 600  # 最大等待时间 10 分钟
    wait_time = 0

    while wait_time < max_wait_time:
      try:
        # 检查是否有上传完成的标志
        upload_complete = page.locator('text="上传完成"')

        if await upload_complete.count() > 0:
          bilibili_logger.success('   [-] 视频上传完成')
          await asyncio.sleep(self.step_delay)
          return

        # 如果没有进度条了，可能上传已完成
        # 等待一下确认
        await asyncio.sleep(5)
        wait_time += 5
        bilibili_logger.info(f'   [-] 上传中... 已等待 {wait_time} 秒')

      except Exception as e:
        bilibili_logger.warning(f'   [-] 等待上传时出错: {e}')
        await asyncio.sleep(5)
        wait_time += 5

    bilibili_logger.warning('   [-] 上传等待超时，继续后续步骤')

  async def _fill_video_info(self, page: Page):
    """填充视频信息：标题、标签、简介"""
    bilibili_logger.info('   [-] 正在填充视频信息...')

    await asyncio.sleep(self.step_delay)

    # 填充标题
    bilibili_logger.info(f'   [-] 填充标题: {self.title}')
    title_input = page.locator('input[placeholder="请输入稿件标题"]')
    if await title_input.count() > 0:
      await title_input.first.fill(self.title)
      await asyncio.sleep(self.step_delay)
    else:
      bilibili_logger.warning('   [-] 未找到标题输入框')

    # 填充简介（标题 + 标签）
    bilibili_logger.info('   [-] 填充简介...')
    desc_editor = page.locator('.ql-editor[contenteditable="true"]')
    if await desc_editor.count() > 0:
      # 内容 = 标题 + 标签
      if self.tags:
        tags_str = ' '.join([f"#{tag}" for tag in self.tags])
        desc_content = f"{self.title}\n{tags_str}"
      else:
        desc_content = self.title

      await desc_editor.first.fill(desc_content)
      await asyncio.sleep(self.step_delay)
    else:
      bilibili_logger.warning('   [-] 未找到简介输入框')

    # 填充标签
    if self.tags:
      bilibili_logger.info(f'   [-] 填充标签: {", ".join(self.tags)}')
      tag_input = page.locator('input[placeholder="按回车键Enter创建标签"]')
      if await tag_input.count() > 0:
        for tag in self.tags:
          await tag_input.first.fill(tag)
          await asyncio.sleep(0.5)
          # 按回车确认标签
          await page.keyboard.press('Enter')
          await asyncio.sleep(0.5)
        await asyncio.sleep(self.step_delay)
      else:
        bilibili_logger.warning('   [-] 未找到标签输入框')

  async def _set_cover(self, page: Page):
    """设置视频封面"""
    bilibili_logger.info('   [-] 正在设置封面...')

    try:
      # 查找封面图片
      video_file = Path(self.file)
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
          image_patterns = ['*.png', '*.PNG', '*.jpg', '*.jpeg', '*.JPG', '*.JPEG']
          for pattern in image_patterns:
            images = list(videos_dir.glob(pattern))
            if images:
              cover_file = images[0]
              break

      if not cover_file:
        bilibili_logger.info('   [-] 未找到封面图片，跳过封面设置')
        return

      bilibili_logger.info(f"   [-] 找到封面图片: {cover_file.name}")

      await asyncio.sleep(self.step_delay)

      # 步骤1：点击"封面设置"区域
      cover_setting_area = page.locator('div.cover-content >> div.cover-main-img')
      if await cover_setting_area.count() > 0:
        await cover_setting_area.first.click()
        bilibili_logger.info('   [-] 已点击封面设置区域')
        await asyncio.sleep(self.step_delay)
      else:
        bilibili_logger.warning('   [-] 未找到封面设置区域')
        return

      # 步骤2：等待并点击"上传封面"按钮
      # 根据用户提供的HTML，使用正确的选择器
      upload_cover_button = page.locator('div.cover-upload.cover-editor-panel-select-item')
      if await upload_cover_button.count() == 0:
        # 备用选择器
        upload_cover_button = page.locator('div.bcc-upload.cover-upload >> div.upload-area')

      if await upload_cover_button.count() > 0:
        bilibili_logger.info('   [-] 找到上传封面按钮，正在点击...')
        # 使用 file chooser API
        async with page.expect_file_chooser(timeout=10000) as fc_info:
          await upload_cover_button.first.click()

        file_chooser = await fc_info.value
        await file_chooser.set_files(str(cover_file))
        bilibili_logger.success(f'   [-] 封面图片已选择: {cover_file.name}')
        await asyncio.sleep(self.step_delay)

        # 步骤3：点击"双比例同步改动"复选框
        bilibili_logger.info('   [-] 正在查找"双比例同步改动"复选框...')
        await asyncio.sleep(self.step_delay)

        sync_checkbox = page.locator('label.sync-checkbox.bcc-checkbox')
        if await sync_checkbox.count() > 0:
          await sync_checkbox.first.click()
          bilibili_logger.success('   [-] 已点击"双比例同步改动"')
          await asyncio.sleep(self.step_delay)
        else:
          bilibili_logger.warning('   [-] 未找到"双比例同步改动"复选框，跳过')

        # 步骤4：等待并点击"完成"按钮
        bilibili_logger.info('   [-] 正在查找完成按钮...')
        await asyncio.sleep(self.step_delay)

        # 根据用户提供的HTML，使用正确的选择器
        finish_button = page.locator('div.button.submit.button.submit:has-text("完成")')
        if await finish_button.count() == 0:
          # 备用选择器
          finish_button = page.locator('div[class*="submit"]:has-text("完成")')

        if await finish_button.count() > 0:
          await finish_button.first.click()
          bilibili_logger.success('   [-] 已点击完成按钮')
          await asyncio.sleep(self.step_delay)
        else:
          bilibili_logger.warning('   [-] 未找到完成按钮，跳过')
      else:
        bilibili_logger.warning('   [-] 未找到上传封面按钮，跳过封面设置')

    except Exception as e:
      bilibili_logger.error(f'   ❌ 封面设置失败: {str(e)}')
      import traceback
      bilibili_logger.error(traceback.format_exc())

  async def _submit_video(self, page: Page):
    """提交视频"""
    bilibili_logger.info('   [-] 正在提交视频...')

    await asyncio.sleep(self.step_delay)

    # 点击"立即投稿"按钮
    submit_button = page.locator('span.submit-add:has-text("立即投稿")')

    if await submit_button.count() == 0:
      # 备用选择器
      submit_button = page.locator('.submit-add')

    if await submit_button.count() == 0:
      bilibili_logger.error('   ❌ 未找到提交按钮')
      return False

    await submit_button.first.click()
    bilibili_logger.success('   [-] 已点击提交按钮')

    # 等待提交完成
    await asyncio.sleep(5)

    # 检查是否提交成功
    # 尝试多个可能的成功提示
    success_indicators = [
      page.locator('text="投稿成功"'),
      page.locator('text="发布成功"'),
      page.locator('text="提交成功"')
    ]

    found_success = False
    for indicator in success_indicators:
      if await indicator.count() > 0:
        found_success = True
        break

    if found_success:
      bilibili_logger.success('✅ 视频提交成功')
      bilibili_logger.info('🔗 查看上传结果: https://member.bilibili.com/platform/upload-manager/article')

      # 记录发布历史
      publish_history = get_publish_history()
      publish_history.add_record(
        platform_id='bilibili',
        platform_name='Bilibili',
        video_file=self.file.name,
        status='success',
        account=get_current_account()
      )
      return True
    else:
      bilibili_logger.warning('   [-] 未检测到成功提示，请手动确认')
      return False
