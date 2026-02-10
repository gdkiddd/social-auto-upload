#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站上传快捷工具
用法: python upload_bilibili.py <账号名>

示例:
    python upload_bilibili.py Amy    # 上传Amy的最新视频到B站
    python upload_bilibili.py all    # 上传所有账号的最新视频到B站
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入主上传模块
if __name__ == '__main__':
    # 设置平台为 bilibili
    sys.argv = ['upload.py', 'bilibili'] + (sys.argv[1:] if len(sys.argv) > 1 else [''])

    # 导入并运行主模块
    import upload
    upload.main()
