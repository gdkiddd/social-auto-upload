#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Cookie 保存工具
用于将手动获取的 cookie 保存为 JSON 文件
"""

import json
from pathlib import Path

from myUtils.account_manager import get_current_account, get_account_cookie_path


def save_cookie_from_clipboard():
    """从剪贴板或输入读取 cookie 并保存"""
    current_account = get_current_account()
    account_file = get_account_cookie_path(current_account, 'youtube')

    print("=" * 60)
    print("YouTube Cookie 保存工具")
    print("=" * 60)
    print()
    print(f"📋 当前账号: {current_account}")
    print(f"📁 Cookie 文件: {account_file}")
    print()
    print("请按以下步骤操作：")
    print()
    print("1. 在 Chrome 浏览器中打开 YouTube Studio 并登录")
    print("   https://studio.youtube.com")
    print()
    print("2. 登录成功后，按 F12 打开开发者工具")
    print()
    print("3. 切换到 'Application' 标签页")
    print()
    print("4. 在左侧找到 'Cookies' → 'https://studio.youtube.com'")
    print()
    print("5. 复制以下重要的 cookie 值：")
    print("   - __Secure-3PSID")
    print("   - __Secure-3PSIDCC")
    print("   - SID")
    print("   - HSID")
    print("   - SSID")
    print("   - SAPISID")
    print("   - APISID")
    print("   - LOGIN_INFO")
    print("   - VISITOR_INFO1_LIVE")
    print("   - YSC")
    print("   - PREF")
    print("   - CONSENT")
    print()
    print("=" * 60)
    print("请按照以下格式输入 cookie（一行一个，格式：名称=值）：")
    print("输入完成后输入 'SAVE' 开始保存")
    print("输入 'QUIT' 或按 Ctrl+C 退出")
    print("=" * 60)
    print()

    cookies = []
    while True:
        try:
            line = input().strip()

            if not line:
                continue

            if line.upper() == 'QUIT':
                print("❌ 已取消操作")
                return False

            if line.upper() == 'SAVE':
                if len(cookies) == 0:
                    print("❌ 没有输入任何 cookie，请至少输入一个有效的 cookie")
                    continue
                break

            # 解析 cookie (格式: name=value)
            if '=' in line:
                name, value = line.split('=', 1)
                name = name.strip()
                value = value.strip()

                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.youtube.com',
                    'path': '/',
                    'expires': -1,
                    'httpOnly': True,
                    'secure': True
                })

                print(f"✅ 已添加: {name}")
            else:
                print("❌ 格式错误，请使用格式: 名称=值")

        except KeyboardInterrupt:
            print()
            print("❌ 已取消操作")
            return False
        except Exception as e:
            print(f"❌ 解析错误: {e}")
            continue

    # 保存 cookie 到 JSON 文件
    try:
        cookie_data = {
            'cookies': cookies,
            'origins': [
                {
                    'origin': 'https://studio.youtube.com',
                    'localStorage': [],
                    'sessionStorage': []
                },
                {
                    'origin': 'https://www.youtube.com',
                    'localStorage': [],
                    'sessionStorage': []
                }
            ]
        }

        # 确保目录存在
        account_file.parent.mkdir(parents=True, exist_ok=True)

        # 写入 JSON 文件
        with open(account_file, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, indent=2, ensure_ascii=False)

        print()
        print("=" * 60)
        print(f"✅ Cookie 已成功保存到: {account_file}")
        print(f"📊 共保存 {len(cookies)} 个 cookie")
        print("=" * 60)
        print()
        print("💡 提示：现在可以使用 'python examples/upload_video_to_youtube.py' 上传视频了")
        print()

        return True

    except Exception as e:
        print()
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    try:
        success = save_cookie_from_clipboard()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
