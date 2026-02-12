import asyncio
import configparser
import os
import base64
import requests

from playwright.async_api import async_playwright
from xhs import XhsClient

from conf import BASE_DIR, LOCAL_CHROME_HEADLESS, get_bark_url, get_telegram_config
from utils.base_social_media import set_init_script
from utils.log import tencent_logger, kuaishou_logger, douyin_logger
from pathlib import Path
from uploader.xhs_uploader.main import sign_local

# Telegram Bot配置
def load_telegram_config():
    """从config.json加载Telegram Bot配置"""
    try:
        telegram_config = get_telegram_config()
        bot_token = telegram_config.get('bot_token')
        chat_id = telegram_config.get('chat_id')

        return bot_token, chat_id
    except Exception as e:
        tencent_logger.error(f"[+] 加载Telegram配置失败: {e}")
        return None, None


def send_telegram_photo(photo_path, caption=None):
    """通过Telegram Bot发送图片

    Args:
        photo_path: 图片文件路径
        caption: 图片说明文字

    Returns:
        bool: 是否发送成功
    """
    try:
        bot_token, chat_id = load_telegram_config()

        if not bot_token or not chat_id:
            tencent_logger.error("[+] Telegram Bot配置不完整")
            return False

        # Telegram Bot API URL
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

        # 准备请求数据
        files = {
            'photo': open(photo_path, 'rb')
        }
        data = {
            'chat_id': chat_id,
            'caption': caption or ''
        }

        tencent_logger.info(f"[+] 发送Telegram图片到 chat_id={chat_id}")

        response = requests.post(url, files=files, data=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                tencent_logger.success("[+] Telegram图片已发送")
                return True
            else:
                tencent_logger.error(f"[+] Telegram API返回错误: {result}")
                return False
        else:
            tencent_logger.error(f"[+] Telegram发送失败: HTTP {response.status_code}")
            return False

    except Exception as e:
        tencent_logger.error(f"[+] 发送Telegram图片异常: {e}")
        return False


def send_bark_notification(title, body):
    """发送Bark通知的辅助函数（备用）

    Args:
        title: 通知标题
        body: 通知内容

    Returns:
        bool: 是否发送成功
    """
    try:
        from urllib.parse import quote

        # 从config.json获取Bark URL
        bark_url = get_bark_url()
        if not bark_url:
            tencent_logger.warning("[+] 未配置Bark URL")
            return False

        # Bark的正确格式: https://api.day.app/YOUR_KEY/TITLE/BODY
        # title和body需要分别进行URL编码
        encoded_title = quote(title)
        encoded_body = quote(body, safe='')  # safe='' 表示编码所有特殊字符

        # 构建Bark URL
        url = f"{bark_url}/{encoded_title}/{encoded_body}"

        tencent_logger.info(f"[+] Bark URL: {url}")

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            tencent_logger.success("[+] Bark通知已发送")
            return True
        else:
            tencent_logger.warning(f"[+] Bark通知发送失败: HTTP {response.status_code}")
            tencent_logger.info(f"[+] 响应内容: {response.text}")
            return False

    except Exception as e:
        tencent_logger.error(f"[+] 发送Bark通知异常: {e}")
        return False


async def cookie_auth_douyin(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.douyin.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.douyin.com/creator-micro/content/upload", timeout=5000)
            # 2024.06.17 抖音创作者中心改版
            # 判断
            # 等待“扫码登录”元素出现，超时 5 秒（如果 5 秒没出现，说明 cookie 有效）
            try:
                await page.get_by_text("扫码登录").wait_for(timeout=5000)
                douyin_logger.error("[+] cookie 失效，需要扫码登录")
                return False
            except:
                douyin_logger.success("[+]  cookie 有效")
                return True
        except:
            douyin_logger.error("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False


async def cookie_auth_tencent(account_file):
    """验证视频号cookie是否有效

    改进的验证逻辑：
    1. 访问创作页面
    2. 检查是否被重定向到登录页
    3. 检查是否出现登录相关元素
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        page = await context.new_page()

        # 访问创作页面
        await page.goto("https://channels.weixin.qq.com/platform/post/create")

        try:
            # 等待页面加载
            await page.wait_for_load_state("networkidle", timeout=10000)

            # 检查是否被重定向到登录页
            current_url = page.url
            if "login" in current_url or "channels.weixin.qq.com" not in current_url:
                tencent_logger.warning(f"[+] 被重定向到登录页: {current_url}")
                await context.close()
                await browser.close()
                return False

            # 检查是否出现登录相关元素（二维码登录框等）
            login_indicators = [
                'div.qrcode-wrap',  # 二维码容器
                'img.qrcode',  # 二维码图片
                'div.login-container',  # 登录容器
                'text=扫码登录',  # 扫码登录文本
            ]

            for selector in login_indicators:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0 and await element.is_visible():
                        tencent_logger.warning(f"[+] 检测到登录元素: {selector}")
                        await context.close()
                        await browser.close()
                        return False
                except:
                    continue

            # 检查是否能看到正常的创作页面元素
            try:
                # 尝试查找创作页面的标志性元素
                create_page_elements = [
                    'div.input-editor',  # 标题输入框
                    'input[type="file"]',  # 文件上传
                    'div.form-btns',  # 按钮区域
                ]

                has_create_element = False
                for selector in create_page_elements:
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0:
                            has_create_element = True
                            break
                    except:
                        continue

                if has_create_element:
                    tencent_logger.success("[+] cookie 有效，已进入创作页面")
                    await context.close()
                    await browser.close()
                    return True
                else:
                    tencent_logger.warning("[+] 未找到创作页面元素，cookie可能失效")
                    await context.close()
                    await browser.close()
                    return False

            except Exception as e:
                tencent_logger.error(f"[+] 验证过程出错: {e}")
                await context.close()
                await browser.close()
                return False

        except Exception as e:
            tencent_logger.error(f"[+] cookie验证异常: {e}")
            await context.close()
            await browser.close()
            return False


async def extract_and_send_qrcode(page, account_name="视频号"):
    """提取二维码并通过Telegram Bot发送图片

    Args:
        page: Playwright页面对象
        account_name: 账号名称，用于通知标题

    Returns:
        str: 二维码图片的保存路径，如果失败返回None
    """
    try:
        tencent_logger.info("[+] 等待二维码加载...")

        # 等待登录页面加载完成
        try:
            # 等待URL包含login或等待登录相关元素
            await page.wait_for_selector('iframe, img.qrcode, .qrcode, div.qrcode-wrap', timeout=15000)
            await asyncio.sleep(2)  # 额外等待2秒确保二维码完全加载
        except:
            tencent_logger.warning("[+] 等待登录元素超时，继续尝试提取二维码...")

        # 等待iframe出现
        try:
            iframe_count = await page.locator('iframe').count()
            tencent_logger.info(f"[+] 找到 {iframe_count} 个iframe")
        except:
            iframe_count = 0
            tencent_logger.info("[+] 没有找到iframe")

        # 遍历所有iframe，查找二维码
        src = None
        for i in range(iframe_count):
            try:
                iframe = page.frame_locator(f'iframe').nth(i)
                tencent_logger.info(f"[+] 正在检查 iframe[{i}]...")

                # 在iframe中查找二维码
                qrcode_selectors = [
                    'img.qrcode',
                    'img[src*="data:image"]',
                    '.qrcode'
                ]

                for selector in qrcode_selectors:
                    try:
                        iframe_img = iframe.locator(selector).first
                        if await iframe_img.count() > 0:
                            src = await iframe_img.get_attribute('src')
                            if src and src.startswith('data:image'):
                                tencent_logger.success(f"[+] 从iframe[{i}]找到二维码: {selector}")
                                break
                    except:
                        continue

                if src:
                    break

            except Exception as e:
                tencent_logger.debug(f"[+] iframe[{i}] 查找失败: {e}")
                continue

        # 如果在iframe中没找到二维码，尝试在主页面中查找
        if not src:
            tencent_logger.info("[+] iframe中未找到二维码，正在检查主页面...")
            main_page_selectors = [
                'img.qrcode',
                'img[src*="data:image"]',
                '.qrcode img',
                'img[src*="qrcode"]',
                'div.qrcode-wrap img',
                'img[alt*="二维码"]',
                'img[alt*="扫码"]'
            ]

            for selector in main_page_selectors:
                try:
                    main_img = page.locator(selector).first
                    if await main_img.count() > 0:
                        src = await main_img.get_attribute('src')
                        if src and (src.startswith('data:image') or 'qrcode' in src.lower()):
                            tencent_logger.success(f"[+] 从主页面找到二维码: {selector}")
                            break
                except:
                    continue

        # 如果没找到二维码
        if not src:
            tencent_logger.error("[+] 无法从iframe中找到二维码")
            tencent_logger.info("[+] 正在截图保存到 debug_qrcode.png，请检查...")
            await page.screenshot(path="debug_qrcode.png")
            return None

        # 解码并保存二维码
        try:
            # 解析base64数据
            if ',' in src:
                base64_data = src.split(',')[1]
            else:
                base64_data = src

            # 解码base64
            image_data = base64.b64decode(base64_data)

            # 保存二维码图片
            temp_dir = Path(BASE_DIR / "data" / "temp_qrcodes")
            temp_dir.mkdir(parents=True, exist_ok=True)

            import time
            timestamp = int(time.time())
            qrcode_path = temp_dir / f"tencent_qrcode_{timestamp}.png"

            with open(qrcode_path, 'wb') as f:
                f.write(image_data)

            tencent_logger.success(f"[+] 二维码已保存到: {qrcode_path}")

            # 发送Telegram图片
            caption = f"{account_name}需要重新登录\n\n请使用手机微信扫码登录"
            send_telegram_photo(str(qrcode_path), caption)

            # 发送Bark通知
            title = f"{account_name}需要重新登录"
            body = f"请使用手机微信扫码登录\n\n二维码已保存到: {qrcode_path}"
            send_bark_notification(title, body)

            return str(qrcode_path)

        except Exception as e:
            tencent_logger.error(f"[+] 解码或保存二维码失败: {e}")
            return None

    except Exception as e:
        tencent_logger.error(f"[+] 提取二维码失败: {e}")
        import traceback
        tencent_logger.error(traceback.format_exc())
        return None


async def cookie_auth_ks(account_file):
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


async def cookie_auth_xhs(account_file):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=LOCAL_CHROME_HEADLESS)
        context = await browser.new_context(storage_state=account_file)
        context = await set_init_script(context)
        # 创建一个新的页面
        page = await context.new_page()
        # 访问指定的 URL
        await page.goto("https://creator.xiaohongshu.com/creator-micro/content/upload")
        try:
            await page.wait_for_url("https://creator.xiaohongshu.com/creator-micro/content/upload", timeout=5000)
        except:
            print("[+] 等待5秒 cookie 失效")
            await context.close()
            await browser.close()
            return False
        # 2024.06.17 抖音创作者中心改版
        if await page.get_by_text('手机号登录').count() or await page.get_by_text('扫码登录').count():
            print("[+] 等待5秒 cookie 失效")
            return False
        else:
            print("[+] cookie 有效")
            return True


async def check_cookie(type, file_path):
    # 小红书
    if type == 1:
        return await cookie_auth_xhs(Path(BASE_DIR / "cookiesFile" / file_path))
    # 视频号
    elif type == 2:
        return await cookie_auth_tencent(Path(BASE_DIR / "cookiesFile" / file_path))
    # 抖音
    elif type == 3:
        return await cookie_auth_douyin(Path(BASE_DIR / "cookiesFile" / file_path))
    # 快手
    elif type == 4:
        return await cookie_auth_ks(Path(BASE_DIR / "cookiesFile" / file_path))
    else:
        return False

# a = asyncio.run(check_cookie(1,"3a6cfdc0-3d51-11f0-8507-44e51723d63c.json"))
# print(a)
