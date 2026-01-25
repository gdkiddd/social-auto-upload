#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 视频上传脚本
支持从 txt 文件读取标题、标签和完整描述
"""

import time
import asyncio
from pathlib import Path

from uploader.youtube_uploader.main import YouTubeUploader
from conf import BASE_DIR
from myUtils.account_manager import get_current_account, get_account_cookie_path
from myUtils.video_project import get_video_project_files


def get_video_info(video_file):
  """
  从视频文件和对应的 txt 文件中读取标题、标签和描述

  txt 文件格式示例：
  这是视频标题
  #标签1 #标签2 #标签3
  这是视频描述的第一行
  这是视频描述的第二行

  Args:
    video_file: 视频文件路径

  Returns:
    (title, tags, description)
  """
  txt_file = video_file.with_suffix('.txt')

  if not txt_file.exists():
    print(f"⚠️  警告: 未找到 {txt_file.name}，使用默认标题")
    return video_file.stem, [], f"视频来自自动上传工具\n视频文件: {video_file.name}"

  with open(txt_file, 'r', encoding='utf-8') as f:
    lines = f.read().strip().split('\n')

  if len(lines) < 1:
    return video_file.stem, [], "无描述"

  # 第一行是标题
  title = lines[0].strip()

  # 第二行是标签（如果有）
  tags = []
  description_lines = []

  if len(lines) >= 2:
    second_line = lines[1].strip()
    # 判断第二行是否是标签（包含 # 号）
    if '#' in second_line:
      # 提取标签
      tags = second_line.replace('#', ' ').split()
      tags = [tag.strip() for tag in tags if tag.strip()]
      # 描述从第三行开始
      if len(lines) >= 3:
        description_lines = lines[2:]
    else:
      # 第二行不是标签，作为描述的一部分
      description_lines = lines[1:]

  # 如果没有找到标签，尝试从标题中提取
  if not tags and '#' in title:
    title_parts = title.split('#')
    title = title_parts[0].strip()
    tags = [tag.strip() for tag in title_parts[1:] if tag.strip()]

  # 组合描述
  if description_lines:
    description = '\n'.join(description_lines).strip()
  else:
    description = f"视频标题：{title}\n\n感谢观看！"

  return title, tags, description


async def upload_single_video(youtube_uploader):
  """上传单个视频的异步包装函数"""
  return await youtube_uploader.upload()


if __name__ == '__main__':
  # 获取当前账号
  current_account = get_current_account()
  account_file = get_account_cookie_path(current_account, 'youtube')

  if not account_file.exists():
    print(f"❌ {account_file.name} 配置文件不存在")
    print(f"请先运行: python examples/get_youtube_cookie.py")
    exit(1)

  # 获取视频项目文件（使用通用函数）
  project_dir, files = get_video_project_files()
  file_num = len(files)

  print(f"=== YouTube 视频上传 ===")
  print(f"找到 {file_num} 个视频文件")
  print("=" * 60)
  print()

  success_count = 0
  failed_count = 0

  for index, file in enumerate(files):
    # 读取视频信息
    title, tags, desc = get_video_info(file)

    # 查找封面图片
    video_file = Path(file)
    cover_extensions = ['.png', '.PNG', '.jpg', '.jpeg', '.JPG', '.JPEG']
    cover_file = None

    for ext in cover_extensions:
      potential_cover = video_file.with_suffix(ext)
      if potential_cover.exists():
        cover_file = potential_cover
        break

    if not cover_file:
      # 如果找不到同名的封面图，尝试查找视频文件所在目录下的第一个图片
      video_dir = video_file.parent
      image_patterns = ['*.png', '*.PNG', '*.jpg', '*.jpeg', '*.JPG', '*.JPEG']
      for pattern in image_patterns:
        images = list(video_dir.glob(pattern))
        if images:
          cover_file = images[0]
          break

    print(f"\n{'=' * 60}")
    print(f"📹 视频 {index + 1}/{file_num}")
    print(f"{'=' * 60}")
    print(f"   文件: {file.name}")
    print(f"   大小: {file.stat().st_size / (1024*1024):.1f} MB")
    print(f"   标题: {title}")
    print(f"   标签: {', '.join(tags) if tags else '无'}")
    print(f"   封面: {cover_file.name if cover_file else '无'}")
    print(f"{'=' * 60}")
    print()

    # 创建上传实例并上传
    youtube_uploader = YouTubeUploader(
      account_file=account_file,
      file=file,
      title=title,
      desc=desc,
      tags=tags,
      thumbnail_path=cover_file
    )

    upload_success = False
    try:
      # 使用 asyncio 运行异步上传
      upload_success = asyncio.run(upload_single_video(youtube_uploader))
      if not upload_success:
        print(f"❌ {file.name} 上传失败，请查看上方错误信息")
        failed_count += 1
      else:
        print(f"✅ {file.name} 上传成功")
        success_count += 1
    except Exception as e:
      error_msg = str(e)
      print(f"❌ {file.name} 上传异常: {error_msg}")
      import traceback
      traceback.print_exc()
      failed_count += 1

    print()

    # 避免上传过快
    if index < file_num - 1:
      print("等待 30 秒后上传下一个视频...")
      time.sleep(30)

  print("=" * 60)
  print("📊 上传统计")
  print("=" * 60)
  print(f"成功: {success_count} 个")
  print(f"失败: {failed_count} 个")
  print(f"总计: {file_num} 个")
  print("=" * 60)
  print()

  # 根据结果返回不同的退出码
  if failed_count > 0:
    exit(1)  # 有失败则返回退出码 1
  else:
    exit(0)  # 全部成功则返回退出码 0
