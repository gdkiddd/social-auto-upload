import json
import pathlib
import random
from biliup.plugins.bili_webup import BiliBili, Data

from utils.log import bilibili_logger


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
        with BiliBili(self.data) as bili:
            bili.login_by_cookies(self.cookie_data)
            bili.access_token = self.cookie_data.get('access_token')
            video_part = bili.upload_file(str(self.file), lines=self.lines,
                                          tasks=self.upload_thread_num)  # 上传视频，默认线路AUTO自动选择，线程数量3。
            video_part['title'] = self.title
            self.data.append(video_part)
            ret = bili.submit()  # 提交视频
            if ret.get('code') == 0:
                bilibili_logger.success(f'[+] {self.file.name}上传 成功')
                return True
            else:
                bilibili_logger.error(f'[-] {self.file.name}上传 失败, error messge: {ret.get("message")}')
                return False
