# -*- coding: utf-8 -*-
"""
发布历史记录模块
记录和管理各平台的发布历史
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from conf import BASE_DIR


class PublishHistory:
    """发布历史管理类"""

    def __init__(self):
        self.history_file = BASE_DIR / "data" / "publish_history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_history_file()

    def _ensure_history_file(self):
        """确保历史记录文件存在"""
        if not self.history_file.exists():
            self._save_history([])

    def _load_history(self) -> List[Dict]:
        """加载发布历史"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _save_history(self, history: List[Dict]):
        """保存发布历史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def add_record(self, platform_id: str, platform_name: str, video_file: str,
                  status: str, account: str, error_message: str = None):
        """
        添加一条发布记录

        Args:
            platform_id: 平台ID
            platform_name: 平台名称
            video_file: 视频文件名
            status: 状态 (success/failed)
            account: 账号名称
            error_message: 错误信息（可选）
        """
        history = self._load_history()

        record = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "platform_id": platform_id,
            "platform_name": platform_name,
            "video_file": video_file,
            "status": status,
            "account": account,
            "error_message": error_message
        }

        # 添加到历史记录开头
        history.insert(0, record)

        # 只保留最近 100 条记录
        history = history[:100]

        self._save_history(history)

    def get_latest_records(self, platform_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        获取最近的发布记录

        Args:
            platform_id: 平台ID（可选，为 None 则返回所有平台）
            limit: 返回记录数量

        Returns:
            发布记录列表
        """
        history = self._load_history()

        if platform_id:
            history = [r for r in history if r['platform_id'] == platform_id]

        return history[:limit]

    def get_latest_by_platform(self) -> Dict[str, Optional[Dict]]:
        """
        获取每个平台的最新发布记录

        Returns:
            字典，key 为 platform_id，value 为最新记录（不存在则为 None）
        """
        history = self._load_history()
        latest_by_platform = {}

        for record in history:
            platform_id = record['platform_id']
            if platform_id not in latest_by_platform:
                latest_by_platform[platform_id] = record

        # 确保所有平台都有记录（即使是 None）
        all_platforms = ['xiaohongshu', 'tencent', 'bilibili', 'douyin', 'kuaishou', 'baijiahao']
        for platform_id in all_platforms:
            if platform_id not in latest_by_platform:
                latest_by_platform[platform_id] = None

        return latest_by_platform

    def display_records(self, records: List[Dict]):
        """
        格式化显示发布记录

        Args:
            records: 发布记录列表
        """
        if not records:
            print("  暂无发布记录")
            return

        for i, record in enumerate(records, 1):
            status_icon = "✅" if record['status'] == 'success' else "❌"
            status_text = "成功" if record['status'] == 'success' else "失败"

            print(f"  [{i}] {record['platform_name']} - {status_icon} {status_text}")
            print(f"      视频: {record['video_file']}")
            print(f"      时间: {record['timestamp']}")
            print(f"      账号: {record['account']}")

            if record['error_message']:
                print(f"      错误: {record['error_message']}")

            print()

    def display_latest_by_platform(self):
        """显示每个平台的最新发布记录"""
        print("\n" + "=" * 60)
        print("📊 各平台最新发布记录")
        print("=" * 60)

        latest_by_platform = self.get_latest_by_platform()

        platform_names = {
            'xiaohongshu': '小红书',
            'tencent': '视频号',
            'bilibili': 'Bilibili',
            'douyin': '抖音',
            'kuaishou': '快手',
            'baijiahao': '百家号'
        }

        for platform_id in ['xiaohongshu', 'tencent', 'bilibili', 'douyin', 'kuaishou', 'baijiahao']:
            record = latest_by_platform.get(platform_id)
            platform_name = platform_names.get(platform_id, platform_id)

            if record:
                status_icon = "✅" if record['status'] == 'success' else "❌"
                status_text = "成功" if record['status'] == 'success' else "失败"
                print(f"{status_icon} {platform_name:10s} - {status_text}")
                print(f"   视频: {record['video_file']}")
                print(f"   时间: {record['timestamp']}")
            else:
                print(f"⊘ {platform_name:10s} - 未发布")

            print()


# 全局实例
_publish_history = None


def get_publish_history() -> PublishHistory:
    """获取发布历史记录实例（单例模式）"""
    global _publish_history
    if _publish_history is None:
        _publish_history = PublishHistory()
    return _publish_history
