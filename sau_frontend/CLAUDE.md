# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是 social-auto-upload 项目的前端部分，是一个自媒体自动化运营系统的 Web 界面。前端与 Python Flask 后端配合，提供视频上传、账号管理、发布中心等功能。

## 开发命令

```bash
# 安装依赖
npm install

# 启动开发服务器（端口 5173）
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## 技术栈

- **Vue 3** - 使用 Composition API 和 `<script setup>` 语法糖
- **Vite** - 构建工具，配置了路径别名 `@` 指向 `src` 目录
- **Element Plus** - UI 组件库，所有图标已在 main.js 中全局注册
- **Pinia** - 状态管理，按功能模块划分 stores
- **Vue Router** - 使用 WebHash 模式
- **Axios** - HTTP 请求，已封装在 `src/utils/request.js`
- **Sass** - CSS 预处理器，样式变量定义在 `src/styles/variables.scss`

## 项目架构

### 目录结构

```
src/
├── api/                # API 接口层，按功能模块划分
│   ├── index.js       # 统一导出所有 API
│   ├── account.js     # 账号管理相关 API
│   ├── material.js    # 素材管理相关 API
│   └── user.js        # 用户相关 API
├── components/         # 可复用组件
├── router/            # 路由配置
│   └── index.js       # 路由定义，使用 hash 模式
├── stores/            # Pinia 状态管理
│   ├── index.js       # Pinia 实例和 store 导出
│   ├── account.js     # 账号状态管理
│   ├── app.js         # 应用全局状态
│   └── user.js        # 用户状态管理
├── styles/            # 全局样式
│   ├── index.scss     # 样式入口
│   ├── reset.scss     # 样式重置
│   └── variables.scss # SCSS 变量（颜色、间距、字体等）
├── utils/             # 工具函数
│   └── request.js     # Axios 封装，包含拦截器
├── views/             # 页面组件
│   ├── Dashboard.vue         # 仪表盘首页
│   ├── AccountManagement.vue # 账号管理
│   ├── MaterialManagement.vue # 素材管理
│   ├── PublishCenter.vue     # 发布中心
│   └── About.vue            # 关于页面
├── App.vue            # 根组件
└── main.js            # 应用入口
```

### API 通信架构

**请求流程：**
1. 开发环境：前端请求 `/api/*` → Vite 代理转发到 `http://localhost:5409`
2. 生产环境：直接请求 `VITE_API_BASE_URL` 配置的地址

**HTTP 封装（`src/utils/request.js`）：**
- 自动添加 Authorization token（从 localStorage 读取）
- 统一响应格式处理（`code === 200` 或 `success`）
- 错误处理和 ElMessage 提示
- 提供快捷方法：`get`、`post`、`put`、`delete`、`upload`

**使用方式：**
```javascript
import { http } from '@/utils/request'
import { accountApi } from '@/api/account'

// 使用封装的 API 模块
const accounts = await accountApi.getAccounts()

// 或直接使用 http
const data = await http.get('/getFiles')
```

### 状态管理架构

**Store 模块划分：**
- `account.js`：管理社交平台账号列表，处理后端返回的数组格式 `[id, type, filePath, name, status]`
- `app.js`：应用全局状态（页面访问标记、素材列表、刷新状态）
- `user.js`：用户认证和信息

**平台类型映射（重要）：**
```javascript
const platformTypes = {
  1: '小红书',
  2: '视频号',
  3: '抖音',
  4: '快手'
}
```

### 路由架构

- 使用 `createWebHashHistory()` 模式
- 主要路由：
  - `/` - Dashboard（仪表盘）
  - `/account-management` - 账号管理
  - `/material-management` - 素材管理
  - `/publish-center` - 发布中心
  - `/about` - 关于

### 样式系统

- SCSS 变量统一在 `src/styles/variables.scss` 定义
- 使用 `@use '@/styles/variables.scss' as *` 引入变量
- Element Plus 主题定制通过覆盖 CSS 变量实现
- 已移除浏览器默认样式（reset.scss）

## 重要配置

### 环境变量

**开发环境（`.env.development`）：**
```
VITE_API_BASE_URL=/api  # 使用代理
```

**生产环境（`.env.production`）：**
```
VITE_API_BASE_URL=http://localhost:5409  # 直接请求后端
```

### Vite 配置要点

1. **路径别名：** `@` → `src`
2. **开发服务器：** 端口 5173，自动打开浏览器
3. **代理配置：** `/api` → `http://localhost:5409`（仅开发环境）
4. **构建优化：** 手动分包（vue、elementPlus、utils）

## 开发注意事项

1. **API 调用：** 所有 API 请求应统一放在 `src/api/` 目录，按模块管理
2. **状态管理：** 跨页面共享的数据使用 Pinia store，页面局部状态使用 `ref`/`reactive`
3. **组件规范：** 页面组件放在 `views/`，可复用组件放在 `components/`
4. **Element Plus 图标：** 已全局注册，直接使用 `<el-icon><IconName /></el-icon>`
5. **后端数据格式：** 账号数据以数组形式返回 `[id, type, filePath, name, status]`，需在 store 中转换
6. **上传进度：** 使用 `http.upload()` 方法，支持 `onUploadProgress` 回调
7. **环境变量：** 使用 `import.meta.env.VITE_API_BASE_URL` 访问

## 后端集成

- 后端服务运行在 `http://localhost:5409`
- 主要 API 端点示例：
  - `/getValidAccounts` - 获取有效账号（带验证）
  - `/getAccounts` - 获取账号列表（快速）
  - `/getFiles` - 获取素材文件列表
  - `/uploadSave` - 上传素材
  - `/account` - 添加账号

## 通用规范参考

本项目同时遵循 `/Users/kidcdf/projects/claude_web.md` 中定义的 Web 项目开发规范。
