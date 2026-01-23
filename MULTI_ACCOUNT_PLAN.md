# CLI多账号切换功能 - 实现计划

## 一、需求概述

在CLI模式下实现多账号管理功能：
1. 启动后先选择账号，再选择平台
2. 账号界面可以选择已有账号、添加账号、删除账号
3. 一个账号对应一套全平台的cookies
4. 账号列表保存在config.json
5. 默认账号名为"KIDDD"

## 二、数据结构设计

### 1. config.json 新增字段

```json
{
  "accounts": ["KIDDD"],
  "current_account": "KIDDD",
  "keep_browser_open": true,
  ...
}
```

- `accounts`: 账号名称列表
- `current_account`: 当前选中的账号

### 2. Cookie目录结构变化

**旧结构:**
```
cookies/
  ├── xiaohongshu_uploader/account.json
  ├── tencent_uploader/account.json
  ├── bilibili_uploader/account.json
  ├── douyin_uploader/account.json
  ├── ks_uploader/account.json
  └── baijiahao_uploader/account.json
```

**新结构:**
```
cookies/
  ├── KIDDD/
  │   ├── xiaohongshu.json
  │   ├── tencent.json
  │   ├── bilibili.json
  │   ├── douyin.json
  │   ├── kuaishou.json
  │   └── baijiahao.json
  ├── 账号2/
  │   └── ...
```

## 三、实现方案

### 3.1 创建账号管理模块 (account_manager.py)

新增 `myUtils/account_manager.py`，提供以下功能：

```python
# 获取账号列表
def get_accounts()

# 添加账号
def add_account(account_name)

# 删除账号
def delete_account(account_name)

# 切换账号
def set_current_account(account_name)

# 获取当前账号
def get_current_account()

# 获取账号的cookie文件路径
def get_account_cookie_path(account_name, platform_id)

# 迁移旧cookie到新结构
def migrate_old_cookies()
```

### 3.2 修改 conf.py

添加账号相关的配置加载函数：

```python
def get_current_account()
def get_accounts()
def set_current_account(account_name)
def add_account(account_name)
def delete_account(account_name)
```

### 3.3 修改 run.py

**新增功能：**

1. 账号选择界面（在平台选择之前）
   - 显示已有账号列表
   - 标记当前账号
   - 提供切换账号选项
   - 提供添加账号选项
   - 提供删除账号选项

2. 修改PLATFORMS配置
   - cookie_file路径改为动态获取：`get_account_cookie_path(current_account, platform_id)`

**界面流程：**
```
启动
  ↓
显示视频信息
  ↓
账号选择界面
  ├─ [1] 账号1 (当前)
  ├─ [2] 账号2
  ├─ [+] 添加新账号
  ├─ [-] 删除账号
  └─ [0] 继续
  ↓
平台选择界面
```

### 3.4 修改 examples/ 下的脚本

**登录脚本** (get_*_cookie.py):
- 从 `cookies/{platform}_uploader/account.json` 改为 `cookies/{current_account}/{platform}.json`

**上传脚本** (upload_video_to_*.py):
- 从 `cookies/{platform}_uploader/account.json` 改为 `cookies/{current_account}/{platform}.json`
- 需要能够接收account_name参数（或从config读取）

### 3.5 Cookie文件迁移

提供迁移工具 `migrate_cookies.py`：
1. 读取旧的cookie文件
2. 创建KIDDD目录
3. 将旧cookie复制到新位置并重命名
4. 可选：删除旧cookie文件

## 四、需要修改的文件清单

### 新增文件
1. `myUtils/account_manager.py` - 账号管理模块
2. `migrate_cookies.py` - Cookie迁移脚本（可选）

### 修改文件
1. `conf.py` - 添加账号相关配置函数
2. `run.py` - 添加账号选择界面
3. `examples/get_xiaohongshu_cookie.py`
4. `examples/get_douyin_cookie.py`
5. `examples/get_tencent_cookie.py`
6. `examples/get_kuaishou_cookie.py`
7. `examples/get_baijiahao_cookie.py`
8. `examples/get_bilibili_cookie.py` (如果有)
9. `examples/upload_video_to_xiaohongshu.py`
10. `examples/upload_video_to_douyin.py`
11. `examples/upload_video_to_tencent.py`
12. `examples/upload_video_to_kuaishou.py`
13. `examples/upload_video_to_baijiahao.py`
14. `examples/upload_video_to_bilibili.py`

### 平台ID映射
```python
PLATFORM_IDS = {
    'xiaohongshu': 'xiaohongshu',
    'douyin': 'douyin',
    'tencent': 'tencent',
    'kuaishou': 'kuaishou',
    'baijiahao': 'baijiahao',
    'bilibili': 'bilibili'
}
```

## 五、实现步骤

1. **创建账号管理模块** - 实现账号的增删改查和路径管理
2. **修改conf.py** - 添加账号配置相关函数
3. **实现Cookie迁移** - 将现有cookie迁移到新结构
4. **修改run.py** - 添加账号选择界面
5. **修改登录脚本** - 使用新的cookie路径
6. **修改上传脚本** - 使用新的cookie路径
7. **测试** - 测试多账号切换功能

## 六、注意事项

1. **向后兼容**：保留旧cookie文件，直到确认新结构工作正常
2. **错误处理**：处理账号不存在、cookie文件缺失等情况
3. **用户确认**：删除账号前需要用户确认
4. **默认账号**：首次运行时自动创建KIDDD账号并迁移旧cookie
5. **目录创建**：自动创建账号目录

## 七、界面设计示例

```
============================================================
📹 即将上传的视频
============================================================
✅ 找到 1 个视频文件

  [1] test.mp4 (15.2 MB)
      标题: 测试视频
      标签: #测试
============================================================

============================================================
👤 账号选择
============================================================
当前账号: KIDDD

请选择账号：
  [1] KIDDD ✅ (当前)
  [2] 测试账号2
  [+] 添加新账号
  [-] 删除账号
  [0] 继续
============================================================
```
