# -*- coding: utf-8 -*-
"""
全局配置模块
包含项目基础配置和配置文件加载功能
"""

import json
from pathlib import Path

# 项目基础目录
BASE_DIR = Path(__file__).parent.resolve()

# 小红书服务配置（默认值，实际值从config.json读取）
XHS_SERVER_DEFAULT = "http://127.0.0.1:11901"

# macOS Chrome 路径示例（如果为空则使用系统默认 Chromium）
LOCAL_CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# 默认headless值，会在运行时从config.json读取
_LOCAL_CHROME_HEADLESS_DEFAULT = False

# ==================== 配置文件加载功能 ====================

# 全局配置缓存
_config_cache = None


def load_config():
    """
    加载全局配置文件 config.json
    如果文件不存在，返回默认配置
    """
    global _config_cache

    config_file = BASE_DIR / "config.json"

    if _config_cache is not None:
        return _config_cache

    # 默认配置
    default_config = {
        "keep_browser_open": True,
        "keep_browser_duration": 3600,
        "bilibili_tid": 36,
        "bilibili_schedule": False,
        "step_delay": 3,  # 步骤之间的延迟时间（秒），用于避免触发风控
        "chrome_headless": False,  # 浏览器headless模式，False=显示窗口，True=后台运行
        "platforms": {
            "xiaohongshu": {"enabled": True, "keep_browser_open": True},
            "douyin": {"enabled": True, "keep_browser_open": True},
            "tencent": {"enabled": True, "keep_browser_open": True},
            "kuaishou": {"enabled": True, "keep_browser_open": True},
            "tiktok": {"enabled": True, "keep_browser_open": True},
            "baijiahao": {"enabled": True, "keep_browser_open": True},
            "bilibili": {"enabled": True}
        }
    }

    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                _config_cache = json.load(f)
                # 合并默认配置，确保所有必需的键都存在
                for key, value in default_config.items():
                    if key not in _config_cache:
                        _config_cache[key] = value
                return _config_cache
        except Exception as e:
            print(f"⚠️  加载配置文件失败: {e}，使用默认配置")
            return default_config
    else:
        # 创建默认配置文件
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"✅ 已创建默认配置文件: {config_file}")
        except:
            pass
        return default_config


def get_config(key=None, default=None):
    """
    获取配置值

    Args:
        key: 配置键，支持点号分隔的路径，如 'platforms.xiaohongshu.enabled'
        default: 默认值

    Returns:
        配置值
    """
    config = load_config()

    if key is None:
        return config

    # 支持点号分隔的路径
    keys = key.split('.')
    value = config

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def reload_config():
    """重新加载配置文件"""
    global _config_cache
    _config_cache = None
    return load_config()


def is_platform_enabled(platform):
    """检查平台是否启用（使用当前账号的配置）"""
    from myUtils.account_manager import is_platform_enabled_for_account, get_current_account
    current_account = get_current_account()
    return is_platform_enabled_for_account(current_account, platform)


def should_keep_browser_open(platform):
    """检查平台是否应保持浏览器打开"""
    # 首先检查平台特定配置
    platform_config = get_config(f'platforms.{platform}')
    if platform_config and 'keep_browser_open' in platform_config:
        return platform_config['keep_browser_open']

    # 否则使用全局配置
    return get_config('keep_browser_open', True)


def get_keep_browser_duration():
    """获取保持浏览器打开的时长（秒）"""
    return get_config('keep_browser_duration', 3600)


def get_step_delay():
    """获取步骤之间的延迟时间（秒），用于避免触发风控"""
    return get_config('step_delay', 3)


def save_config(config=None):
    """
    保存配置到文件

    Args:
        config: 要保存的配置，如果为 None 则保存当前配置
    """
    global _config_cache

    if config is None:
        config = _config_cache if _config_cache else load_config()

    config_file = BASE_DIR / "config.json"

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        _config_cache = config
        return True
    except Exception as e:
        print(f"⚠️  保存配置文件失败: {e}")
        return False


def is_chrome_headless():
    """
    获取Chrome headless模式配置

    Returns:
        bool: False=显示浏览器窗口，True=后台运行
    """
    return get_config('chrome_headless', _LOCAL_CHROME_HEADLESS_DEFAULT)


def set_chrome_headless(headless):
    """
    设置Chrome headless模式

    Args:
        headless: bool, False=显示浏览器窗口，True=后台运行

    Returns:
        bool: 设置是否成功
    """
    config = load_config()
    config['chrome_headless'] = headless
    return save_config(config)


# 动态获取headless配置
LOCAL_CHROME_HEADLESS = is_chrome_headless()


# ==================== 账号管理便捷函数 ====================

def get_current_account():
    """获取当前账号"""
    from myUtils.account_manager import get_current_account as _get_current_account
    return _get_current_account()


def get_accounts():
    """获取账号列表"""
    from myUtils.account_manager import get_accounts as _get_accounts
    return _get_accounts()


def get_cookie_path(platform_id):
    """
    获取当前账号的cookie文件路径

    Args:
        platform_id: 平台ID (如 'xiaohongshu', 'douyin' 等)

    Returns:
        cookie文件路径
    """
    from myUtils.account_manager import get_cookie_path_for_current_account
    return get_cookie_path_for_current_account(platform_id)


def get_chrome_user_data_dir(platform_id):
    """
    获取Chrome用户数据目录路径（用于永久保存浏览器数据）

    Args:
        platform_id: 平台ID (如 'xiaohongshu', 'douyin' 等)

    Returns:
        用户数据目录路径
    """
    from myUtils.account_manager import get_current_account
    current_account = get_current_account()
    user_data_dir = BASE_DIR / "data" / "chrome_user_data" / platform_id / current_account
    user_data_dir.mkdir(parents=True, exist_ok=True)
    return str(user_data_dir)


# ==================== 通知服务配置函数 ====================

def get_bark_url():
    """
    获取Bark通知URL
    优先从环境变量读取，其次从config.json

    Returns:
        str: Bark URL，如果未配置则返回空字符串
    """
    import os

    # 1. 从环境变量读取 BARK_ID
    bark_id = os.getenv('BARK_ID', '')
    if bark_id:
        return f"https://api.day.app/{bark_id}"

    # 2. 从config.json读取（向后兼容）
    bark_url = get_config('bark.url', '')
    if bark_url:
        return bark_url

    # 3. 尝试从旧的 secure_config 读取（兼容性）
    try:
        import sys
        sys.path.insert(0, str(Path('/Users/kidcdf/projects/kid_utils')))
        from secure_config import get_config as get_secure_config
        bark_id = get_secure_config('bark.id', '')
        if bark_id:
            return f"https://api.day.app/{bark_id}"
    except:
        pass

    return ''


def get_telegram_config():
    """
    获取Telegram Bot配置
    优先从环境变量读取，其次从config.json

    Returns:
        dict: {'bot_token': str, 'chat_id': str}，如果未配置则返回空字典
    """
    import os

    # 1. 从环境变量读取
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '') or os.getenv('TELEGRAM_BOT_GDKIDDD_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')

    if bot_token and chat_id:
        return {'bot_token': bot_token, 'chat_id': chat_id}

    # 2. 尝试从旧的 secure_config 读取（兼容性）
    try:
        import sys
        sys.path.insert(0, str(Path('/Users/kidcdf/projects/kid_utils')))
        from secure_config import get_config as get_secure_config

        bot_token = get_secure_config('telegram_bot.gdkiddd_token') or get_secure_config('telegram_bot.token')
        chat_id = get_secure_config('telegram_bot.chat_ids.kid_studio')

        if bot_token and chat_id:
            return {'bot_token': bot_token, 'chat_id': chat_id}
    except:
        pass

    # 3. 从config.json读取（向后兼容）
    telegram = get_config('telegram', {})
    return {
        'bot_token': telegram.get('bot_token', ''),
        'chat_id': telegram.get('chat_id', '')
    }


def get_xhs_server():
    """
    获取小红书服务地址

    Returns:
        str: 小红书服务地址，如果未配置则返回默认值
    """
    return get_config('xhs_server', XHS_SERVER_DEFAULT)
