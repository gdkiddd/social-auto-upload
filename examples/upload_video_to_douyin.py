import sys
import asyncio
from pathlib import Path

# 添加项目根目录到 Python 路径,解决从其他目录运行脚本时的模块导入问题
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conf import BASE_DIR
from myUtils.account_manager import get_current_account, get_account_cookie_path
from myUtils.video_project import get_video_project_files
from uploader.douyin_uploader.main import douyin_setup, DouYinVideo
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags


if __name__ == '__main__':
    from conf import load_config

    current_account = get_current_account()
    account_file = get_account_cookie_path(current_account, 'douyin')

    # 读取配置
    config = load_config()
    schedule_time = config.get('schedule_time', None)

    if schedule_time:
        print(f"⏰ 定时发布模式: {schedule_time}")
        # 定时发布
        from datetime import datetime
        schedule_dt = datetime.strptime(schedule_time, '%Y-%m-%d %H:%M')
        publish_datetimes = [schedule_dt]  # 所有视频使用同一时间
    else:
        print("⏰ 立即发布模式")
        publish_datetimes = [0]  # 0 表示立即发布

    # 获取视频项目文件（使用通用函数）
    project_dir, files = get_video_project_files()

    cookie_setup = asyncio.run(douyin_setup(account_file, handle=False))
    for index, file in enumerate(files):
        title, tags = get_title_and_hashtags(str(file))
        thumbnail_path = file.with_suffix('.png')
        # 打印视频文件名、标题和 hashtag
        print(f"视频文件名：{file}")
        print(f"标题：{title}")
        print(f"Hashtag：{tags}")
        # 暂时没有时间修复封面上传，故先隐藏掉该功能
        # if thumbnail_path.exists():
            # app = DouYinVideo(title, file, tags, publish_datetimes[index], account_file, thumbnail_path=thumbnail_path)
        # else:
        app = DouYinVideo(title, file, tags, publish_datetimes[index], account_file)
        asyncio.run(app.main(), debug=False)
