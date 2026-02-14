# -*- coding: utf-8 -*-
"""
视频项目工具函数
用于获取当前的视频项目目录
"""

import sys
import json
import re
from pathlib import Path

from conf import BASE_DIR


def _log_with_logger(logger, level, message):
    """统一日志输出：优先使用外部 logger，否则使用 print。"""
    if logger and hasattr(logger, level):
        getattr(logger, level)(message)
    else:
        print(message)


def _sort_project_dirs(dirs):
    """项目目录排序：优先按前缀序号，再按名称。"""
    def _key(d):
        number = extract_folder_number(d.name)
        if number is None:
            return (1, 10**9, d.name.lower())
        return (0, number, d.name.lower())
    return sorted(dirs, key=_key)


def _find_projects_in_dir(parent_dir):
    """在指定目录下查找包含 mp4 的项目目录。"""
    if not parent_dir.exists() or not parent_dir.is_dir():
        return []
    projects = []
    for item in parent_dir.iterdir():
        if not item.is_dir() or item.name.startswith('.'):
            continue
        if list(item.glob("*.mp4")):
            projects.append(item)
    return _sort_project_dirs(projects)


def extract_folder_number(folder_name):
    """从文件夹名中提取序号，例如：'12) 标题' -> 12。"""
    match = re.match(r'^(\d+)\)', folder_name or '')
    if match:
        return int(match.group(1))
    return None


def load_uploading_info(uploading_json=None, logger=None):
    """
    读取 uploading.json。

    Returns:
        dict | None: 包含 folder_path/folder_name/folder_number 的字典；无记录返回 None
    """
    uploading_json = uploading_json or (BASE_DIR / "videos" / "uploading.json")
    if not Path(uploading_json).exists():
        return None

    try:
        with open(uploading_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else None
    except Exception as e:
        _log_with_logger(logger, "warning", f"⚠️  读取 uploading.json 失败: {e}")
        return None


def save_uploading_info(folder_number, folder_name, folder_path, uploading_json=None, logger=None):
    """写入 uploading.json。"""
    uploading_json = uploading_json or (BASE_DIR / "videos" / "uploading.json")
    data = {
        'folder_number': folder_number,
        'folder_name': folder_name,
        'folder_path': str(folder_path),
    }
    with open(uploading_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _log_with_logger(logger, "info", f"上传中记录已更新: {folder_name}")


def clear_uploading_info(uploading_json=None, logger=None):
    """删除 uploading.json（存在时）。"""
    uploading_json = uploading_json or (BASE_DIR / "videos" / "uploading.json")
    uploading_json = Path(uploading_json)
    if uploading_json.exists():
        uploading_json.unlink()
        _log_with_logger(logger, "info", "已清理 uploading.json")


def get_next_video_folder(source_dir, current_number=None, logger=None):
    """
    从账号源目录里按序号获取下一个待上传视频文件夹。

    Args:
        source_dir: 源目录，例如 videos/Amy
        current_number: 当前序号（仅找更大的序号）

    Returns:
        tuple: (folder_number, folder_path)；未找到时为 (None, None)
    """
    source_dir = Path(source_dir)
    if not source_dir.exists():
        _log_with_logger(logger, "error", f"源目录不存在: {source_dir}")
        return None, None

    folders = [f for f in source_dir.iterdir() if f.is_dir() and not f.name.startswith('.')]
    folder_numbers = []
    for folder in folders:
        number = extract_folder_number(folder.name)
        if number is not None:
            folder_numbers.append((number, folder))

    if not folder_numbers:
        _log_with_logger(logger, "warning", f"未找到可上传文件夹: {source_dir}")
        return None, None

    folder_numbers.sort(key=lambda x: x[0])
    start_number = current_number if current_number is not None else 0

    for number, folder in folder_numbers:
        if number > start_number:
            return number, folder

    return None, None


def get_video_project_dir():
    """
    获取当前的视频项目目录

    优先从 videos/uploading.json 读取正在上传的视频路径
    如果没有，则从 videos/ 目录下查找（排除 demo 文件夹）
    只允许有一个待上传的项目，如果有多个则提示并使用第一个

    Returns:
        Path: 项目目录路径，如果没有则返回 None
    """
    # 优先读取 uploading.json
    data = load_uploading_info()
    if data:
        folder_path = data.get('folder_path')
        if folder_path:
            project_dir = Path(folder_path)
            if project_dir.exists():
                print(f"📂 从 uploading.json 读取项目: {project_dir.name}")
                return project_dir
            print(f"⚠️  uploading.json 中的路径不存在: {folder_path}")

    # 其次尝试账号目录：videos/当前账号/项目目录
    videos_dir = BASE_DIR / "videos"
    try:
        from myUtils.account_manager import get_current_account
        current_account = get_current_account()
    except Exception:
        current_account = None

    if current_account:
        account_dir = videos_dir / current_account
        if not account_dir.exists():
            account_dirs = []
            if videos_dir.exists():
                account_dirs = [
                    d.name for d in videos_dir.iterdir()
                    if d.is_dir() and not d.name.startswith('.') and d.name.lower() != 'demo'
                ]
                account_dirs.sort()
            print(f"⚠️  当前账号是 {current_account}，但未找到目录: {account_dir}")
            if account_dirs:
                print(f"💡 可用视频账号目录: {', '.join(account_dirs)}")
            print("💡 请切换到正确账号，或创建同名目录后再重试")

        account_projects = _find_projects_in_dir(account_dir)
        if account_projects:
            if len(account_projects) > 1:
                print(f"\n⚠️  检测到账号 {current_account} 有 {len(account_projects)} 个视频项目：")
                for i, d in enumerate(account_projects, 1):
                    print(f"  [{i}] {d.name}")
                print(f"\n💡 只使用第一个项目: {account_projects[0].name}")
            print(f"📂 从账号目录读取项目: {account_projects[0].name}")
            return account_projects[0]

        # 兼容：如果账号目录本身直接放 mp4，也视为项目目录
        if account_dir.exists() and list(account_dir.glob("*.mp4")):
            print(f"📂 从账号目录读取项目: {account_dir.name}")
            return account_dir
        if account_dir.exists():
            print(f"⚠️  账号目录存在但未找到可上传项目: {account_dir}")
            print("💡 目录结构应为: videos/用户名/视频文件夹/xxx.mp4")

    # 降级到扫描 videos/ 根目录

    if not videos_dir.exists():
        return None

    # 获取根目录中真正的项目文件夹（目录内包含 mp4，且排除 demo）
    project_dirs = []
    for item in videos_dir.iterdir():
        if not item.is_dir() or item.name.startswith('.') or item.name.lower() == 'demo':
            continue
        if list(item.glob("*.mp4")):
            project_dirs.append(item)
    project_dirs = _sort_project_dirs(project_dirs)

    if not project_dirs:
        return None

    if len(project_dirs) > 1:
        print(f"\n⚠️  检测到 {len(project_dirs)} 个视频项目：")
        for i, d in enumerate(project_dirs, 1):
            print(f"  [{i}] {d.name}")
        print(f"\n💡 只使用第一个项目: {project_dirs[0].name}")

    return project_dirs[0]


def get_video_files_from_project(project_dir=None):
    """
    从项目目录获取视频文件

    Args:
        project_dir: 项目目录，如果为 None 则自动获取

    Returns:
        list: 视频文件列表
    """
    if project_dir is None:
        project_dir = get_video_project_dir()

    if project_dir is None:
        return []

    # 获取项目目录下的所有 mp4 文件
    video_files = sorted(list(project_dir.glob("*.mp4")))
    return video_files


def get_video_project_files(exit_on_error=True):
    """
    获取视频项目目录和视频文件（带错误处理和提示）

    这是一个便捷函数，封装了获取项目目录和视频文件的完整流程

    Args:
        exit_on_error: 如果出错是否退出程序，默认 True

    Returns:
        (project_dir, video_files) 元组
            - project_dir: Path 对象，项目目录路径
            - video_files: list，视频文件列表

        如果出错且 exit_on_error=True，则直接退出程序
        如果出错且 exit_on_error=False，则返回 (None, [])
    """
    # 获取项目目录
    project_dir = get_video_project_dir()
    if project_dir is None:
        print("❌ videos/ 目录下没有找到视频项目")
        print("💡 推荐目录结构: videos/用户名/视频文件夹/xxx.mp4")
        if exit_on_error:
            sys.exit(1)
        return None, []

    print(f"📁 当前项目: {project_dir.name}")

    # 获取视频文件
    video_files = get_video_files_from_project(project_dir)
    if not video_files:
        print("❌ 项目目录下没有找到视频文件 (.mp4)")
        if exit_on_error:
            sys.exit(1)
        return project_dir, []

    print(f"✅ 找到 {len(video_files)} 个视频文件")
    return project_dir, video_files
