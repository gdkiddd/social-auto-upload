import json
import pathlib
import random
from biliup.plugins.bili_webup import BiliBili, Data

from utils.log import bilibili_logger
from myUtils.publish_history import get_publish_history
from myUtils.account_manager import get_current_account


def extract_keys_from_json(data):
    """Extract specified keys from the provided JSON data.
    支持两种格式：
    1. biliup 格式：{"cookie_info": {"cookies": [...]}, "token_info": {}}
    2. Playwright storage_state 格式：{"cookies": [...], "origins": [...]}
    """
    keys_to_extract = ["SESSDATA", "bili_jct", "DedeUserID__ckMd5", "DedeUserID", "access_token"]
    extracted_data = {}

    # 检测格式并提取 cookies
    if 'cookie_info' in data and 'cookies' in data['cookie_info']:
        # biliup 格式
        cookies_list = data['cookie_info']['cookies']
    elif 'cookies' in data:
        # Playwright storage_state 格式
        cookies_list = data['cookies']
    else:
        raise ValueError("无法识别的 cookie 文件格式")

    # Extracting cookie data
    for cookie in cookies_list:
        if cookie['name'] in keys_to_extract:
            extracted_data[cookie['name']] = cookie['value']

    # Extracting access_token (biliup 格式)
    if "token_info" in data and "access_token" in data['token_info']:
        extracted_data['access_token'] = data['token_info']['access_token']

    return extracted_data


def read_cookie_json_file(filepath: pathlib.Path):
    with open(filepath, 'r', encoding='utf-8') as file:
        content = json.load(file)
        return content


def random_emoji():
    emoji_list = ["🍏", "🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍈", "🍒", "🍑", "🍍", "🥭", "🥥", "🥝",
                  "🍅", "🍆", "🥑", "🥦", "🥒", "🥬", "🌶", "🌽", "🥕", "🥔", "🍠", "🥐", "🍞", "🥖", "🥨", "🥯", "🧀", "🥚", "🍳", "🥞",
                  "🥓", "🥩", "🍗", "🍖", "🌭", "🍔", "🍟", "🍕", "🥪", "🥙", "🌮", "🌯", "🥗", "🥘", "🥫", "🍝", "🍜", "🍲", "🍛", "🍣",
                  "🍱", "🥟", "🍤", "🍙", "🍚", "🍘", "🍥", "🥮", "🥠", "🍢", "🍡", "🍧", "🍨", "🍦", "🥧", "🍰", "🎂", "🍮", "🍭", "🍬",
                  "🍫", "🍿", "🧂", "🍩", "🍪", "🌰", "🥜", "🍯", "🥛", "🍼", "☕️", "🍵", "🥤", "🍶", "🍻", "🥂", "🍷", "🥃", "🍸", "🍹",
                  "🍾", "🥄", "🍴", "🍽", "🥣", "🥡", "🥢"]
    return random.choice(emoji_list)


class BilibiliUploader(object):
    def __init__(self, cookie_data, file: pathlib.Path, title, desc, tid, tags, dtime):
        self.upload_thread_num = 3
        self.copyright = 1
        self.lines = 'AUTO'
        self.cookie_data = cookie_data
        self.file = file
        self.title = title
        self.desc = desc
        self.tid = tid
        self.tags = tags
        self.dtime = dtime
        self._init_data()

    def _init_data(self):
        self.data = Data()
        self.data.copyright = self.copyright
        self.data.title = self.title
        self.data.desc = self.desc
        self.data.tid = self.tid
        self.data.set_tag(self.tags)
        self.data.dtime = self.dtime

    def upload(self):
        bilibili_logger.info(f'📹 正在上传: {self.file.name}')
        bilibili_logger.info(f'   文件大小: {self.file.stat().st_size / (1024*1024):.1f} MB')
        bilibili_logger.info(f'   标题: {self.title}')
        bilibili_logger.info(f'   标签: {", ".join(self.tags) if self.tags else "无"}')
        bilibili_logger.info(f'   分区: tid={self.tid}')
        bilibili_logger.info(f'   正在上传视频文件...')

        try:
            # 准备新版 biliup 需要的 cookie 格式
            # 从提取的数据中构建 cookie_info 格式
            cookies_list = []
            for name, value in self.cookie_data.items():
                if name in ['SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5']:
                    cookies_list.append({'name': name, 'value': value})

            cookie_data_for_biliup = {
                'cookie_info': {
                    'cookies': cookies_list
                }
            }

            # 如果有 access_token，添加到 token_info
            if self.cookie_data.get('access_token'):
                cookie_data_for_biliup['token_info'] = {
                    'access_token': self.cookie_data['access_token']
                }

            bilibili_logger.info(f'   Cookie 数据准备完成')

            with BiliBili(self.data) as bili:
                # 验证 cookie 数据
                if not self.cookie_data.get('SESSDATA'):
                    bilibili_logger.error('❌ 缺少必要的 cookie: SESSDATA')
                    return False
                if not self.cookie_data.get('bili_jct'):
                    bilibili_logger.error('❌ 缺少必要的 cookie: bili_jct')
                    return False

                bili.login_by_cookies(cookie_data_for_biliup)
                bili.access_token = self.cookie_data.get('access_token')

                # 上传视频
                bilibili_logger.info(f'   开始上传视频文件...')

                # 添加对 preupload API 错误的检测
                import biliup.plugins.bili_webup

                # 保存原始方法
                from requests import Session
                original_get = Session.get

                api_error = None  # 用于存储 API 错误信息

                def debug_get_wrapper(self, url, **kwargs):
                    nonlocal api_error
                    resp = original_get(self, url, **kwargs)
                    if 'preupload' in url:
                        try:
                            ret = resp.json()
                            if ret.get('OK') == 0:
                                # API 返回错误
                                error_msg = ret.get('message', ret.get('info', '未知错误'))
                                error_code = ret.get('code', 'N/A')
                                api_error = f"Bilibili API 错误 (code: {error_code}): {error_msg}"
                                bilibili_logger.error(f'❌ {api_error}')
                                # 特殊处理频率限制错误
                                if error_code == 601:
                                    bilibili_logger.error(f'💡 上传频率限制：请等待 15-30 分钟后再试')
                                    bilibili_logger.error(f'💡 建议：手动上传到 Bilibili，或者稍后使用本工具重试')
                        except:
                            pass  # 如果解析失败，继续正常流程
                    return resp

                # 临时替换 Session.get 方法
                Session.get = debug_get_wrapper

                try:
                    video_part = bili.upload_file(str(self.file), lines=self.lines,
                                                  tasks=self.upload_thread_num)
                    bilibili_logger.success(f'   ✅ 视频文件上传完成')

                    # 检查是否有 API 错误
                    if api_error:
                        raise Exception(api_error)

                except KeyError as e:
                    if 'chunk_size' in str(e):
                        bilibili_logger.error(f'❌ Bilibili API 返回错误（可能原因：上传频率限制、Cookie 过期等）')
                        if api_error:
                            bilibili_logger.error(f'   详细信息: {api_error}')
                        raise Exception(f"Bilibili 上传失败: {api_error or 'API 返回数据格式错误'}")
                    else:
                        raise
                except Exception as e:
                    if 'chunk_size' in str(e) or 'Bilibili API 错误' in str(e):
                        bilibili_logger.error(f'❌ Bilibili API 返回错误')
                        if api_error:
                            bilibili_logger.error(f'   详细信息: {api_error}')
                        raise Exception(f"Bilibili 上传失败: {api_error or str(e)}")
                    else:
                        raise
                finally:
                    # 恢复原方法
                    Session.get = original_get

                video_part['title'] = self.title
                self.data.append(video_part)

                bilibili_logger.info(f'   正在提交视频...')
                ret = bili.submit()  # 提交视频

                bilibili_logger.info(f'   返回结果: {ret}')

                # 检查返回值
                if ret is None:
                    bilibili_logger.error(f'❌ {self.file.name} 提交失败：无返回值')
                    return False

                code = ret.get('code')
                if code is None:
                    bilibili_logger.error(f'❌ {self.file.name} 提交失败：返回值中没有 code')
                    bilibili_logger.error(f'   完整返回: {ret}')
                    return False

                if code == 0:
                    bilibili_logger.success(f'✅ {self.file.name} 上传成功')
                    bilibili_logger.info(f'🔗 查看上传结果: https://member.bilibili.com/platform/upload-manager/article')
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
                    bilibili_logger.error(f'❌ {self.file.name} 上传失败')
                    bilibili_logger.error(f'   错误码: {code}')
                    bilibili_logger.error(f'   错误信息: {ret.get("message")}')
                    bilibili_logger.error(f'   完整返回: {ret}')
                    return False

        except Exception as e:
            bilibili_logger.error(f'❌ {self.file.name} 上传异常')
            bilibili_logger.error(f'   异常信息: {str(e)}')
            import traceback
            bilibili_logger.error(f'   详细错误:\n{traceback.format_exc()}')
            return False
