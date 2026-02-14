#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无人值守自动上传脚本
功能：
1. 从 videos/demo/Amy/ 按序号复制下一个视频文件夹到 videos/
2. 选中 Amy 账户
3. 执行全部平台上传功能（支持断点续传）
4. 记录每个平台的上传状态，支持跳过已成功的平台
5. 上传成功后更新 latest.json 记录
6. 输出详细日志
7. 完成后发送 bark 通知
"""

import os
import sys
import json
import shutil
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# 切换到脚本所在目录
SCRIPT_DIR = Path(__file__).parent.resolve()
os.chdir(SCRIPT_DIR)

# 现在导入模块
from conf import is_platform_enabled, get_bark_url
from myUtils.account_manager import (
    get_accounts, set_current_account, get_current_account,
    check_account_cookie_exists
)
from myUtils.video_project import (
    load_uploading_info,
    save_uploading_info,
    clear_uploading_info,
    get_next_video_folder,
)

# 配置
ACCOUNT_NAME = "Amy"
SOURCE_DIR = SCRIPT_DIR / "videos" / ACCOUNT_NAME  # videos 目录下按账号组织
TARGET_DIR = SCRIPT_DIR / "videos"
UPLOADING_JSON_FILE = TARGET_DIR / "uploading.json"  # 记录当前正在上传的视频路径
HISTORY_JSON_FILE = TARGET_DIR / "history.json"  # 记录上传历史
UPLOAD_STATUS_FILE = SOURCE_DIR / "video_upload_status.json"  # 记录每个视频的上传状态

# 平台列表（与 run.py 保持一致）
PLATFORMS = [
    {'id': 'xiaohongshu', 'name': '小红书'},
    {'id': 'bilibili', 'name': 'Bilibili'},
    {'id': 'kuaishou', 'name': '快手'},
    {'id': 'douyin', 'name': '抖音'},
    {'id': 'tencent', 'name': '视频号'},
    {'id': 'baijiahao', 'name': '百家号'}
]

# 上传脚本映射
UPLOAD_SCRIPTS = {
    'xiaohongshu': 'examples/upload_video_to_xiaohongshu.py',
    'bilibili': 'examples/upload_video_to_bilibili.py',
    'kuaishou': 'examples/upload_video_to_kuaishou.py',
    'baijiahao': 'examples/upload_video_to_baijiahao.py',
    'douyin': 'examples/upload_video_to_douyin.py',
    'tencent': 'examples/upload_video_to_tencent.py'
}


class Logger:
    """日志输出类"""
    def __init__(self):
        self.logs = []
        self.start_time = datetime.now()

    def log(self, message, level="INFO"):
        """输出日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"
        print(log_line)
        self.logs.append(log_line)

    def info(self, message):
        self.log(message, "INFO")

    def success(self, message):
        self.log(f"✅ {message}", "SUCCESS")

    def warning(self, message):
        self.log(f"⚠️  {message}", "WARNING")

    def error(self, message):
        self.log(f"❌ {message}", "ERROR")

    def divider(self):
        """输出分隔线"""
        print("=" * 60)


def send_bark_notification(title, content, logger):
    """发送 Bark 通知"""
    try:
        from urllib.parse import quote

        bark_url = get_bark_url()
        if not bark_url:
            logger.warning("未配置Bark URL，跳过通知")
            return

        # URL 编码标题和内容
        encoded_title = quote(title)
        encoded_content = quote(content, safe='')

        url = f"{bark_url}/{encoded_title}/{encoded_content}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.success("Bark 通知发送成功")
        else:
            logger.warning(f"Bark 通知发送失败: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Bark 通知发送异常: {e}")


def load_upload_status(logger):
    """加载视频上传状态

    Returns:
        dict: 上传状态字典，格式：{video_folder_name: {platform_id: status}}
    """
    if not UPLOAD_STATUS_FILE.exists():
        logger.info("未找到上传状态文件，创建新的状态记录")
        return {}

    try:
        with open(UPLOAD_STATUS_FILE, 'r', encoding='utf-8') as f:
            status = json.load(f)
            logger.info(f"读取上传状态文件成功")
            return status
    except Exception as e:
        logger.warning(f"读取上传状态文件失败: {e}，将创建新的状态记录")
        return {}


def save_upload_status(status, logger):
    """保存视频上传状态

    Args:
        status: 上传状态字典
    """
    try:
        with open(UPLOAD_STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        logger.success("上传状态已保存")
    except Exception as e:
        logger.error(f"保存上传状态失败: {e}")


def get_video_upload_status(video_folder_name, logger):
    """获取指定视频的上传状态

    Args:
        video_folder_name: 视频文件夹名称

    Returns:
        dict: 该视频的上传状态，格式：{platform_id: status}
    """
    status = load_upload_status(logger)
    return status.get(video_folder_name, {})


def update_video_upload_status(video_folder_name, platform_id, platform_name, upload_result, logger):
    """更新指定视频的上传状态

    Args:
        video_folder_name: 视频文件夹名称
        platform_id: 平台ID
        platform_name: 平台名称
        upload_result: 上传结果（成功/失败/跳过）
    """
    status = load_upload_status(logger)

    if video_folder_name not in status:
        status[video_folder_name] = {}

    status[video_folder_name][platform_id] = {
        'platform_name': platform_name,
        'status': upload_result,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    save_upload_status(status, logger)


def is_platform_uploaded(video_folder_name, platform_id, logger):
    """检查指定视频的指定平台是否已成功上传

    Args:
        video_folder_name: 视频文件夹名称
        platform_id: 平台ID

    Returns:
        bool: True 表示已成功上传，False 表示未上传或上传失败
    """
    video_status = get_video_upload_status(video_folder_name, logger)
    platform_status = video_status.get(platform_id, {})

    if platform_status.get('status') == '成功':
        return True

    return False


def load_upload_history(logger):
    """加载上传历史记录

    Returns:
        list: 历史记录列表
    """
    if not HISTORY_JSON_FILE.exists():
        logger.info("未找到上传历史文件，创建新的历史记录")
        return []

    try:
        with open(HISTORY_JSON_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
            logger.info(f"读取上传历史: 共 {len(history)} 条记录")
            return history
    except Exception as e:
        logger.warning(f"读取上传历史失败: {e}，将创建新的历史记录")
        return []


def save_upload_history(history, logger):
    """保存上传历史记录

    Args:
        history: 历史记录列表
    """
    try:
        with open(HISTORY_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        logger.success(f"上传历史已保存")
    except Exception as e:
        logger.error(f"保存上传历史失败: {e}")


def add_upload_history(folder_name, upload_results, logger):
    """添加一条上传历史记录

    Args:
        folder_name: 视频文件夹名称
        upload_results: 上传结果字典 {platform_name: status}
    """
    history = load_upload_history(logger)

    # 统计结果
    success_count = 0
    failed_count = 0

    for platform_name, status in upload_results.items():
        if status == "成功":
            success_count += 1
        elif status == "失败":
            failed_count += 1

    total_platforms = success_count + failed_count

    # 判断总体结果：只要有失败就是 fail，全部成功才是 success
    result = "fail" if failed_count > 0 else "success"

    # 创建历史记录
    record = {
        "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "account": ACCOUNT_NAME,
        "video": folder_name,
        "platforms": total_platforms,
        "result": result,
        "details": upload_results
    }

    # 添加到历史开头
    history.insert(0, record)

    # 只保留最近 100 条记录
    history = history[:100]

    # 保存历史
    save_upload_history(history, logger)

    logger.success(f"已添加上传历史: {folder_name} - {result}")


def switch_account(account_name, logger):
    """切换到指定账号"""
    current_account = get_current_account()
    logger.info(f"当前账号: {current_account}")

    if current_account == account_name:
        logger.success(f"已经是账号: {account_name}")
        return True

    # 检查账号是否存在
    accounts = get_accounts()
    if account_name not in accounts:
        logger.error(f"账号不存在: {account_name}")
        logger.info(f"可用账号: {', '.join(accounts)}")
        return False

    # 切换账号
    logger.info(f"切换到账号: {account_name}")
    if set_current_account(account_name):
        logger.success(f"账号切换成功: {account_name}")
        return True
    else:
        logger.error(f"账号切换失败: {account_name}")
        return False


def check_cookies(account_name, logger):
    """检查账号的 cookie 文件"""
    logger.divider()
    logger.info("检查 Cookie 状态")

    missing_cookies = []
    for platform in PLATFORMS:
        platform_id = platform['id']
        platform_name = platform['name']

        if check_account_cookie_exists(account_name, platform_id):
            logger.success(f"{platform_name}: Cookie 已就绪")
        else:
            logger.warning(f"{platform_name}: Cookie 缺失")
            missing_cookies.append(platform_name)

    if missing_cookies:
        logger.warning(f"以下平台缺少 Cookie: {', '.join(missing_cookies)}")
        return False
    else:
        logger.success("所有平台 Cookie 都已就绪")
        return True


def run_upload(platform_id, platform_name, video_folder_name, logger):
    """执行单个平台的上传

    Args:
        platform_id: 平台ID
        platform_name: 平台名称
        video_folder_name: 视频文件夹名称
        logger: 日志对象
    """
    # 检查是否已成功上传
    if is_platform_uploaded(video_folder_name, platform_id, logger):
        logger.info(f"✅ {platform_name} 已上传成功，跳过")
        return '跳过'

    logger.divider()
    logger.info(f"开始上传到 {platform_name}")

    script_path = UPLOAD_SCRIPTS.get(platform_id)
    if not script_path:
        logger.error(f"未找到 {platform_name} 的上传脚本")
        return '失败'

    script_file = SCRIPT_DIR / script_path
    if not script_file.exists():
        logger.error(f"脚本文件不存在: {script_file}")
        return '失败'

    try:
        # 执行上传脚本（实时显示输出）
        print()  # 空行分隔
        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=SCRIPT_DIR,
            timeout=600  # 10分钟超时
        )

        upload_result = '成功' if result.returncode == 0 else '失败'

        # 更新上传状态
        update_video_upload_status(video_folder_name, platform_id, platform_name, upload_result, logger)

        if result.returncode == 0:
            logger.success(f"{platform_name} 上传成功")
            return '成功'
        else:
            logger.error(f"{platform_name} 上传失败 (退出码: {result.returncode})")
            return '失败'

    except subprocess.TimeoutExpired:
        logger.error(f"{platform_name} 上传超时（10分钟）")
        # 更新上传状态为失败
        update_video_upload_status(video_folder_name, platform_id, platform_name, '失败', logger)
        return '失败'
    except Exception as e:
        logger.error(f"{platform_name} 上传异常: {e}")
        # 更新上传状态为失败
        update_video_upload_status(video_folder_name, platform_id, platform_name, '失败', logger)
        return '失败'


def main():
    """主函数"""
    logger = Logger()
    logger.divider()
    logger.info("🚀 无人值守自动上传脚本启动")
    logger.info(f"开始时间: {logger.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. 检查是否有正在上传的视频
        logger.divider()
        logger.info("步骤 1: 检查上传状态")
        uploading_info = load_uploading_info(uploading_json=UPLOADING_JSON_FILE, logger=logger)

        if uploading_info:
            # 继续上传之前的视频
            folder_number = uploading_info['folder_number']
            folder_name = uploading_info['folder_name']
            folder_path = Path(uploading_info['folder_path'])
            logger.info(f"继续上传视频: 序号 {folder_number} - {folder_name}")
            logger.info(f"视频路径: {folder_path}")
        else:
            # 获取下一个待上传的视频
            logger.info("获取下一个待上传视频")
            folder_number, folder_path = get_next_video_folder(SOURCE_DIR, logger=logger)
            if not folder_path:
                send_bark_notification("自动上传结束", "所有视频已上传完成", logger)
                return

            folder_name = folder_path.name
            logger.success(f"选择视频: 序号 {folder_number} - {folder_name}")

            # 保存到 uploading.json
            save_uploading_info(
                folder_number,
                folder_name,
                folder_path,
                uploading_json=UPLOADING_JSON_FILE,
                logger=logger
            )

        # 2. 切换到 Amy 账户
        logger.divider()
        logger.info("步骤 2: 切换账户")
        if not switch_account(ACCOUNT_NAME, logger):
            send_bark_notification("自动上传失败", f"切换账户失败: {ACCOUNT_NAME}", logger)
            return

        # 3. 检查 Cookie
        logger.divider()
        logger.info("步骤 3: 检查 Cookie")
        if not check_cookies(ACCOUNT_NAME, logger):
            send_bark_notification("自动上传失败", "Cookie 不完整，请先登录", logger)
            return

        # 4. 执行上传
        logger.divider()
        logger.info("步骤 4: 执行平台上传")
        logger.info(f"视频路径: {folder_path}")

        upload_results = {}
        for platform in PLATFORMS:
            platform_id = platform['id']
            platform_name = platform['name']

            # 检查平台是否启用
            if not is_platform_enabled(platform_id):
                logger.warning(f"{platform_name} 已禁用，跳过")
                upload_results[platform_name] = "跳过"
                continue

            # 执行上传
            result = run_upload(platform_id, platform_name, folder_name, logger)
            upload_results[platform_name] = result

        # 5. 生成总结报告
        logger.divider()
        logger.info("📊 上传结果汇总")

        success_count = sum(1 for v in upload_results.values() if v == "成功")
        failed_count = sum(1 for v in upload_results.values() if v == "失败")
        skipped_count = sum(1 for v in upload_results.values() if v == "跳过")

        for platform_name, result in upload_results.items():
            icon = "✅" if result == "成功" else "❌" if result == "失败" else "⏭️ "
            logger.info(f"  {icon} {platform_name}: {result}")

        logger.divider()
        logger.info(f"总计: 成功 {success_count} | 失败 {failed_count} | 跳过 {skipped_count}")

        # 6. 添加上传历史记录
        add_upload_history(folder_name, upload_results, logger)

        # 7. 检查是否所有平台都成功
        video_status = get_video_upload_status(folder_name, logger)
        enabled_platforms = [p for p in PLATFORMS if is_platform_enabled(p['id'])]
        total_enabled = len(enabled_platforms)
        uploaded_platforms = sum(1 for p in enabled_platforms
                                if video_status.get(p['id'], {}).get('status') == '成功')

        logger.info(f"上传进度: {uploaded_platforms}/{total_enabled} 个平台已成功")

        # 8. 发送 Bark 通知
        end_time = datetime.now()
        duration = (end_time - logger.start_time).total_seconds()

        # 构建详细的上传结果列表
        platform_details = []
        for platform_name, result in upload_results.items():
            icon = "✅" if result == "成功" else "❌" if result == "失败" else "⏭️ "
            platform_details.append(f"{icon} {platform_name}: {result}")

        platform_list = "\n".join(platform_details)

        # 根据进度决定标题和内容
        if uploaded_platforms >= total_enabled:
            title = "✅ 自动上传完成"
            status_summary = f"所有平台上传成功 ({uploaded_platforms}/{total_enabled})"

            # 尝试获取下一个视频，更新 uploading.json
            next_number, next_folder = get_next_video_folder(
                SOURCE_DIR, current_number=folder_number, logger=logger
            )
            if next_folder:
                save_uploading_info(
                    next_number,
                    next_folder.name,
                    next_folder,
                    uploading_json=UPLOADING_JSON_FILE,
                    logger=logger
                )
                logger.info(f"✅ 已准备下一个视频: 序号 {next_number} - {next_folder.name}")
            else:
                # 没有下一个视频了，删除 uploading.json
                clear_uploading_info(uploading_json=UPLOADING_JSON_FILE, logger=logger)
                logger.success("✅ 所有视频已上传完成")
        else:
            title = "⚠️ 自动上传部分完成"
            status_summary = f"进度: {uploaded_platforms}/{total_enabled} 个平台成功"
            remaining = total_enabled - uploaded_platforms
            status_summary += f"\n再次运行将自动上传剩余 {remaining} 个平台"

        content = f"""序号: {folder_number}
视频: {folder_name}
{status_summary}
本次: 成功 {success_count} | 失败 {failed_count} | 跳过 {skipped_count}
耗时: {int(duration)}秒

{platform_list}"""

        logger.divider()
        send_bark_notification(title, content, logger)

        if uploaded_platforms >= total_enabled:
            logger.success(f"✅ 所有任务完成！总耗时: {int(duration)}秒")
        else:
            logger.info(f"⚠️  部分任务完成，再次运行将自动继续")

        logger.divider()

    except Exception as e:
        logger.error(f"脚本执行异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        send_bark_notification("自动上传异常", str(e), logger)


if __name__ == "__main__":
    main()
