#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无人值守自动上传脚本
功能：
1. 从 videos/demo/Amy/ 按序号复制下一个视频文件夹到 videos/
2. 选中 Amy 账户
3. 执行全部平台上传功能
4. 上传成功后更新 latest.json 记录
5. 输出详细日志
6. 完成后发送 bark 通知
"""

import os
import sys
import json
import shutil
import subprocess
import requests
import re
from datetime import datetime
from pathlib import Path

# 切换到脚本所在目录
SCRIPT_DIR = Path(__file__).parent.resolve()
os.chdir(SCRIPT_DIR)

# 现在导入模块
from conf import load_config, save_config, is_platform_enabled
from myUtils.account_manager import (
    get_accounts, set_current_account, get_current_account,
    check_account_cookie_exists, get_account_cookie_path
)

# 配置
BARK_URL = "https://api.day.app/uuAAL4HgGCDWZVy5NHA9ZR"
ACCOUNT_NAME = "Amy"
SOURCE_DIR = SCRIPT_DIR / "videos" / "demo" / ACCOUNT_NAME  # demo 目录下按账号组织
TARGET_DIR = SCRIPT_DIR / "videos"
LATEST_JSON_FILE = SOURCE_DIR / "latest.json"  # 记录最新上传的视频序号

# 平台列表（与 run.py 保持一致）
PLATFORMS = [
    {'id': 'xiaohongshu', 'name': '小红书'},
    {'id': 'bilibili', 'name': 'Bilibili'},
    {'id': 'kuaishou', 'name': '快手'},
    {'id': 'baijiahao', 'name': '百家号'},
    {'id': 'douyin', 'name': '抖音'},
    {'id': 'tencent', 'name': '视频号'}
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
        url = f"{BARK_URL}/{title}/{content}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            logger.success("Bark 通知发送成功")
        else:
            logger.warning(f"Bark 通知发送失败: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Bark 通知发送异常: {e}")


def extract_folder_number(folder_name):
    """从文件夹名中提取序号

    例如: "1) 跑滴滴..." -> 1
         "10) 36岁..." -> 10
    """
    # 匹配开头的数字序号
    match = re.match(r'^(\d+)\)', folder_name)
    if match:
        return int(match.group(1))
    return None


def load_latest_upload_info(logger):
    """加载最新上传记录

    Returns:
        int: 最新上传的视频序号，如果没有记录则返回 0
    """
    if not LATEST_JSON_FILE.exists():
        logger.info("未找到上传记录文件，将上传第一个视频")
        return 0

    try:
        with open(LATEST_JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            latest_number = data.get('latest_number', 0)
            logger.info(f"读取上传记录: 最新上传序号 = {latest_number}")
            return latest_number
    except Exception as e:
        logger.warning(f"读取上传记录失败: {e}，将上传第一个视频")
        return 0


def save_latest_upload_info(folder_number, folder_name, logger):
    """保存最新上传记录

    Args:
        folder_number: 视频文件夹序号
        folder_name: 视频文件夹名称
    """
    try:
        data = {
            'latest_number': folder_number,
            'folder_name': folder_name,
            'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        with open(LATEST_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.success(f"上传记录已更新: 序号 {folder_number} - {folder_name}")
    except Exception as e:
        logger.error(f"保存上传记录失败: {e}")


def get_next_video_folder(logger):
    """获取下一个待上传的视频文件夹

    Returns:
        Path: 下一个视频文件夹路径，如果没有则返回 None
    """
    logger.info(f"扫描源目录: {SOURCE_DIR}")

    if not SOURCE_DIR.exists():
        logger.error(f"源目录不存在: {SOURCE_DIR}")
        return None

    # 获取所有子文件夹（排除隐藏文件和 latest.json）
    folders = [f for f in SOURCE_DIR.iterdir()
               if f.is_dir() and not f.name.startswith('.')]

    if not folders:
        logger.error("demo 目录下没有找到视频文件夹")
        return None

    # 提取每个文件夹的序号
    folder_numbers = []
    for folder in folders:
        number = extract_folder_number(folder.name)
        if number is not None:
            folder_numbers.append((number, folder))

    if not folder_numbers:
        logger.error("没有找到带序号的视频文件夹（格式：序号) 标题）")
        return None

    # 按序号排序
    folder_numbers.sort(key=lambda x: x[0])

    # 获取最新上传的序号
    latest_number = load_latest_upload_info(logger)

    # 找到下一个序号的文件夹
    for number, folder in folder_numbers:
        if number > latest_number:
            logger.info(f"找到下一个视频: 序号 {number} - {folder.name}")
            logger.info(f"上次上传序号: {latest_number}")
            return number, folder

    logger.warning(f"所有视频都已上传完成（最新序号: {latest_number}）")
    return None, None


def copy_video_folder(source_folder, logger):
    """复制视频文件夹到 videos/ 目录"""
    target_path = TARGET_DIR / source_folder.name

    # 检查目标是否已存在
    if target_path.exists():
        logger.warning(f"目标目录已存在: {target_path}")
        logger.info(f"删除旧目录: {target_path}")
        shutil.rmtree(target_path)

    # 复制文件夹
    logger.info(f"开始复制: {source_folder} -> {target_path}")
    try:
        shutil.copytree(source_folder, target_path)
        logger.success(f"复制完成: {target_path}")

        # 列出复制的文件
        files = list(target_path.glob("*"))
        logger.info(f"共复制 {len(files)} 个文件")
        for file in files:
            logger.info(f"  - {file.name}")

        return target_path
    except Exception as e:
        logger.error(f"复制失败: {e}")
        return None


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


def run_upload(platform_id, platform_name, logger):
    """执行单个平台的上传"""
    logger.divider()
    logger.info(f"开始上传到 {platform_name}")

    script_path = UPLOAD_SCRIPTS.get(platform_id)
    if not script_path:
        logger.error(f"未找到 {platform_name} 的上传脚本")
        return False

    script_file = SCRIPT_DIR / script_path
    if not script_file.exists():
        logger.error(f"脚本文件不存在: {script_file}")
        return False

    try:
        # 执行上传脚本（实时显示输出）
        print()  # 空行分隔
        result = subprocess.run(
            [sys.executable, str(script_file)],
            cwd=SCRIPT_DIR,
            timeout=600  # 10分钟超时
        )

        if result.returncode == 0:
            logger.success(f"{platform_name} 上传成功")
            return True
        else:
            logger.error(f"{platform_name} 上传失败 (退出码: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"{platform_name} 上传超时（10分钟）")
        return False
    except Exception as e:
        logger.error(f"{platform_name} 上传异常: {e}")
        return False


def main():
    """主函数"""
    logger = Logger()
    logger.divider()
    logger.info("🚀 无人值守自动上传脚本启动")
    logger.info(f"开始时间: {logger.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 1. 获取下一个待上传的视频文件夹
        logger.divider()
        logger.info("步骤 1: 获取下一个待上传视频")
        folder_number, video_folder = get_next_video_folder(logger)
        if not video_folder:
            send_bark_notification("自动上传结束", "所有视频已上传完成", logger)
            return

        # 2. 复制到 videos/ 目录
        logger.divider()
        logger.info("步骤 2: 复制视频文件夹")
        target_folder = copy_video_folder(video_folder, logger)
        if not target_folder:
            send_bark_notification("自动上传失败", "复制视频文件夹失败", logger)
            return

        # 3. 切换到 Amy 账户
        logger.divider()
        logger.info("步骤 3: 切换账户")
        if not switch_account(ACCOUNT_NAME, logger):
            send_bark_notification("自动上传失败", f"切换账户失败: {ACCOUNT_NAME}", logger)
            return

        # 4. 检查 Cookie
        if not check_cookies(ACCOUNT_NAME, logger):
            send_bark_notification("自动上传失败", "Cookie 不完整，请先登录", logger)
            return

        # 5. 执行上传
        logger.divider()
        logger.info("步骤 4: 执行平台上传")

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
            success = run_upload(platform_id, platform_name, logger)
            upload_results[platform_name] = "成功" if success else "失败"

        # 6. 生成总结报告
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

        # 7. 更新上传记录（仅当全部成功时）
        if failed_count == 0:
            save_latest_upload_info(folder_number, video_folder.name, logger)

            # 删除 videos/ 目录中的视频文件夹
            try:
                if target_folder.exists():
                    logger.info(f"删除已上传的视频文件夹: {target_folder.name}")
                    shutil.rmtree(target_folder)
                    logger.success(f"已删除: {target_folder}")
                else:
                    logger.warning(f"目标文件夹不存在: {target_folder}")
            except Exception as e:
                logger.error(f"删除视频文件夹失败: {e}")
        else:
            logger.warning("部分平台上传失败，不更新上传记录")

        # 8. 发送 Bark 通知
        end_time = datetime.now()
        duration = (end_time - logger.start_time).total_seconds()

        title = "自动上传完成" if failed_count == 0 else "自动上传部分失败"

        # 构建详细的上传结果列表
        platform_details = []
        for platform_name, result in upload_results.items():
            icon = "✅" if result == "成功" else "❌" if result == "失败" else "⏭️"
            platform_details.append(f"{icon} {platform_name}: {result}")

        platform_list = "\n".join(platform_details)

        content = f"""序号: {folder_number}
视频: {video_folder.name}
总计: 成功 {success_count} | 失败 {failed_count} | 跳过 {skipped_count}
耗时: {int(duration)}秒

{platform_list}"""

        logger.divider()
        send_bark_notification(title, content, logger)

        logger.success(f"所有任务完成！总耗时: {int(duration)}秒")
        logger.divider()

    except Exception as e:
        logger.error(f"脚本执行异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        send_bark_notification("自动上传异常", str(e), logger)


if __name__ == "__main__":
    main()
