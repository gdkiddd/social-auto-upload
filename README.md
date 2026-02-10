# 社交自动上传

一键发布视频到多个社交平台。

## 支持平台

- 微信视频号
- 抖音
- B站
- 小红书
- 快手
- 百家号
- TikTok
- YouTube

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 初始化数据库
python db/createTable.py

# 运行后端
python sau_backend.py

# 运行前端
cd sau_frontend
npm install
npm run dev
```

## 命令行工具

### 单平台上传

```bash
# 上传到视频号
python upload_tencent.py Amy

# 上传到抖音
python upload_douyin.py Amy

# 通用命令
python upload.py <平台> <账号>
```

### 获取Cookie

```bash
python examples/get_tencent_cookie.py
python examples/get_douyin_cookie.py
```

## 配置

复制 `conf.example.py` 为 `conf.py` 并配置：

- Bark通知URL
- Telegram Bot配置
- 平台参数

## 目录结构

```
social-auto-upload/
├── cookies/          # Cookie存储（已加入gitignore）
├── videos/           # 待上传视频
├── uploader/         # 各平台上传器
├── examples/         # 示例脚本
└── upload*.py        # 快捷上传工具
```
