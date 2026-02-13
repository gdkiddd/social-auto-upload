# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path.cwd()))

from myUtils.upload_history import get_upload_history

print("=" * 60)
print("📊 上传历史记录")
print("=" * 60)

upload_history = get_upload_history()
records = upload_history.get_latest_records(limit=10)

if not records:
    print("\n暂无上传历史记录")
else:
    print(f"\n共 {len(records)} 条上传记录\n")

    for i, record in enumerate(records[:5], 1):
        result_icon = "✅" if record['result'] == 'success' else "❌"
        print(f"\n[{i}] {result_icon} {record['date']}")
        print(f"    账号: {record['account']}")
        print(f"    视频: {record['video'][:30]}...")
        print(f"    平台: {record['platforms']} 个")
        print(f"    结果: {record['result']}")

print("\n" + "=" * 60)
