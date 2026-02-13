# -*- coding: utf-8 -*-
"""
发布历史记录工具（已废弃）
统一使用 myUtils.upload_history
"""

from pathlib import Path
from myUtils.account_manager import get_current_account
from myUtils.upload_history import get_upload_history


def record_publish_history(platform_id: str, platform_name: str, video_file_path: str,
                          status: str = 'success', error_message: str = None):
    """
    记录发布历史（已废弃，仅保留向后兼容）

    此函数现在将单平台记录转换为新的多平台记录格式
    """
    try:
        upload_history = get_upload_history()
        current_account = get_current_account()
        video_name = Path(video_file_path).name

        # 构建上传结果字典
        # 如果是第一次记录，需要合并之前可能已记录的其他平台
        # 这里简化处理：每次只记录当前平台
        upload_results = {
            platform_id: "成功" if status == "success" else "失败"
        }

        # 添加记录
        upload_history.add_record(
            folder_name=video_name,
            upload_results=upload_results,
            account=current_account
        )
    except Exception as e:
        # 记录发布历史失败不应该影响主流程
        print(f"记录发布历史失败: {e}")
