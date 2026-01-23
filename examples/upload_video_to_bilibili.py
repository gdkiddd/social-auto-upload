#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilibili 视频上传脚本
支持从 txt 文件读取标题、标签和完整描述
"""

import time
import json
from pathlib import Path

from uploader.bilibili_uploader.main import read_cookie_json_file, extract_keys_from_json, random_emoji, BilibiliUploader
from conf import BASE_DIR
from myUtils.account_manager import get_current_account, get_account_cookie_path
from utils.constant import VideoZoneTypes
from utils.files_times import generate_schedule_time_next_day


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


def load_config():
    """加载全局配置"""
    config_file = BASE_DIR / "config.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


if __name__ == '__main__':
    # 加载全局配置
    config = load_config()

    filepath = Path(BASE_DIR) / "videos"
    current_account = get_current_account()
    account_file = get_account_cookie_path(current_account, 'bilibili')

    if not account_file.exists():
        print(f"❌ {account_file.name} 配置文件不存在")
        print(f"请先运行: ./bilibili_login.sh")
        exit()

    # 读取 cookie
    cookie_data = read_cookie_json_file(account_file)
    cookie_data = extract_keys_from_json(cookie_data)

    # 从配置读取视频分区，默认为知识分区
    tid = config.get('bilibili_tid', VideoZoneTypes.KNOWLEDGE.value)

    # 获取视频目录
    folder_path = Path(filepath)
    files = list(folder_path.glob("*.mp4"))

    if not files:
        print(f"❌ 在 {filepath} 目录下没有找到视频文件")
        exit()

    file_num = len(files)

    # 从配置读取是否定时发布，默认为立即发布
    use_schedule = config.get('bilibili_schedule', False)

    if use_schedule:
        timestamps = generate_schedule_time_next_day(file_num, 1, daily_times=[16], timestamps=True)
        print(f"发布方式: 定时发布（第二天 16:00）")
    else:
        timestamps = [0] * file_num  # 立即发布
        print(f"发布方式: 立即发布")

    print(f"=== Bilibili 视频上传 ===")
    print(f"找到 {file_num} 个视频文件")
    print(f"视频分区: tid={tid}")
    print("=" * 60)
    print()

    for index, file in enumerate(files):
        # 读取视频信息
        title, tags, desc = get_video_info(file)

        # 添加随机 emoji 避免标题重复
        title_with_emoji = title + random_emoji()

        # 打印视频信息
        print(f"📹 视频 {index + 1}/{file_num}")
        print(f"   文件: {file.name}")
        print(f"   标题: {title_with_emoji}")
        print(f"   标签: {', '.join(tags) if tags else '无'}")
        print(f"   描述: {desc[:50]}..." if len(desc) > 50 else f"   描述: {desc}")
        print()

        # 创建上传实例并上传
        bili_uploader = BilibiliUploader(
            cookie_data=cookie_data,
            file=file,
            title=title_with_emoji,
            desc=desc,
            tid=tid,
            tags=tags,
            dtime=timestamps[index]
        )

        try:
            bili_uploader.upload()
            print(f"✅ {file.name} 上传成功")
        except Exception as e:
            print(f"❌ {file.name} 上传失败: {str(e)}")

        print()

        # 避免上传过快
        if index < file_num - 1:
            print("等待 30 秒后上传下一个视频...")
            time.sleep(30)

    print("=" * 60)
    print("✅ 所有视频上传完成！")
    print(f"注: Bilibili 使用 API 方式上传，没有浏览器窗口")
