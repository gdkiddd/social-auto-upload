# Playwright 自动化最佳实践 - 按钮和标签定位经验总结

本文档总结了在使用 Playwright 进行网页自动化时，定位和点击按钮、标签的最佳实践和常见问题解决方案。

## 目录
- [核心原则](#核心原则)
- [常见问题与解决方案](#常见问题与解决方案)
- [选择器策略](#选择器策略)
- [实战案例](#实战案例)

---

## 核心原则

### 1. 避免 Strict Mode Violation
**问题：** 当选择器匹配到多个元素时，Playwright 的 strict mode 会报错

**解决方案：**
- 使用 `.first` 选择第一个元素
- 使用更精确的选择器组合
- 使用 `:has()` 伪类进行精确过滤

```python
# ❌ 错误：匹配到多个元素
button = page.locator('button:has-text("发布")')
await button.click()  # strict mode violation

# ✅ 正确：选择第一个元素
button = page.locator('button:has-text("发布")').first
await button.click()

# ✅ 更好：使用更精确的选择器
button = page.locator('button.semi-button-primary:has-text("发布")')
await button.click()
```

### 2. 使用多个备选选择器
不同的网页版本或动态加载可能导致单一选择器失效，应该准备多个备选方案。

```python
# 方式1：使用 class 选择器
button = page.locator('button.semi-button-primary:has-text("完成")')

if await button.count() == 0:
    # 方式2：使用更通用的选择器
    button = page.locator('div.semi-button:has-text("完成")')

if await button.count() == 0:
    # 方式3：使用层级结构
    button = page.locator('div.container >> span:has-text("完成")')

# 使用第一个可用的选择器
if await button.count() > 0:
    await button.click()
```

### 3. 添加重试逻辑
网页元素可能需要时间加载，或者存在网络延迟，应该添加重试机制。

```python
max_retries = 3
success = False

for attempt in range(max_retries):
    try:
        button = page.locator('button:has-text("确认")')
        if await button.count() > 0:
            await button.click()
            success = True
            break
        else:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    except Exception as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(1)
        else:
            raise

if not success:
    print("操作失败")
```

### 4. 使用 File Chooser API 处理文件上传
不要点击文件输入框，使用 `expect_file_chooser` API 更可靠。

```python
# ❌ 错误：直接点击 file input
file_input = page.locator('input[type="file"]')
await file_input.set_input_files('/path/to/file')

# ✅ 正确：使用 file chooser API
async with page.expect_file_chooser() as fc_info:
    await upload_button.click()  # 点击触发文件选择的按钮

file_chooser = await fc_info.value
await file_chooser.set_files('/path/to/file')
```

---

## 常见问题与解决方案

### 问题 1: Class 名称动态变化
**现象：** 元素的 class 包含随机哈希值，如 `container-XzaV9h upload-ZOJTUA`

**解决方案：**
- 使用部分 class 名称：`div[class*="container-"]`
- 使用其他属性：`div[data-role="upload"]`
- 使用子元素或文本内容：`div:has-text("上传封面")`

```python
# 使用部分 class 匹配
container = page.locator('div.upload-ZOJTUA')  # ❌ 可能失效
container = page.locator('div[class*="upload-"]')  # ✅ 更稳定

# 使用文本内容
container = page.locator('div:has(div.text-zsBQsb:has-text("上传封面"))')
```

### 问题 2: 元素在 iframe 中
**现象：** 元素存在但无法定位

**解决方案：**
```python
# 先切换到 iframe
frame = page.frame_locator('iframe selector')
button = frame.locator('button:has-text("确认")')
await button.click()
```

### 问题 3: 元素需要滚动到可见区域
**现象：** 元素存在但点击失败

**解决方案：**
```python
element = page.locator('button:has-text("确认")')
await element.scroll_into_view_if_needed()
await element.click()
```

### 问题 4: 元素被其他元素遮挡
**现象：** 点击报错 "Element is obscured by another element"

**解决方案：**
```python
# 方式1：强制点击
element = page.locator('button:has-text("确认")')
await element.click(force=True)

# 方式2：先移除遮挡元素
obstacle = page.locator('.modal-overlay')
await obstacle.evaluate('el => el.remove()')
await element.click()
```

### 问题 5: Ant Design 组件的特殊处理
**现象：** Ant Design 的 Checkbox、Radio 等组件需要点击特定元素

**解决方案：**
```python
# ❌ 错误：直接点击 input
checkbox = page.locator('input[type="checkbox"]')
await checkbox.click()

# ✅ 正确：点击 wrapper 或 span
checkbox_wrapper = page.locator('label.ant-checkbox-wrapper:has-text("允许下载")')
await checkbox_wrapper.click()

# 或者点击内部的可点击元素
checkbox_inner = page.locator('.ant-checkbox-inner')
await checkbox_inner.click()
```

---

## 选择器策略

### 优先级排序（从高到低）

#### 1. 使用 data-* 属性（最稳定）
```python
button = page.locator('[data-testid="submit-button"]')
```

#### 2. 使用明确的 class 名称
```python
button = page.locator('button.semi-button-primary')
```

#### 3. 使用文本内容配合 class
```python
button = page.locator('button.semi-button-primary:has-text("确认")')
```

#### 4. 使用文本内容（备选）
```python
button = page.locator('button:has-text("确认")')
```

#### 5. 使用层级关系
```python
button = page.locator('div.container >> div.content >> button.submit')
```

### CSS 选择器 vs XPath

**推荐使用 CSS 选择器（更简洁）：**
```python
# CSS 选择器
button = page.locator('button.semi-button-primary')

# XPath（仅在复杂情况使用）
button = page.locator('xpath=//button[contains(@class, "semi-button-primary")]')
```

---

## 实战案例

### 案例 1: 快手"允许下载" Checkbox

**HTML 结构：**
```html
<label class="ant-checkbox-wrapper ant-checkbox-wrapper-checked">
  <span class="ant-checkbox ant-checkbox-checked">
    <input type="checkbox" class="ant-checkbox-input" value="downloadType" checked="">
    <span class="ant-checkbox-inner"></span>
  </span>
  <span>允许下载此作品</span>
</label>
```

**解决方案：**
```python
# 点击 wrapper（最可靠）
checkbox_wrapper = page.locator('label.ant-checkbox-wrapper:has-text("允许下载")')
await checkbox_wrapper.click()

# 或点击内部 span
checkbox_inner = page.locator('.ant-checkbox-inner')
await checkbox_inner.click()
```

### 案例 2: 抖音上传封面

**完整流程：**
```python
async def set_cover(page, cover_file):
    # 1. 点击"选择封面"
    select_button = page.locator('div[class*="cover-"]').first
    await select_button.click()
    await asyncio.sleep(2)

    # 2. 使用多种选择器定位"上传封面"容器
    upload_container = page.locator('div.upload-ZOJTUA.container-XzaV9h')

    if await upload_container.count() == 0:
        upload_container = page.locator('div:has(div.text-zsBQsb:has-text("上传封面")) >> div.semi-upload')

    # 使用 file chooser API
    async with page.expect_file_chooser() as fc_info:
        await upload_container.first.click()

    file_chooser = await fc_info.value
    await file_chooser.set_files(str(cover_file))

    # 3. 点击"设置横封面"按钮
    horizontal_button = page.locator('button.semi-button-primary:has(span.semi-button-content:has-text("设置横封面"))')
    await horizontal_button.click()

    # 4. 点击"完成"
    finish_button = page.locator('button:has-text("完成")')
    await finish_button.click()
```

### 案例 3: 百家号封面上传

**使用精确的选择器组合：**
```python
# 点击"编辑封面"
cover_wrapper = page.locator('div[class*="coverWrapper"]').first
await cover_wrapper.click()

# 点击"本地上传"按钮并使用 file chooser
local_upload = page.locator('div._28b32fc37e18461a-noimg:has-text("本地上传")')

async with page.expect_file_chooser() as fc_info:
    await local_upload.click()

file_chooser = await fc_info.value
await file_chooser.set_files(str(cover_file))

# 点击"确定"
confirm_button = page.locator('button:has-text("确定")')
await confirm_button.first.click()
```

---

## 调试技巧

### 1. 检查元素是否存在
```python
count = await page.locator('button:has-text("确认")').count()
print(f"找到 {count} 个元素")
```

### 2. 获取元素详细信息
```python
element = page.locator('button:has-text("确认")').first
class_name = await element.get_attribute('class')
text_content = await element.text_content()
print(f"Class: {class_name}")
print(f"Text: {text_content}")
```

### 3. 截图调试
```python
await page.screenshot(path='debug.png')
```

### 4. 等待策略
```python
# 等待元素出现
await page.wait_for_selector('button:has-text("确认")', timeout=5000)

# 等待元素可见
button = page.locator('button:has-text("确认")')
await button.wait_for(state='visible')

# 等待 URL 变化
await page.wait_for_url('https://example.com/success')
```

---

## 性能优化建议

### 1. 减少不必要的等待
```python
# ❌ 固定等待（慢）
await asyncio.sleep(5)

# ✅ 智能等待（快）
await page.wait_for_selector('button:has-text("确认")')
```

### 2. 复用 Locators
```python
# ❌ 每次都创建新的 locator
for i in range(10):
    await page.locator('button').click()

# ✅ 复用 locator
button = page.locator('button')
for i in range(10):
    await button.nth(i).click()
```

### 3. 批量操作
```python
# ✅ 使用 Promise.all 并行执行
await asyncio.gather(
    element1.click(),
    element2.fill('text'),
    element3.select_option('value')
)
```

---

## 总结

### 核心要点
1. **精确选择器优先**：使用 class + 文本组合，避免歧义
2. **多重备选方案**：准备 2-3 个备选选择器
3. **重试机制**：对关键操作添加重试逻辑
4. **详细日志**：记录每一步操作，方便调试
5. **容错处理**：操作失败时给出明确提示

### 常用模式
```python
# 标准模式：查找 + 重试 + 容错
element = page.locator('preferred-selector')
if await element.count() == 0:
    element = page.locator('fallback-selector')

for attempt in range(3):
    if await element.count() > 0:
        try:
            await element.click()
            break
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1)
            else:
                print(f"操作失败: {e}")
    else:
        await asyncio.sleep(1)
```

---

**最后更新：** 2026-01-23
**适用版本：** Playwright Python Async API
