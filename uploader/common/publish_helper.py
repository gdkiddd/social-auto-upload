# -*- coding: utf-8 -*-
"""
发布历史记录工具
"""

from pathlib import Path
from myUtils.account_manager import get_current_account
from myUtils.publish_history import get_publish_history


def record_publish_history(platform_id: str, platform_name: str, video_file_path: str,
                          status: str = 'success', error_msg: str = None):
    """
    记录发布历史

    Args:
        platform_id: 平台ID (如 'xiaohongshu', 'douyin' 等)
        platform_name: 平台中文名 (如 '小红书', '抖音' 等)
        video_file_path: 视频文件路径
        status: 发布状态 ('success' 或 'failed')
        error_msg: 错误信息（如果失败）
    """
    try:
        publish_history = get_publish_history()
        current_account = get_current_account()

        publish_history.add_record(
            platform_id=platform_id,
            platform_name=platform_name,
            video_file=Path(video_file_path).name,
            status=status,
            account=current_account,
            error_msg=error_msg
        )
    except Exception as e:
        # 记录发布历史失败不应该影响主流程
        print(f"记录发布历史失败: {e}")
