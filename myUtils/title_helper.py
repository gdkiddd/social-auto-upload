# -*- coding: utf-8 -*-
"""
标题处理工具
用于去除视频标题开头的序号
"""

import re


def remove_serial_number(title):
    """
    去除标题开头的序号

    支持的格式：
    - 1) 标题
    - 2) 标题
    - 10) 标题
    - 数字) 标题
    - 数字.标题
    - 数字 ) 标题

    Args:
        title: 原始标题

    Returns:
        str: 去除序号后的标题
    """
    if not title:
        return title

    # 尝试匹配并去除序号
    # 格式1: "数字) 标题" 或 "数字.标题"
    match = re.match(r'^(\d+)[\.\s]*\)?[\)\.s]*\)?([\s\S].*?)$', title)
    if match:
        return match.group(2).strip()  # 返回序号后的部分

    # 格式2: "数字)标题"
    match = re.match(r'^(\d+)[\.\s]*[\)\.s]*\)?([\s\S].*?)$', title)
    if match:
        return match.group(2).strip()

    # 格式3: "数字）标题"
    match = re.match(r'^(\d+)[\.\s]*[\)\.s]*\)（([\s\S].*?）', title)
    if match:
        return match.group(2).strip()

    # 格式4: "数字.标题"
    # 这个情况比较复杂，直接按第一个括号或空格分割
    if ')' in title:
        parts = title.split(')', 1)
        if len(parts) > 1:
            # 找到最后一部分（应该是纯标题）
            last_part = parts[-1].strip()
            # 如果最后一部分以空格开头，去除空格
            return last_part.lstrip()

    # 如果没有括号，尝试按空格分割
    if ' ' in title:
        parts = title.split()
        if len(parts) > 1:
            # 返回空格后的部分
            return parts[-1].strip()

    # 如果都没匹配到，返回原标题
    return title


def extract_title_from_filename(filename):
    """
    从文件名中提取标题并去除序号

    Args:
        filename: 文件名（带或不带扩展名）

    Returns:
        str: 清理后的标题
    """
    # 去除扩展名
    from pathlib import Path
    name = Path(filename).stem

    # 去除序号
    clean_title = remove_serial_number(name)

    return clean_title
