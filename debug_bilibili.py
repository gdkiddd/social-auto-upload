# -*- coding: utf-8 -*-
"""
Bilibili 上传调试脚本
检查 cookie、配置和连接状态
"""

import json
import pathlib
from pathlib import Path
from myUtils.account_manager import get_current_account, get_account_cookie_path
from myUtils.video_project import get_video_project_dir, get_video_files_from_project
from uploader.bilibili_uploader.main import read_cookie_json_file, extract_keys_from_json

def check_bilibili_status():
    """检查 Bilibili 状态"""
    print("=" * 60)
    print("🔍 Bilibili 上传调试")
    print("=" * 60)
    print()

    # 1. 检查当前账号
    current_account = get_current_account()
    print(f"📌 当前账号: {current_account}")
    print()

    # 2. 检查 cookie 文件
    account_file = get_account_cookie_path(current_account, 'bilibili')
    print(f"📁 Cookie 文件路径: {account_file}")
    print()

    if not account_file.exists():
        print("❌ Cookie 文件不存在！")
        print("💡 请先运行登录: python examples/get_bilibili_cookie_simple.py")
        return False

    print("✅ Cookie 文件存在")
    print()

    # 3. 读取并检查 cookie 内容
    try:
        print("📖 读取 Cookie 文件...")
        with open(account_file, 'r', encoding='utf-8') as f:
            cookie_json = json.load(f)

        print(f"   文件大小: {len(json.dumps(cookie_json))} 字节")
        print()

        # 4. 提取关键数据
        print("🔑 提取关键 Cookie 数据...")
        extracted = extract_keys_from_json(cookie_json)

        required_keys = {
            'SESSDATA': '会话令牌',
            'bili_jct': 'CSRF 令牌',
            'DedeUserID': '用户 ID',
            'DedeUserID__ckMd5': '用户 ID 校验'
        }

        all_ok = True
        for key, desc in required_keys.items():
            value = extracted.get(key)
            if value:
                # 只显示前后几位，保护隐私
                display_value = value[:8] + '...' if len(value) > 8 else value
                print(f"   ✅ {key} ({desc}): {display_value}")
            else:
                print(f"   ❌ {key} ({desc}): 缺失！")
                all_ok = False

        print()

        # 5. 检查 access_token
        if extracted.get('access_token'):
            print("   ✅ access_token: 存在")
        else:
            print("   ⚠️  access_token: 不存在（某些操作可能需要）")

        print()

        if not all_ok:
            print("=" * 60)
            print("❌ Cookie 数据不完整！")
            print("=" * 60)
            print()
            print("💡 解决方法：")
            print("   1. 重新登录 Bilibili")
            print("   2. 运行: python examples/get_bilibili_cookie_simple.py")
            print("   3. 确保浏览器登录成功后点击 Inspector 的 '继续' 按钮")
            print()
            return False

        # 6. 检查配置文件
        print("⚙️  检查配置文件...")
        from conf import load_config
        config = load_config()

        bilibili_tid = config.get('bilibili_tid')
        if bilibili_tid:
            print(f"   ✅ bilibili_tid: {bilibili_tid}")
        else:
            print(f"   ⚠️  bilibili_tid: 未设置（将使用默认值）")

        bilibili_schedule = config.get('bilibili_schedule')
        if bilibili_schedule:
            print(f"   ✅ bilibili_schedule: {bilibili_schedule}")
        else:
            print(f"   ℹ️  bilibili_schedule: 未设置（默认立即发布）")

        print()

        # 7. 检查视频文件
        print("📹 检查视频文件...")
        project_dir = get_video_project_dir()
        if project_dir:
            print(f"   ✅ 找到视频项目目录: {project_dir.name}")
            video_files = get_video_files_from_project(project_dir)
            if video_files:
                print(f"   ✅ 找到 {len(video_files)} 个视频文件")
                for video in video_files[:3]:  # 只显示前3个
                    size_mb = video.stat().st_size / (1024*1024)
                    print(f"      - {video.name} ({size_mb:.1f} MB)")
                if len(video_files) > 3:
                    print(f"      ... 还有 {len(video_files) - 3} 个文件")
            else:
                print("   ⚠️  项目目录下没有 .mp4 文件")
        else:
            print("   ⚠️  videos/ 目录下没有找到视频项目")
            print("   💡 请在 videos/ 目录下创建一个文件夹（如 '项目1'），放入视频文件")

        print()

        # 8. 总结
        print("=" * 60)
        print("✅ 检查完成！Cookie 和配置看起来正常")
        print("=" * 60)
        print()
        print("💡 如果仍然上传失败，可能的原因：")
        print("   1. Cookie 已过期（重新登录可解决）")
        print("   2. 网络连接问题")
        print("   3. Bilibili API 限流")
        print("   4. 视频文件格式或大小问题")
        print()
        print("🔗 查看详细错误信息:")
        print("   运行上传脚本并查看控制台输出")
        print()
        return True

    except Exception as e:
        print(f"❌ 读取 Cookie 文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    check_bilibili_status()
