#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilibili 登录获取 Cookie - macOS 版本
使用扫码方式登录，自动保存 cookie 文件
"""

import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from biliup.plugins.bili_webup import BiliBili, Data
from utils.log import bilibili_logger


def bilibili_qrcode_login(account_file):
    """
    使用二维码方式登录 Bilibili
    """
    bilibili_logger.info('[+] 正在启动 Bilibili 二维码登录...')

    # 初始化数据
    data = Data()

    with BiliBili(data) as bili:
        try:
            # 获取二维码
            qrcode_data = bili.get_qrcode()

            if qrcode_data.get('code') == 0:
                # 打印二维码 URL（可以复制到浏览器打开，或使用终端二维码显示工具）
                qrcode_url = qrcode_data['data']['url']
                bilibili_logger.info(f'[+] 请使用手机 Bilibili APP 扫描二维码登录')
                bilibili_logger.info(f'[+] 二维码链接: {qrcode_url}')

                # 如果系统有 qrcode 终端工具，可以显示二维码
                try:
                    import qrcode_terminal
                    bilibili_logger.info('[+] 正在显示二维码...')
                    qrcode_terminal.main(qrcode_url)
                    bilibili_logger.info('[+] 如果二维码无法显示，请访问上面的链接')
                except ImportError:
                    bilibili_logger.info('[+] 提示: pip install qrcode-terminal 可以在终端显示二维码')
                    bilibili_logger.info('[+] 或直接复制上面的链接到浏览器打开')

                # 等待扫码登录
                bilibili_logger.info('[+] 等待扫码登录...')

                # 使用二维码登录
                result = bili.login_by_qrcode(qrcode_data['data']['qrcode_key'],
                                            qrcode_data['data']['oauth_key'])

                if result:
                    bilibili_logger.success('[+] 登录成功!')

                    # 保存 cookie 信息
                    cookie_info = {
                        'cookie_info': {
                            'cookies': [
                                {'name': 'SESSDATA', 'value': bili.cookies['SESSDATA']},
                                {'name': 'bili_jct', 'value': bili.cookies['bili_jct']},
                                {'name': 'DedeUserID__ckMd5', 'value': bili.cookies['DedeUserID__ckMd5']},
                                {'name': 'DedeUserID', 'value': bili.cookies['DedeUserID']},
                            ]
                        },
                        'token_info': {}
                    }

                    # 如果有 access_token 也保存
                    if hasattr(bili, 'access_token') and bili.access_token:
                        cookie_info['token_info']['access_token'] = bili.access_token

                    # 保存到文件
                    account_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(account_file, 'w', encoding='utf-8') as f:
                        json.dump(cookie_info, f, indent=2, ensure_ascii=False)

                    bilibili_logger.success(f'[+] Cookie 已保存到: {account_file}')
                    return True
                else:
                    bilibili_logger.error('[-] 登录失败，请重试')
                    return False

            else:
                bilibili_logger.error(f'[-] 获取二维码失败: {qrcode_data.get("message")}')
                return False

        except Exception as e:
            bilibili_logger.error(f'[-] 登录过程出错: {str(e)}')
            return False


if __name__ == '__main__':
    # Cookie 保存路径
    account_file = Path(__file__).parent.parent / "cookies" / "bilibili_uploader" / "account.json"

    print(f'Bilibili 登录 - macOS 版本')
    print(f'Cookie 保存路径: {account_file}')
    print('=' * 60)

    # 执行登录
    success = bilibili_qrcode_login(account_file)

    if success:
        print('\n✅ 登录成功！现在可以上传视频了')
        print(f'运行上传命令: python examples/upload_video_to_bilibili.py')
    else:
        print('\n❌ 登录失败，请重试')
        sys.exit(1)
