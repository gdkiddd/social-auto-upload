# -*- coding: utf-8 -*-
"""
全局配置模块
包含项目基础配置和配置文件加载功能
"""

import json
from pathlib import Path

# 项目基础目录
BASE_DIR = Path(__file__).parent.resolve()

# 小红书服务配置
XHS_SERVER = "http://127.0.0.1:11901"

# macOS Chrome 路径示例（如果为空则使用系统默认 Chromium）
LOCAL_CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
LOCAL_CHROME_HEADLESS = False  # False = 显示浏览器窗口，True = 后台运行

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
    """检查平台是否启用"""
    return get_config(f'platforms.{platform}.enabled', True)


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
