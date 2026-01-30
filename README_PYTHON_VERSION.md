# Python 版本兼容性说明

## 📋 依赖文件说明

项目提供了两个依赖文件，分别支持不同的 Python 版本：

### 1. `requirements.txt` - Python 3.10+ 版本（推荐）
- **适用版本**：Python 3.10, 3.11, 3.12, 3.13+
- **使用场景**：主机器、新部署环境
- **关键依赖**：
  - click==8.2.1
  - cffi==1.17.1

### 2. `requirements_py39.txt` - Python 3.9 兼容版本
- **适用版本**：Python 3.9
- **使用场景**：老版本 Python 环境
- **关键修改**：
  - click: 8.2.1 → 8.1.8
  - cffi: 1.17.1 → 1.16.0

---

## 🚀 使用方法

### 检查 Python 版本

```bash
python3 --version
```

### 安装依赖

**Python 3.10+（推荐）**：
```bash
pip3 install -r requirements.txt
```

**Python 3.9**：
```bash
pip3 install -r requirements_py39.txt
```

---

## ⚠️ 常见问题

### 错误：click 或 cffi 版本不兼容

**错误信息**：
```
ERROR: Could not find a version that satisfies the requirement click==8.2.1
ERROR: No matching distribution found for click==8.2.1
```

**解决方案**：
1. 检查 Python 版本（需要 >=3.10）
2. 如果是 Python 3.9，使用 `requirements_py39.txt`

### 如何升级 Python

**macOS (Homebrew)**：
```bash
# 安装最新版 Python
brew install python@3.13

# 验证安装
python3.13 --version

# 创建别名（可选）
echo "alias python3=/opt/homebrew/bin/python3.13" >> ~/.zshrc
source ~/.zshrc
```

---

## 📊 版本对比

| 包名 | Python 3.9 | Python 3.10+ |
|------|-----------|--------------|
| click | 8.1.8 | 8.2.1 |
| cffi | 1.16.0 | 1.17.1 |

---

## 💡 建议

- ✅ **推荐使用 Python 3.10+**，可以获得更好的性能和最新特性
- ✅ **定期升级依赖**：`pip3 install --upgrade -r requirements.txt`
- ✅ **使用虚拟环境**：`python3 -m venv venv`
