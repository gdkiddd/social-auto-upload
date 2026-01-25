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
from conf import load_config, save_config, is_platform_enabled, reload_config
from myUtils.account_manager import (
    get_accounts, add_account, delete_account,
    get_current_account, set_current_account,
    get_account_cookie_path, check_account_cookie_exists,
    ensure_default_account, migrate_old_cookies
)
from myUtils.publish_history import get_publish_history
from myUtils.video_project import get_video_project_dir, get_video_files_from_project

# 确保默认账号存在
ensure_default_account()


# 平台配置（按顺序）
PLATFORMS = [
    {
        'id': 'xiaohongshu',
        'name': '小红书',
        'cookie_file': 'xiaohongshu',  # 使用平台ID，由 account_manager 处理路径
        'script': 'examples/upload_video_to_xiaohongshu.py',
        'login_script': 'examples/get_xiaohongshu_cookie.py',
        'has_browser': True
    },
    {
        'id': 'tencent',
        'name': '视频号',
        'cookie_file': 'tencent',
        'script': 'examples/upload_video_to_tencent.py',
        'login_script': 'examples/get_tencent_cookie.py',
        'has_browser': True
    },
    {
        'id': 'bilibili',
        'name': 'Bilibili',
        'cookie_file': 'bilibili',
        'script': 'examples/upload_video_to_bilibili.py',
        'login_script': 'examples/get_bilibili_cookie_simple.py',
        'has_browser': True
    },
    {
        'id': 'kuaishou',
        'name': '快手',
        'cookie_file': 'kuaishou',
        'script': 'examples/upload_video_to_kuaishou.py',
        'login_script': 'examples/get_kuaishou_cookie.py',
        'has_browser': True
    },
    {
        'id': 'baijiahao',
        'name': '百家号',
        'cookie_file': 'baijiahao',
        'script': 'examples/upload_video_to_baijiahao.py',
        'login_script': 'examples/get_baijiahao_cookie.py',
        'has_browser': True
    },
    {
        'id': 'douyin',
        'name': '抖音',
        'cookie_file': 'douyin',
        'script': 'examples/upload_video_to_douyin.py',
        'login_script': 'examples/get_douyin_cookie.py',
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
    """重命名 txt、png、jpg 等文件，使其与对应的 mp4 文件同名"""
    project_dir = get_video_project_dir()
    if project_dir is None:
        return

    video_files = list(project_dir.glob("*.mp4"))
    if len(video_files) == 0:
        return
    elif len(video_files) == 1:
        # 只有一个视频，把所有 txt 和图片文件重命名为该视频的名字
        video_name = video_files[0].stem
        renamed_count = 0

        # 支持更多图片格式
        for ext in ['*.txt', '*.png', '*.PNG', '*.jpg', '*.JPG', '*.jpeg', '*.JPEG']:
            matching_files = list(project_dir.glob(ext))

            for file in matching_files:
                # 如果文件不是对应的同名文件
                if file.stem != video_name:
                    new_name = project_dir / f"{video_name}{file.suffix}"
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
                project_dir / f"{video_name}.txt",
                project_dir / f"{video_name}.png",
                project_dir / f"{video_name}.PNG",
                project_dir / f"{video_name}.jpg",
                project_dir / f"{video_name}.JPG",
                project_dir / f"{video_name}.jpeg",
                project_dir / f"{video_name}.JPEG"
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

    project_dir = get_video_project_dir()

    if project_dir is None:
        print("⚠️  videos/ 目录下没有找到视频项目")
        print("💡 请在 videos/ 目录下创建一个文件夹（如 '项目1'），放入视频文件")
        print()
        return

    print(f"📁 项目目录: {project_dir.name}")
    print()

    video_files = get_video_files_from_project(project_dir)

    if not video_files:
        print(f"⚠️  项目目录下没有找到视频文件 (.mp4)")
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

        elif choice == '' or choice == str(continue_idx):
            # 回车或输入继续选项，继续到平台选择
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


def show_platform_settings(platform):
    """显示平台设置菜单"""
    platform_id = platform['id']
    platform_name = platform['name']

    while True:
        print("\n" + "=" * 60)
        print(f"⚙️  {platform_name} 设置")
        print("=" * 60)

        # 获取当前状态
        has_cookie = check_cookie_exists(platform_id)
        is_enabled = is_platform_enabled(platform_id)

        print(f"Cookie 状态: {'✅ 已登录' if has_cookie else '❌ 未登录'}")
        print(f"上传开关: {'✅ 已启用' if is_enabled else '❌ 已禁用'}")
        print()
        print("请选择操作：")
        print("  [1] 立即上传")
        print("  [2] 开启/关闭上传")
        print("  [3] 重登录")
        print()
        print("  [0] 返回")
        print("=" * 60)

        choice = input("\n请输入选项: ").strip()

        if choice == '0':
            break

        elif choice == '1':
            # 立即上传到此平台
            schedule_time = get_schedule_time_config()
            run_single_platform(platform, schedule_time)

        elif choice == '2':
            # 切换上传开关（使用账号级别的配置）
            from myUtils.account_manager import (
                get_current_account,
                is_platform_enabled_for_account,
                set_platform_enabled_for_account
            )

            current_account = get_current_account()
            current_status = is_platform_enabled_for_account(current_account, platform_id)

            # 切换状态
            new_status = not current_status

            # 保存到账号级别的配置
            if set_platform_enabled_for_account(current_account, platform_id, new_status):
                print(f"\n✅ {platform_name} 上传开关已{'启用' if new_status else '禁用'}")
                print(f"💡 配置已保存到账号: {current_account}")
            else:
                print(f"\n❌ 保存配置失败")

        elif choice == '3':
            # 登录/重新登录
            login_script = platform.get('login_script')
            if login_script and Path(login_script).exists():
                print(f"\n正在打开 {platform_name} 登录页面...")
                success = run_login(login_script)
                if success:
                    print(f"\n✅ {platform_name} 登录成功")
                else:
                    print(f"\n❌ {platform_name} 登录失败")
            else:
                print(f"\n❌ {platform_name} 没有配置登录脚本")

        else:
            print("\n❌ 无效的选项")


def show_publish_history():
    """显示发布历史记录"""
    print("\n" + "=" * 60)
    print("📊 发布历史记录")
    print("=" * 60)

    publish_history = get_publish_history()

    print("\n选择查看方式：")
    print("  [1] 查看各平台最新记录")
    print("  [2] 查看所有记录（最近20条）")
    print()
    print("  [0] 返回")
    print("=" * 60)

    choice = input("\n请输入选项: ").strip()

    if choice == '0':
        return
    elif choice == '1':
        # 显示各平台最新记录
        publish_history.display_latest_by_platform()
    elif choice == '2':
        # 显示所有记录
        records = publish_history.get_latest_records(limit=20)
        publish_history.display_records(records)
    else:
        print("\n❌ 无效的选项")

    input("\n按回车键继续...")


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

    # 选项1：全部上传
    print("  [1] 全部上传")

    # 选项2-N：平台设置
    for i, platform in enumerate(PLATFORMS, start=2):
        has_cookie = check_cookie_exists(platform['id'])
        is_enabled = is_platform_enabled(platform['id'])

        # 状态图标：只在未登录时显示❌，已登录不显示图标
        cookie_status = "" if has_cookie else "❌"
        switch_status = "🔴" if not is_enabled else ""

        print(f"  [{i}] {platform['name']}\t{cookie_status} {switch_status}")

    # 账号管理选项
    account_option = len(PLATFORMS) + 2
    print(f"  [{account_option}] 切换账号")

    # 发布历史选项
    history_option = len(PLATFORMS) + 3
    print(f"  [{history_option}] 查看发布历史")

    # 最后一个选项：设置定时时间
    last_option = len(PLATFORMS) + 4
    print(f"  [{last_option}] 设置定时发布时间")

    # 新选项：修改视频信息
    edit_video_option = len(PLATFORMS) + 5
    print(f"  [{edit_video_option}] 修改标题和标签")

    print()
    print("  [0] 退出")
    print()
    print("说明：❌=未登录  🔴=已禁用")
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


def edit_video_info():
    """修改视频标题和标签"""
    project_dir = get_video_project_dir()

    if project_dir is None:
        print("\n❌ videos/ 目录下没有找到视频项目")
        return

    video_files = get_video_files_from_project(project_dir)
    if not video_files:
        print("\n❌ 项目目录下没有视频文件")
        return

    # 显示视频列表
    print("\n" + "=" * 60)
    print(f"📝 选择要修改的视频 (项目: {project_dir.name})")
    print("=" * 60)

    for i, video_file in enumerate(video_files, 1):
        print(f"  [{i}] {video_file.name}")

    print("  [0] 返回")
    print("=" * 60)

    choice = input("\n请选择视频: ").strip()

    if choice == '0':
        return

    try:
        video_index = int(choice) - 1
        if video_index < 0 or video_index >= len(video_files):
            print("\n❌ 无效的选择")
            return
    except ValueError:
        print("\n❌ 无效的输入")
        return

    video_file = video_files[video_index]
    txt_file = video_file.with_suffix('.txt')

    # 读取当前内容
    current_title = ""
    current_tags = ""
    current_desc = ""

    if txt_file.exists():
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')
            if lines:
                current_title = lines[0].strip()
            if len(lines) >= 2:
                current_tags = lines[1].strip()
            if len(lines) >= 3:
                current_desc = lines[2].strip()

    # 显示当前信息并输入新信息
    print("\n" + "=" * 60)
    print(f"📝 修改视频信息: {video_file.name}")
    print("=" * 60)

    print(f"\n当前标题: {current_title}")
    new_title = input("新标题 (直接回车保持不变): ").strip()

    print(f"\n当前标签: {current_tags}")
    new_tags = input("新标签 (直接回车保持不变): ").strip()

    print(f"\n当前描述: {current_desc[:100]}{'...' if len(current_desc) > 100 else ''}")
    new_desc = input("新描述 (直接回车保持不变): ").strip()

    # 如果没有修改，直接返回
    if not new_title and not new_tags and not new_desc:
        print("\n⚠️  未做任何修改")
        return

    # 使用新值或保持原值
    final_title = new_title if new_title else current_title
    final_tags = new_tags if new_tags else current_tags
    final_desc = new_desc if new_desc else current_desc

    # 写入txt文件
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(final_title + '\n')
        f.write(final_tags + '\n')
        f.write(final_desc + '\n')

    print(f"\n✅ 已更新 {txt_file.name}")

    # 如果修改了标题，重命名文件
    if new_title and new_title != current_title:
        old_base = video_file.stem

        # 构建新文件名（替换非法字符）
        safe_title = new_title.replace('/', '-').replace('\\', '-').replace(':', '-')
        safe_title = ''.join(c for c in safe_title if c.isalnum() or c in (' ', '-', '_', '(', ')', '【', '】', '（', '）'))
        safe_title = safe_title.strip()
        safe_title = safe_title[:50] if len(safe_title) > 50 else safe_title  # 限制长度

        if not safe_title:
            print("\n❌ 标题包含无效字符，无法重命名文件")
            print("\n" + "=" * 60)
            return

        new_video_name = f"{safe_title}.mp4"
        new_txt_name = f"{safe_title}.txt"

        new_video_file = videos_dir / new_video_name
        new_txt_file = videos_dir / new_txt_name

        # 重命名视频文件
        if video_file.exists():
            if new_video_file.exists():
                print(f"\n⚠️  目标文件已存在: {new_video_name}")
                overwrite = input("是否覆盖? (y/N): ").strip().lower()
                if overwrite == 'y':
                    new_video_file.unlink()
                    video_file.rename(new_video_file)
                    print(f"✅ 已重命名: {video_file.name} -> {new_video_name}")
                else:
                    print(f"⚠️  跳过视频文件重命名")
            else:
                video_file.rename(new_video_file)
                print(f"✅ 已重命名: {video_file.name} -> {new_video_name}")

        # 重命名txt文件
        if txt_file.exists():
            if new_txt_file.exists():
                # 如果新文件已存在（可能因为视频文件重命名导致），直接覆盖
                new_txt_file.unlink()
            txt_file.rename(new_txt_file)
            print(f"✅ 已重命名: {txt_file.name} -> {new_txt_name}")

        # 重命名png文件（如果存在）
        for ext in ['.png', '.PNG']:
            old_png = videos_dir / f"{old_base}{ext}"
            new_png = videos_dir / f"{safe_title}{ext}"
            if old_png.exists():
                if new_png.exists():
                    new_png.unlink()
                old_png.rename(new_png)
                print(f"✅ 已重命名: {old_png.name} -> {new_png.name}")

        print(f"\n✅ 所有文件已重命名为: {safe_title}")

    print("\n" + "=" * 60)


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
    运行脚本并监控浏览器窗口，实时输出日志

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

    # 有浏览器的平台，需要监控窗口并实时输出日志
    process = None
    try:
        # 启动进程
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # 监控进程并实时输出
        start_time = time.time()

        while True:
            # 实时读取输出
            output = process.stdout.readline()
            if output:
                print(output.strip())

            # 检查进程是否结束
            if process.poll() is not None:
                # 读取剩余的所有输出
                remaining_output = process.stdout.read()
                if remaining_output:
                    print(remaining_output.strip())
                break

            # 检查是否超时（30分钟）
            if time.time() - start_time > 1800:
                print(f"\n⚠️  {platform_info['name']} 运行超时（30分钟），正在终止...")
                process.terminate()
                time.sleep(5)
                if process.poll() is None:
                    process.kill()
                return False, "运行超时"

            # 短暂等待，避免CPU占用过高
            time.sleep(0.1)

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

    # 获取当前视频项目
    project_dir = get_video_project_dir()

    if project_dir is None:
        print("❌ videos/ 目录下没有找到视频项目")
        print("💡 请在 videos/ 目录下创建一个文件夹（如 '项目1'），放入视频文件")
        return

    print(f"📁 当前项目: {project_dir.name}")

    video_files = get_video_files_from_project(project_dir)
    if not video_files:
        print("❌ 项目目录下没有找到视频文件 (.mp4)")
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

    # 检查 cookie，如果没有直接登录，不询问
    if not check_cookie_exists(platform['cookie_file']):
        login_script = platform.get('login_script')
        if login_script and Path(login_script).exists():
            print(f"⚠️  {platform_name} 未登录，正在打开登录页面...")
            success = run_login(login_script)
            if not success:
                print(f"❌ {platform_name} 登录失败")
                input("\n按回车键继续...")
                return

            if not check_cookie_exists(platform['cookie_file']):
                print(f"⚠️  {platform_name} Cookie 仍未生成")
                input("\n按回车键继续...")
                return
        else:
            print(f"❌ {platform_name} 无 Cookie 且无登录脚本")
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
        bufsize=1,
        universal_newlines=True
    )

    # 监控进程并实时输出
    start_time = time.time()

    while True:
        # 实时读取输出
        output = process.stdout.readline()
        if output:
            print(output.strip())

        # 检查进程是否结束
        if process.poll() is not None:
            exit_code = process.returncode

            # 读取剩余的所有输出
            remaining_output = process.stdout.read()
            if remaining_output:
                print(remaining_output.strip())

            if exit_code == 0:
                print(f"\n✅ {platform_name} 上传进程已结束")
            else:
                print(f"\n⚠️  {platform_name} 上传进程异常结束（退出码: {exit_code}）")
                print(f"💡 详细错误信息请查看上方日志")
            break

        # 检查是否超时（30分钟）
        if time.time() - start_time > 1800:
            print(f"\n⚠️  {platform_name} 运行超时（30分钟），正在终止...")
            process.terminate()
            time.sleep(5)
            if process.poll() is None:
                process.kill()
            break

        # 短暂等待，避免CPU占用过高
        time.sleep(0.1)

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
            # 进入平台设置
            index = int(choice) - 2
            platform = PLATFORMS[index]
            show_platform_settings(platform)

        elif choice == str(len(PLATFORMS) + 2):
            # 切换账号
            show_account_menu()

        elif choice == str(len(PLATFORMS) + 3):
            # 查看发布历史
            show_publish_history()

        elif choice == str(len(PLATFORMS) + 4):
            # 设置定时时间
            set_schedule_time()

        elif choice == str(len(PLATFORMS) + 5):
            # 修改视频标题和标签
            edit_video_info()

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
