# -*- coding: utf-8 -*-
"""
视频项目工具函数
用于获取当前的视频项目目录
"""

from pathlib import Path
from conf import BASE_DIR
import sys


def get_video_project_dir():
  """
  获取当前的视频项目目录

  videos/ 目录下除了 demo 文件夹外，其他文件夹视为待上传的视频项目
  只允许有一个待上传的项目，如果有多个则提示并使用第一个

  Returns:
    Path: 项目目录路径，如果没有则返回 None
  """
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
