#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键运行所有平台的上传脚本 - 增强版
支持菜单选择、窗口监控、定时设置
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 切换到脚本所在目录
SCRIPT_DIR = Path(__file__).parent.resolve()
os.chdir(SCRIPT_DIR)

# 现在导入模块（需要先切换目录）
from conf import load_config, save_config, is_platform_enabled
from myUtils.account_manager import (
    get_accounts, add_account, delete_account,
    get_current_account, set_current_account,
    get_account_cookie_path, check_account_cookie_exists,
    ensure_default_account, migrate_old_cookies
)

# 确保默认账号存在
ensure_default_account()


# 平台配置（按顺序）
PLATFORMS = [
    {
        'id': 'xiaohongshu',
        'name': '小红书',
        'cookie_file': 'cookies/xiaohongshu_uploader/account.json',
        'script': 'examples/upload_video_to_xiaohongshu.py',
        'login_script': 'examples/get_xiaohongshu_cookie.py',
        'has_browser': True
    },
    {
        'id': 'tencent',
        'name': '视频号',
        'cookie_file': 'cookies/tencent_uploader/account.json',
        'script': 'examples/upload_video_to_tencent.py',
        'login_script': 'examples/get_tencent_cookie.py',
        'has_browser': True
    },
    {
        'id': 'bilibili',
        'name': 'Bilibili',
        'cookie_file': 'cookies/bilibili_uploader/account.json',
        'script': 'examples/upload_video_to_bilibili.py',
        'login_script': None,
        'has_browser': False
    },
    {
        'id': 'douyin',
        'name': '抖音',
        'cookie_file': 'cookies/douyin_uploader/account.json',
        'script': 'examples/upload_video_to_douyin.py',
        'login_script': 'examples/get_douyin_cookie.py',
        'has_browser': True
    },
    {
        'id': 'kuaishou',
        'name': '快手',
        'cookie_file': 'cookies/ks_uploader/account.json',
        'script': 'examples/upload_video_to_kuaishou.py',
        'login_script': 'examples/get_kuaishou_cookie.py',
        'has_browser': True
    },
    {
        'id': 'baijiahao',
        'name': '百家号',
        'cookie_file': 'cookies/baijiahao_uploader/account.json',
        'script': 'examples/upload_video_to_baijiahao.py',
        'login_script': 'examples/get_baijiahao_cookie.py',
        'has_browser': True
    }
]


def check_cookie_exists(cookie_file_or_platform_id):
    """
    检查 cookie 文件是否存在

    Args:
        cookie_file_or_platform_id: cookie文件路径 或 平台ID
    """
    # 如果传入的是平台ID，使用当前账号的cookie路径
    if isinstance(cookie_file_or_platform_id, str) and not cookie_file_or_platform_id.endswith('.json'):
        platform_id = cookie_file_or_platform_id
        current_account = get_current_account()
        return check_account_cookie_exists(current_account, platform_id)

    # 兼容旧的路径方式
    if not Path(cookie_file_or_platform_id).is_absolute():
        cookie_path = SCRIPT_DIR / cookie_file_or_platform_id
    else:
        cookie_path = Path(cookie_file_or_platform_id)
    return cookie_path.exists()


def rename_video_files():
    """重命名 txt 和 png 文件，使其与对应的 mp4 文件同名"""
    videos_dir = Path("videos")
    if not videos_dir.exists():
        return

    video_files = list(videos_dir.glob("*.mp4"))
    if len(video_files) == 0:
        return
    elif len(video_files) == 1:
        # 只有一个视频，把所有 txt 和 png 重命名为该视频的名字
        video_name = video_files[0].stem
        renamed_count = 0

        for ext in ['*.txt', '*.png', '*.PNG']:
            matching_files = list(videos_dir.glob(ext))

            for file in matching_files:
                # 如果文件不是对应的同名文件
                if file.stem != video_name:
                    new_name = videos_dir / f"{video_name}{file.suffix}"
                    try:
                        file.rename(new_name)
                        renamed_count += 1
                        print(f"  📝 {file.name} → {new_name.name}")
                    except Exception as e:
                        print(f"  ⚠️  重命名 {file.name} 失败: {e}")

        if renamed_count > 0:
            print(f"✅ 已重命名 {renamed_count} 个文件")
            print()
    else:
        # 多个视频，只重命名已匹配的文件（同名的）
        for video_file in video_files:
            video_name = video_file.stem
            renamed_count = 0

            # 查找可能匹配的文件（相同基础名称但不同扩展名）
            possible_files = [
                videos_dir / f"{video_name}.txt",
                videos_dir / f"{video_name}.png",
                videos_dir / f"{video_name}.PNG"
            ]

            for file in possible_files:
                if file.exists():
                    # 文件已匹配，无需重命名
                    pass

        # 不输出任何信息，因为多视频情况下需要手动管理文件名
        pass


def show_video_info():
    """显示即将上传的视频信息"""
    print("\n" + "=" * 60)
    print("📹 即将上传的视频")
    print("=" * 60)

    videos_dir = Path("videos")
    if not videos_dir.exists():
        print("⚠️  videos/ 目录不存在")
        print()
        return

    video_files = sorted(list(videos_dir.glob("*.mp4")))
    if not video_files:
        print("⚠️  videos/ 目录下没有视频文件")
        print()
        return

    print(f"✅ 找到 {len(video_files)} 个视频文件")
    print()

    for i, video_file in enumerate(video_files, 1):
        file_size = video_file.stat().st_size / (1024 * 1024)  # MB
        txt_file = video_file.with_suffix('.txt')

        print(f"  [{i}] {video_file.name} ({file_size:.1f} MB)")

        # 读取并显示 txt 文件内容
        if txt_file.exists():
            with open(txt_file, 'r', encoding='utf-8') as f:
                lines = f.read().strip().split('\n')

            if lines:
                print(f"      标题: {lines[0].strip()}")
                if len(lines) >= 2:
                    print(f"      标签: {lines[1].strip()}")
                if len(lines) >= 3:
                    desc_preview = lines[2].strip()[:50]
                    if len(lines[2].strip()) > 50:
                        desc_preview += "..."
                    print(f"      描述: {desc_preview}")
        else:
            print(f"      ⚠️  未找到对应的 txt 文件")
        print()

    print("=" * 60)


def show_account_menu():
    """显示账号选择菜单"""
    while True:
        print("\n" + "=" * 60)
        print("👤 账号选择")
        print("=" * 60)

        current_account = get_current_account()
        accounts = get_accounts()

        print(f"当前账号: {current_account}")
        print()

        # 显示账号列表
        if accounts:
            for i, account in enumerate(accounts, 1):
                current_mark = " ✅ (当前)" if account == current_account else ""
                print(f"  [{i}] {account}{current_mark}")

        # 操作选项
        start_idx = len(accounts) + 1
        add_idx = start_idx
        delete_idx = start_idx + 1
        continue_idx = start_idx + 2
        migrate_idx = start_idx + 3

        print()
        print(f"  [{add_idx}] 添加新账号")
        if len(accounts) > 1:
            print(f"  [{delete_idx}] 删除账号")
        print(f"  [{migrate_idx}] 迁移旧Cookie")
        print()
        print(f"  [{continue_idx}] 继续")
        print("  [0] 退出")
        print("=" * 60)

        choice = input("\n请输入选项: ").strip()

        if choice == '0':
            print("\n👋 再见！")
            sys.exit(0)

        elif choice == str(continue_idx):
            # 继续到平台选择
            break

        elif choice == str(add_idx):
            # 添加新账号
            print("\n" + "-" * 40)
            account_name = input("请输入新账号名称: ").strip()
            if account_name:
                add_account(account_name)
            else:
                print("❌ 账号名称不能为空")

        elif choice == str(delete_idx) and len(accounts) > 1:
            # 删除账号
            print("\n" + "-" * 40)
            print(f"已有账号: {', '.join(accounts)}")
            account_name = input("请输入要删除的账号名称: ").strip()

            if account_name in accounts:
                if account_name == current_account:
                    print(f"⚠️  不能删除当前账号")
                else:
                    confirm = input(f"确认删除账号 '{account_name}'？[y/N]: ").strip().lower()
                    if confirm == 'y' or confirm == 'yes':
                        delete_account(account_name)
            else:
                print(f"❌ 账号 '{account_name}' 不存在")

        elif choice == str(migrate_idx):
            # 迁移旧Cookie
            migrate_old_cookies()

        elif choice.isdigit():
            # 选择账号
            idx = int(choice)
            if 1 <= idx <= len(accounts):
                selected_account = accounts[idx - 1]
                if selected_account != current_account:
                    set_current_account(selected_account)
                else:
                    print(f"✅ 当前已经是账号 '{selected_account}'")
            else:
                print("\n❌ 无效的选项")
        else:
            print("\n❌ 无效的选项")


def show_menu():
    """显示菜单"""
    # 先重命名文件
    rename_video_files()

    # 显示视频信息
    show_video_info()

    print("\n" + "=" * 60)
    print("🚀 社交媒体自动发布工具")
    print("=" * 60)

    # 显示当前账号
    current_account = get_current_account()
    print(f"当前账号: {current_account}")

    print()
    print("请选择操作：")
    print()

    # 选项1：执行所有
    print("  [1] 执行所有平台")

    # 选项2-N：执行单个平台
    for i, platform in enumerate(PLATFORMS, start=2):
        status = "✅" if check_cookie_exists(platform['id']) else "❌"
        print(f"  [{i}] {platform['name']}\t{status}")

    # 账号管理选项
    account_option = len(PLATFORMS) + 2
    print(f"  [{account_option}] 切换账号")

    # 最后一个选项：设置定时时间
    last_option = len(PLATFORMS) + 3
    print(f"  [{last_option}] 设置定时发布时间")
    print()
    print("  [0] 退出")
    print("=" * 60)


def get_schedule_time_config():
    """获取当前的定时配置"""
    config = load_config()
    schedule_time = config.get('schedule_time', None)

    if schedule_time:
        print(f"\n当前定时设置: {schedule_time}")
    else:
        print("\n当前设置: 立即发布")

    return schedule_time


def set_schedule_time():
    """设置定时发布时间"""
    print("\n" + "=" * 60)
    print("⏰ 设置定时发布时间")
    print("=" * 60)
    print()
    print("请选择：")
    print("  [1] 立即发布")
    print("  [2] 定时发布（指定日期和时间）")
    print("  [3] 定时发布（明天几点）")
    print()

    choice = input("请输入选项 [1-3]: ").strip()

    schedule_time = None
    config = load_config()

    if choice == '1':
        # 立即发布
        schedule_time = None
        print("✅ 已设置为：立即发布")

    elif choice == '2':
        # 指定日期和时间
        print("\n请输入发布时间（格式：YYYY-MM-DD HH:MM）")
        print("例如：2026-01-23 16:00")
        time_str = input("发布时间: ").strip()

        try:
            # 验证格式
            dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
            if dt <= datetime.now():
                print("⚠️  警告：发布时间不能早于当前时间")
                return None

            schedule_time = time_str
            print(f"✅ 已设置为：{schedule_time}")
        except ValueError:
            print("❌ 时间格式错误，请使用格式：YYYY-MM-DD HH:MM")
            return None

    elif choice == '3':
        # 明天几点
        print("\n请输入发布时间（24小时制）")
        print("例如：16")
        hour_str = input("几点发布: ").strip()

        try:
            hour = int(hour_str)
            if hour < 0 or hour > 23:
                print("❌ 时间必须在 0-23 之间")
                return None

            # 计算明天的时间
            tomorrow = datetime.now() + timedelta(days=1)
            schedule_time = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M')
            print(f"✅ 已设置为：{schedule_time}（明天 {hour}点）")
        except ValueError:
            print("❌ 请输入有效的数字（0-23）")
            return None

    else:
        print("❌ 无效的选项")
        return None

    # 保存到配置
    if schedule_time is None or choice != '':
        config['schedule_time'] = schedule_time
        config_file = Path('config.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"💾 配置已保存到 config.json")

    return schedule_time


def run_script_with_monitor(script_path, platform_info, schedule_time=None):
    """
    运行脚本并监控浏览器窗口

    Args:
        script_path: 脚本路径
        platform_info: 平台信息
        schedule_time: 定时发布时间

    Returns:
        (success, result_message)
    """
    if not platform_info['has_browser']:
        # Bilibili 等无浏览器平台，直接运行
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            success = result.returncode == 0

            if success:
                return True, "发布成功"
            else:
                return False, f"发布失败: {result.stderr[-100:] if result.stderr else '未知错误'}"
        except subprocess.TimeoutExpired:
            return False, "发布超时（10分钟）"
        except Exception as e:
            return False, f"发布出错: {str(e)}"

    # 有浏览器的平台，需要监控窗口
    process = None
    try:
        print(f"\n⏳ 正在启动 {platform_info['name']} 上传...")
        print(f"💡 上传完成后请手动关闭浏览器窗口，程序会自动检测并继续")
        print(f"   （如果浏览器窗口已关闭，程序将自动继续下一个平台）")

        # 启动进程
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # 监控进程
        start_time = time.time()

        while True:
            # 检查进程是否结束
            if process.poll() is not None:
                print(f"\n✅ {platform_info['name']} 上传进程已结束")
                break

            # 检查是否超时（30分钟）
            if time.time() - start_time > 1800:
                print(f"\n⚠️  {platform_info['name']} 运行超时（30分钟），正在终止...")
                process.terminate()
                time.sleep(5)
                if process.poll() is None:
                    process.kill()
                return False, "运行超时"

            # 等待一段时间
            time.sleep(2)

        # 获取返回码
        return_code = process.returncode
        success = return_code == 0

        if success:
            if schedule_time:
                return True, f"定时发布成功（{schedule_time}）"
            else:
                return True, "发布成功"
        else:
            return False, "发布失败（请查看日志）"

    except KeyboardInterrupt:
        if process:
            process.terminate()
        print(f"\n⚠️  {platform_info['name']} 被用户中断")
        return False, "用户中断"
    except Exception as e:
        return False, f"运行出错: {str(e)}"


def ask_user_login(platform_name, login_script):
    """询问用户是否先登录"""
    print(f"\n{'=' * 60}")
    print(f"⚠️  {platform_name} 的 Cookie 文件不存在")
    print(f"{'=' * 60}")

    if login_script and Path(login_script).exists():
        choice = input(f"是否先登录 {platform_name}? [y/N/s=跳过]: ").strip().lower()
        if choice == 'y' or choice == 'yes':
            return 'login'
        elif choice == 's' or choice == 'skip':
            return 'skip'
    else:
        choice = input(f"是否跳过 {platform_name}? [Y/n]: ").strip().lower()
        if choice == 'n' or choice == 'no':
            return 'skip'

    return 'skip'


def run_login(login_script):
    """运行登录脚本"""
    try:
        print(f"\n正在启动登录...")
        result = subprocess.run(
            [sys.executable, str(login_script)],
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 运行登录脚本失败: {e}")
        return False


def run_all_platforms(schedule_time=None):
    """运行所有平台"""
    print("\n" + "=" * 60)
    print(f"🚀 开始执行所有平台")
    if schedule_time:
        print(f"⏰ 定时发布时间: {schedule_time}")
    else:
        print(f"⏰ 发布方式: 立即发布")
    print("=" * 60)

    # 检查视频目录
    videos_dir = Path("videos")
    if not videos_dir.exists():
        print("❌ videos/ 目录不存在")
        print("请先创建 videos/ 目录并放入视频文件")
        return

    video_files = list(videos_dir.glob("*.mp4"))
    if not video_files:
        print("❌ videos/ 目录下没有视频文件")
        return

    print(f"✅ 找到 {len(video_files)} 个视频文件")
    print()

    # 统计
    results = {}

    for i, platform in enumerate(PLATFORMS, 1):
        platform_name = platform['name']
        platform_id = platform['id']

        print(f"\n{'=' * 60}")
        print(f"📱 [{i}/{len(PLATFORMS)}] {platform_name}")
        print(f"{'=' * 60}")

        # 检查平台是否启用
        if not is_platform_enabled(platform_id):
            print(f"⊗ {platform_name} - 已禁用（在 config.json 中配置）")
            results[platform_id] = {'status': 'disabled', 'message': '已禁用'}
            continue

        # 检查 cookie
        if not check_cookie_exists(platform['cookie_file']):
            action = ask_user_login(platform_name, platform.get('login_script'))

            if action == 'login':
                success = run_login(platform['login_script'])
                if not success:
                    print(f"❌ {platform_name} 登录失败")
                    results[platform_id] = {'status': 'login_failed', 'message': '登录失败'}
                    continue

                if not check_cookie_exists(platform['cookie_file']):
                    print(f"⚠️  {platform_name} Cookie 仍未生成")
                    results[platform_id] = {'status': 'no_cookie', 'message': '无 Cookie'}
                    continue
            else:
                print(f"⊘ {platform_name} - 跳过（无 Cookie）")
                results[platform_id] = {'status': 'skipped', 'message': '无 Cookie，已跳过'}
                continue

        # 运行上传脚本
        script_path = Path(platform['script'])
        if not script_path.exists():
            print(f"❌ 上传脚本不存在: {script_path}")
            results[platform_id] = {'status': 'script_not_found', 'message': '脚本不存在'}
            continue

        success, message = run_script_with_monitor(script_path, platform, schedule_time)

        if success:
            print(f"✅ {platform_name} - {message}")
            results[platform_id] = {'status': 'success', 'message': message}
        else:
            print(f"❌ {platform_name} - {message}")
            results[platform_id] = {'status': 'failed', 'message': message}

        # 等待一下再执行下一个
        if i < len(PLATFORMS):
            print(f"\n⏳ 3 秒后开始下一个平台...")
            time.sleep(3)

    # 打印最终结果
    print_final_results(results)


def run_single_platform(platform, schedule_time=None):
    """运行单个平台"""
    platform_name = platform['name']
    platform_id = platform['id']

    print(f"\n{'=' * 60}")
    print(f"📱 {platform_name}")
    print(f"{'=' * 60}")

    if schedule_time:
        print(f"⏰ 定时发布时间: {schedule_time}")
    else:
        print(f"⏰ 发布方式: 立即发布")

    # 检查平台是否启用
    if not is_platform_enabled(platform_id):
        print(f"⊗ {platform_name} - 已禁用（在 config.json 中配置）")
        input("\n按回车键继续...")
        return

    # 检查 cookie
    if not check_cookie_exists(platform['cookie_file']):
        action = ask_user_login(platform_name, platform.get('login_script'))

        if action == 'login':
            success = run_login(platform['login_script'])
            if not success:
                print(f"❌ {platform_name} 登录失败")
                input("\n按回车键继续...")
                return

            if not check_cookie_exists(platform['cookie_file']):
                print(f"⚠️  {platform_name} Cookie 仍未生成")
                input("\n按回车键继续...")
                return
        else:
            print(f"⊘ {platform_name} - 跳过（无 Cookie）")
            input("\n按回车键继续...")
            return

    # 运行上传脚本
    script_path = Path(platform['script'])
    if not script_path.exists():
        print(f"❌ 上传脚本不存在: {script_path}")
        input("\n按回车键继续...")
        return

    print(f"\n⏳ 正在启动 {platform_name} 上传...")
    print(f"💡 上传完成后，请关闭浏览器窗口或等待完成")
    print(f"💡 然后按回车键继续")

    # 启动进程
    process = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # 监控进程
    start_time = time.time()

    while True:
        # 检查进程是否结束
        if process.poll() is not None:
            print(f"\n✅ {platform_name} 上传进程已结束")
            break

        # 检查是否超时（30分钟）
        if time.time() - start_time > 1800:
            print(f"\n⚠️  {platform_name} 运行超时（30分钟），正在终止...")
            process.terminate()
            time.sleep(5)
            if process.poll() is None:
                process.kill()
            break

        # 等待一段时间
        time.sleep(2)

    # 按任意键继续
    input("\n按回车键继续...")


def print_final_results(results):
    """打印最终结果"""
    print("\n" + "=" * 60)
    print("📊 所有平台发布结果")
    print("=" * 60)

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for platform in PLATFORMS:
        platform_id = platform['id']
        platform_name = platform['name']
        result = results.get(platform_id, {'status': 'unknown', 'message': '未知'})

        status = result['status']
        message = result['message']

        if status == 'success':
            symbol = '✅'
            success_count += 1
        elif status == 'failed':
            symbol = '❌'
            failed_count += 1
        elif status == 'skipped' or status == 'no_cookie' or status == 'disabled':
            symbol = '⊘'
            skipped_count += 1
        else:
            symbol = '❓'

        print(f"{symbol} {platform_name}: {message}")

    print()
    print(f"总计: {len(PLATFORMS)} 个平台")
    print(f"✅ 成功: {success_count}")
    print(f"❌ 失败: {failed_count}")
    print(f"⊘ 跳过: {skipped_count}")
    print("=" * 60)

    # 保存结果
    results_file = Path("upload_results.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n📁 结果已保存到: {results_file}")


def main():
    """主函数"""
    # 首先显示账号选择菜单
    show_account_menu()

    while True:
        show_menu()

        # 显示当前定时设置
        schedule_time = get_schedule_time_config()

        choice = input("\n请输入选项: ").strip()

        if choice == '0':
            print("\n👋 再见！")
            break

        elif choice == '1':
            # 执行所有平台
            run_all_platforms(schedule_time)

        elif choice.isdigit() and 2 <= int(choice) <= len(PLATFORMS) + 1:
            # 执行单个平台
            index = int(choice) - 2
            platform = PLATFORMS[index]
            run_single_platform(platform, schedule_time)

        elif choice == str(len(PLATFORMS) + 2):
            # 切换账号
            show_account_menu()

        elif choice == str(len(PLATFORMS) + 3):
            # 设置定时时间
            set_schedule_time()

        else:
            print("\n❌ 无效的选项，请重新选择")
            time.sleep(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户退出")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
