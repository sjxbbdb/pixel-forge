# pixel-forge

纯桌面自动化工具包。视觉感知 + 键鼠操作 + 验证工作流，给智能体直接调用。

## 结构

```
vision.py    — 截图、OCR、像素对比、变化检测
actions.py   — 鼠标点击、键盘输入、窗口查找/激活
workflow.py  — Pipeline：startup → poll → send_text（每步截前后图验证）
```

## 安装

```bash
pip install pillow pytesseract pyautogui pygetwindow numpy httpx
# Mac 额外: pip install pyobjc-framework-Quartz
```

## 使用

```python
import asyncio
from workflow import Pipeline

async def main():
    pipe = Pipeline(
        keywords=["飞鸽", "feige"],          # 窗口标题关键词
        process_names=["Feige", "ByteDance"], # Mac进程名
    )

    ok = await pipe.startup()
    if not ok:
        print("未找到窗口")
        return

    while True:
        changed = await pipe.poll()
        if changed:
            text = await pipe.read_text()    # OCR当前窗口内容
            print(f"屏幕上: {text[:100]}")

            result = await pipe.send_text("你好")
            print(f"发送: {result}")

        await asyncio.sleep(3)

asyncio.run(main())
```

## 模块

### vision.py

| 函数 | 说明 |
|------|------|
| `capture(bbox)` | 区域截图 → PIL Image |
| `ocr(img)` | 截图 → 文字 |
| `pixel_diff(a, b)` | 两张图差异比例 (0~1) |
| `is_blank(img)` | 是否黑屏/白屏/纯色 |
| `changed(before, after)` | 是否有可见变化 |
| `text_in_image(img, needle)` | 截图中是否包含指定文字 |

### actions.py

| 函数 | 说明 |
|------|------|
| `click(x, y)` | 鼠标点击 |
| `type_text(text)` | 逐字输入 |
| `press_key(key)` | 按键 |
| `hotkey(*keys)` | 组合键 |
| `find_window(keywords)` | 按标题找窗口 → rect |
| `activate_window(keywords)` | 激活窗口到前台 |

### workflow.py

`Pipeline` 类封装完整流程：

```python
pipe = Pipeline(keywords=[...], process_names=[...])

await pipe.startup()         # 找窗口 + 激活 + 截图验证
await pipe.poll()            # 截屏对比，返回是否有变化
await pipe.read_text()       # OCR当前窗口全部文字
await pipe.read_image()      # 返回当前截图(PIL Image)
await pipe.send_text("abc")  # 点击→输入→发送→截图验证
```

## 验证链

`send_text` 每一步都带截图对比：

```
点击输入框  → 截前图→点击→截后图→像素差>0.5%→通过
输入文字    → 截前图→打字→截后图→OCR确认文字→通过
发送        → 截前图→回车→截后图→像素差>2%→后验证OCR→通过
```

## 跨平台

- Windows: pygetwindow + ImageGrab + pyautogui
- Mac: osascript + screencapture + pyautogui

代码自动判断平台，无需手动切换。
