# -*- coding: utf-8 -*-
"""
账号管理模块
提供多账号的增删改查功能
"""

import json
import shutil
from pathlib import Path
from typing import List, Optional

from conf import BASE_DIR, load_config, save_config


# 平台ID映射
PLATFORM_COOKIE_NAMES = {
    'xiaohongshu': 'xiaohongshu',
    'tencent': 'tencent',
    'bilibili': 'bilibili',
    'douyin': 'douyin',
    'kuaishou': 'kuaishou',
    'baijiahao': 'baijiahao'
}

# 旧的cookie文件路径映射
OLD_COOKIE_PATHS = {
    'xiaohongshu': 'cookies/xiaohongshu_uploader/account.json',
    'tencent': 'cookies/tencent_uploader/account.json',
    'bilibili': 'cookies/bilibili_uploader/account.json',
    'douyin': 'cookies/douyin_uploader/account.json',
    'kuaishou': 'cookies/ks_uploader/account.json',
    'baijiahao': 'cookies/baijiahao_uploader/account.json'
}


def get_accounts() -> List[str]:
    """获取账号列表"""
    config = load_config()
    return config.get('accounts', ['KIDDD'])


def add_account(account_name: str) -> bool:
    """
    添加新账号

    Args:
        account_name: 账号名称

    Returns:
        是否添加成功
    """
    if not account_name or not account_name.strip():
        print("❌ 账号名称不能为空")
        return False

    account_name = account_name.strip()

    # 检查账号是否已存在
    accounts = get_accounts()
    if account_name in accounts:
        print(f"❌ 账号 '{account_name}' 已存在")
        return False

    # 添加账号
    accounts.append(account_name)
    config = load_config()
    config['accounts'] = accounts

    if save_config(config):
        # 创建账号目录
        account_dir = BASE_DIR / 'cookies' / account_name
        account_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ 账号 '{account_name}' 添加成功")
        return True
    else:
        print(f"❌ 添加账号 '{account_name}' 失败")
        return False


def delete_account(account_name: str) -> bool:
    """
    删除账号

    Args:
        account_name: 账号名称

    Returns:
        是否删除成功
    """
    accounts = get_accounts()

    if account_name not in accounts:
        print(f"❌ 账号 '{account_name}' 不存在")
        return False

    # 如果是最后一个账号，不允许删除
    if len(accounts) == 1:
        print("❌ 这是最后一个账号，不能删除")
        return False

    # 删除账号
    accounts.remove(account_name)
    config = load_config()
    config['accounts'] = accounts

    # 如果删除的是当前账号，切换到第一个账号
    if config.get('current_account') == account_name:
        config['current_account'] = accounts[0]

    if save_config(config):
        # 删除账号目录（包含cookies）
        account_dir = BASE_DIR / 'cookies' / account_name
        if account_dir.exists():
            shutil.rmtree(account_dir)
            print(f"🗑️  已删除账号 '{account_name}' 的cookie文件")
        print(f"✅ 账号 '{account_name}' 删除成功")
        return True
    else:
        print(f"❌ 删除账号 '{account_name}' 失败")
        return False


def get_current_account() -> str:
    """获取当前账号"""
    config = load_config()
    current = config.get('current_account')

    # 如果没有当前账号或账号不存在，返回第一个账号
    accounts = get_accounts()
    if not current or current not in accounts:
        if accounts:
            set_current_account(accounts[0])
            return accounts[0]
        else:
            # 如果没有任何账号，返回默认账号
            return 'KIDDD'

    return current


def set_current_account(account_name: str) -> bool:
    """
    设置当前账号

    Args:
        account_name: 账号名称

    Returns:
        是否设置成功
    """
    accounts = get_accounts()

    if account_name not in accounts:
        print(f"❌ 账号 '{account_name}' 不存在")
        return False

    config = load_config()
    config['current_account'] = account_name

    if save_config(config):
        print(f"✅ 已切换到账号: {account_name}")
        return True
    else:
        print(f"❌ 切换账号失败")
        return False


def get_account_cookie_path(account_name: str, platform_id: str) -> Path:
    """
    获取账号的cookie文件路径

    Args:
        account_name: 账号名称
        platform_id: 平台ID

    Returns:
        cookie文件路径
    """
    cookie_name = PLATFORM_COOKIE_NAMES.get(platform_id, platform_id)
    return BASE_DIR / 'cookies' / account_name / f'{cookie_name}.json'


def check_account_cookie_exists(account_name: str, platform_id: str) -> bool:
    """
    检查账号的cookie文件是否存在

    Args:
        account_name: 账号名称
        platform_id: 平台ID

    Returns:
        cookie文件是否存在
    """
    cookie_path = get_account_cookie_path(account_name, platform_id)
    return cookie_path.exists()


def get_cookie_path_for_current_account(platform_id: str) -> Path:
    """
    获取当前账号的cookie文件路径

    Args:
        platform_id: 平台ID

    Returns:
        cookie文件路径
    """
    current_account = get_current_account()
    return get_account_cookie_path(current_account, platform_id)


def migrate_old_cookies() -> None:
    """迁移旧的cookie文件到新的账号结构"""
    print("\n" + "=" * 60)
    print("🔄 Cookie 迁移工具")
    print("=" * 60)

    # 检查是否已经有KIDDD账号
    accounts = get_accounts()
    if 'KIDDD' not in accounts:
        add_account('KIDDD')
        set_current_account('KIDDD')

    kiddd_dir = BASE_DIR / 'cookies' / 'KIDDD'
    kiddd_dir.mkdir(parents=True, exist_ok=True)

    migrated_count = 0

    for platform_id, old_path in OLD_COOKIE_PATHS.items():
        old_file = BASE_DIR / old_path

        if not old_file.exists():
            print(f"⊘ {platform_id}: 旧cookie文件不存在")
            continue

        new_file = get_account_cookie_path('KIDDD', platform_id)

        # 如果新文件已存在，跳过
        if new_file.exists():
            print(f"⊘ {platform_id}: 新cookie文件已存在，跳过")
            continue

        try:
            shutil.copy2(old_file, new_file)
            print(f"✅ {platform_id}: 迁移成功")
            migrated_count += 1
        except Exception as e:
            print(f"❌ {platform_id}: 迁移失败 - {e}")

    print()
    print(f"📊 迁移完成: {migrated_count}/{len(OLD_COOKIE_PATHS)} 个平台")
    print(f"📁 Cookie已保存到: {kiddd_dir}")

    # 询问是否删除旧文件
    print()
    choice = input("是否删除旧的cookie文件？[y/N]: ").strip().lower()
    if choice == 'y' or choice == 'yes':
        deleted_count = 0
        for platform_id, old_path in OLD_COOKIE_PATHS.items():
            old_file = BASE_DIR / old_path
            if old_file.exists():
                try:
                    old_file.unlink()
                    # 删除空目录
                    old_dir = old_file.parent
                    if old_dir.exists() and not list(old_dir.iterdir()):
                        old_dir.rmdir()
                        # 删除cookies下的空目录
                        cookies_dir = old_dir.parent
                        if cookies_dir.exists() and not list(cookies_dir.iterdir()):
                            cookies_dir.rmdir()
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  删除 {old_path} 失败: {e}")

        print(f"🗑️  已删除 {deleted_count} 个旧文件")

    print("=" * 60)


def ensure_default_account():
    """确保默认账号存在"""
    config = load_config()

    # 如果config中没有accounts字段，初始化它
    if 'accounts' not in config:
        config['accounts'] = []

    # 如果没有账号，添加KIDDD
    if not config['accounts']:
        config['accounts'].append('KIDDD')

    # 如果没有current_account，设置为KIDDD
    if 'current_account' not in config or not config['current_account']:
        config['current_account'] = 'KIDDD'

    save_config(config)

    # 创建KIDDD目录
    kiddd_dir = BASE_DIR / 'cookies' / 'KIDDD'
    kiddd_dir.mkdir(parents=True, exist_ok=True)
