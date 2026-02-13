# -*- coding: utf-8 -*-
"""
视频项目工具函数
用于获取当前的视频项目目录
"""

from pathlib import Path
from conf import BASE_DIR
import sys
import json


def get_video_project_dir():
    """
    获取当前的视频项目目录

    优先从 videos/uploading.json 读取正在上传的视频路径
    如果没有，则从 videos/ 目录下查找（排除 demo 文件夹）
    只允许有一个待上传的项目，如果有多个则提示并使用第一个

    Returns:
        Path: 项目目录路径，如果没有则返回 None
    """
    uploading_json = BASE_DIR / "videos" / "uploading.json"

    # 优先读取 uploading.json
    if uploading_json.exists():
        try:
            with open(uploading_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                folder_path = data.get('folder_path')
                if folder_path:
                    project_dir = Path(folder_path)
                    if project_dir.exists():
                        print(f"📂 从 uploading.json 读取项目: {project_dir.name}")
                        return project_dir
                    else:
                        print(f"⚠️  uploading.json 中的路径不存在: {folder_path}")
        except Exception as e:
            print(f"⚠️  读取 uploading.json 失败: {e}")

    # 降级到扫描 videos/ 目录
    videos_dir = BASE_DIR / "videos"

    if not videos_dir.exists():
        return None

    # 获取所有文件夹（排除 demo）
    project_dirs = []
    for item in videos_dir.iterdir():
        if item.is_dir() and item.name.lower() != 'demo':
            project_dirs.append(item)

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
        print("💡 请在 videos/ 目录下创建一个文件夹（如 '项目1'），放入视频文件")
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
