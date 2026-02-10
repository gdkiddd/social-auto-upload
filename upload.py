#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单平台视频上传工具
用法: python upload.py <平台> <账号名>

示例:
    python upload.py tencent Amy       # 上传Amy的最新视频到视频号
    python upload.py douyin Amy        # 上传Amy的最新视频到抖音
    python upload.py bilibili Amy      # 上传Amy的最新视频到B站
    python upload.py xiaohongshu Amy   # 上传Amy的最新视频到小红书
    python upload.py kuaishou Amy      # 上传Amy的最新视频到快手
    python upload.py baijiahao Amy     # 上传Amy的最新视频到百家号

支持的账号参数:
    - 账号名        指定账号名的最新视频
    - all           所有账号的最新视频（不推荐，会按顺序上传）

上传完成后会发送Bark通知结果
"""

import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
import requests
from urllib.parse import quote

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from conf import BASE_DIR, load_config, get_bark_url
from myUtils.account_manager import get_accounts, set_current_account
from myUtils.video_project import get_video_project_files
from utils.log import logger


# 平台配置
PLATFORMS = {
    'tencent': {
        'name': '视频号',
        'script': 'examples/upload_video_to_tencent.py'
    },
    'douyin': {
        'name': '抖音',
        'script': 'examples/upload_video_to_douyin.py'
    },
    'bilibili': {
        'name': 'B站',
        'script': 'examples/upload_video_to_bilibili.py'
    },
    'xiaohongshu': {
        'name': '小红书',
        'script': 'examples/upload_video_to_xiaohongshu.py'
    },
    'kuaishou': {
        'name': '快手',
        'script': 'examples/upload_video_to_kuaishou.py'
    },
    'baijiahao': {
        'name': '百家号',
        'script': 'examples/upload_video_to_baijiahao.py'
    },
}


def send_bark_notification(title, content, is_success=True):
    """发送 Bark 通知"""
    try:
        bark_url = get_bark_url()
        if not bark_url:
            logger.warning("未配置Bark URL，跳过通知")
            return

        # 添加图标
        icon = "🎉" if is_success else "❌"

        # URL 编码标题和内容
        encoded_title = quote(f"{icon} {title}")
        encoded_content = quote(content, safe='')

        url = f"{bark_url}/{encoded_title}/{encoded_content}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.success("Bark 通知发送成功")
        else:
            logger.warning(f"Bark 通知发送失败: HTTP {response.status_code}")
    except Exception as e:
        logger.warning(f"Bark 通知发送异常: {e}")


def upload_to_platform(platform, account_name):
    """
    上传视频到指定平台

    Args:
        platform: 平台名称 (tencent, douyin, bilibili, etc.)
        account_name: 账号名称

    Returns:
        tuple: (success: bool, message: str, video_names: list)
    """
    if platform not in PLATFORMS:
        return False, f"不支持的平台: {platform}", []

    platform_config = PLATFORMS[platform]
    platform_name = platform_config['name']
    script_path = PROJECT_ROOT / platform_config['script']

    if not script_path.exists():
        return False, f"上传脚本不存在: {script_path}", []

    # 获取视频文件信息
    project_dir, video_files = get_video_project_files(exit_on_error=False)
    if not video_files:
        return False, "没有找到视频文件", []

    # 提取视频文件名（不含扩展名）
    video_names = [f.stem for f in video_files]

    logger.info(f"{'='*50}")
    logger.info(f"📱 平台: {platform_name}")
    logger.info(f"👤 账号: {account_name}")
    logger.info(f"🎬 视频: {', '.join(video_names)}")
    logger.info(f"{'='*50}")

    # 检查账号是否存在
    accounts = get_accounts()
    if account_name != 'all' and account_name not in accounts:
        return False, f"账号 '{account_name}' 不存在，可用账号: {', '.join(accounts)}", video_names

    # 获取要上传的账号列表
    if account_name == 'all':
        upload_accounts = accounts
        logger.warning(f"⚠️  将依次上传所有账号的视频，这可能需要较长时间...")
    else:
        upload_accounts = [account_name]

    results = []
    start_time = datetime.now()

    for acc in upload_accounts:
        logger.info(f"\n{'#'*50}")
        logger.info(f"🔄 正在上传账号: {acc}")
        logger.info(f"{'#'*50}\n")

        # 设置当前账号
        set_current_account(acc)

        # 执行上传脚本
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            # 打印输出
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            # 检查退出码
            if result.returncode == 0:
                results.append((acc, True, "上传成功"))
                logger.success(f"✅ 账号 '{acc}' 上传成功")
            else:
                results.append((acc, False, f"上传失败 (退出码: {result.returncode})"))
                logger.error(f"❌ 账号 '{acc}' 上传失败")

        except subprocess.TimeoutExpired:
            results.append((acc, False, "上传超时（超过1小时）"))
            logger.error(f"❌ 账号 '{acc}' 上传超时")
        except Exception as e:
            results.append((acc, False, f"上传出错: {e}"))
            logger.error(f"❌ 账号 '{acc}' 上传出错: {e}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 汇总结果
    total_accounts = len(upload_accounts)
    success_accounts = sum(1 for _, success, _ in results if success)
    failed_accounts = total_accounts - success_accounts

    logger.info(f"\n{'='*50}")
    logger.info(f"📊 上传结果汇总")
    logger.info(f"{'='*50}")

    for acc, success, msg in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {acc}: {msg}")

    logger.info(f"\n总计: {success_accounts}/{total_accounts} 个账号上传成功")

    if success_accounts == total_accounts:
        return True, f"所有账号上传成功 ({success_accounts}/{total_accounts})", video_names
    elif success_accounts > 0:
        return True, f"部分账号上传成功 ({success_accounts}/{total_accounts})", video_names
    else:
        return False, f"所有账号上传失败 (0/{total_accounts})", video_names


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='单平台视频上传工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python upload.py tencent Amy       # 上传Amy的最新视频到视频号
  python upload.py douyin Amy        # 上传Amy的最新视频到抖音
  python upload.py bilibili Amy      # 上传Amy的最新视频到B站
  python upload.py xiaohongshu Amy   # 上传Amy的最新视频到小红书
  python upload.py kuaishou Amy      # 上传Amy的最新视频到快手
  python upload.py baijiahao Amy     # 上传Amy的最新视频到百家号

支持的账号参数:
  账号名        指定账号名的最新视频
  all           所有账号的最新视频

支持的平台:
  tencent       视频号
  douyin        抖音
  bilibili      B站
  xiaohongshu   小红书
  kuaishou      快手
  baijiahao     百家号
        """
    )

    parser.add_argument('platform', help='平台名称 (tencent, douyin, bilibili, xiaohongshu, kuaishou, baijiahao)')
    parser.add_argument('account', help='账号名称 (或使用 "all" 上传所有账号)')

    args = parser.parse_args()

    platform = args.platform.lower()
    account_name = args.account

    # 执行上传
    start_time = datetime.now()
    success, message, video_names = upload_to_platform(platform, account_name)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 发送Bark通知
    platform_name = PLATFORMS.get(platform, {}).get('name', platform)
    title = f"{platform_name}上传结果"

    duration_str = f"{int(duration // 60)}分{int(duration % 60)}秒" if duration > 60 else f"{int(duration)}秒"

    # 构建视频名称字符串
    if video_names:
        if len(video_names) <= 3:
            video_str = ', '.join(video_names)
        else:
            video_str = ', '.join(video_names[:3]) + f' 等{len(video_names)}个视频'
    else:
        video_str = '无'

    content = f"{message}\n视频: {video_str}\n耗时: {duration_str}\n账号: {account_name}"

    send_bark_notification(title, content, is_success=success)

    # 退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
