import asyncio
from pathlib import Path

from conf import BASE_DIR
from myUtils.account_manager import get_current_account, get_account_cookie_path
from uploader.ks_uploader.main import ks_setup, KSVideo
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags


if __name__ == '__main__':
    from conf import load_config

    filepath = Path(BASE_DIR) / "videos"
    current_account = get_current_account()
    account_file = get_account_cookie_path(current_account, 'kuaishou')

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

    # 获取视频目录
    folder_path = Path(filepath)
    # 获取文件夹中的所有文件
    files = list(folder_path.glob("*.mp4"))
    file_num = len(files)

    cookie_setup = asyncio.run(ks_setup(account_file, handle=False))
    for index, file in enumerate(files):
        title, tags = get_title_and_hashtags(str(file))
        # 打印视频文件名、标题和 hashtag
        print(f"视频文件名：{file}")
        print(f"标题：{title}")
        print(f"Hashtag：{tags}")
        app = KSVideo(title, file, tags, publish_datetimes[index], account_file)
        asyncio.run(app.main(), debug=False)
