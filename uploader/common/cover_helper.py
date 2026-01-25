# -*- coding: utf-8 -*-
"""
封面图片处理工具
"""

from pathlib import Path
from typing import Optional


def find_cover_image(video_file_path: str) -> Optional[Path]:
    """
    查找视频封面图片

    优先级：
    1. 同名封面（不同扩展名）
    2. 视频所在目录下的第一个图片

    Args:
        video_file_path: 视频文件路径

    Returns:
        封面图片路径，如果找不到则返回 None
    """
    video_file = Path(video_file_path)
    cover_extensions = ['.png', '.PNG', '.jpg', '.jpeg', '.JPG', '.JPEG']

    # 1. 首先尝试查找同名封面
    for ext in cover_extensions:
        potential_cover = video_file.with_suffix(ext)
        if potential_cover.exists():
            return potential_cover

    # 2. 查找视频所在目录下的第一个图片
    video_dir = video_file.parent
    image_patterns = ['*.png', '*.PNG', '*.jpg', '*.jpeg', '*.JPG', '*.JPEG']

    for pattern in image_patterns:
        images = list(video_dir.glob(pattern))
        if images:
            return images[0]

    return None
