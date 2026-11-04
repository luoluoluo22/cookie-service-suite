#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用图标生成与格式转换工具
- 负责生成或转换 Cookie Service Suite 的系统托盘和桌面图标
- 输出 assets/app_icon.png 与 assets/app_icon.ico
"""

import os
from PIL import Image, ImageDraw, ImageFilter

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
PNG_PATH = os.path.join(ASSETS_DIR, "app_icon.png")
ICO_PATH = os.path.join(ASSETS_DIR, "app_icon.ico")


def draw_fallback_icon(size: int = 256) -> Image.Image:
    """使用 Pillow 绘制高科技质感 Cookie 图标 (带霓虹发光与芯片电路元素)"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. 背景圆角外框 (深灰金属渐变)
    margin = int(size * 0.06)
    radius = int(size * 0.22)
    bg_box = [margin, margin, size - margin, size - margin]
    draw.rounded_rectangle(bg_box, radius=radius, fill=(18, 22, 34, 255), outline=(56, 189, 248, 180), width=int(size * 0.025))

    # 2. 发光环境环
    center_x, center_y = size // 2, size // 2
    cookie_r = int(size * 0.30)
    draw.ellipse(
        [center_x - cookie_r - 6, center_y - cookie_r - 6, center_x + cookie_r + 6, center_y + cookie_r + 6],
        outline=(56, 189, 248, 100),
        width=int(size * 0.02),
    )

    # 3. 黄金科技 Cookie 主体 (烤金与琥珀渐变质感)
    cookie_box = [center_x - cookie_r, center_y - cookie_r, center_x + cookie_r, center_y + cookie_r]
    draw.ellipse(cookie_box, fill=(217, 119, 6, 255), outline=(245, 158, 11, 255), width=int(size * 0.02))

    # 4. Cookie 上的巧克力碎与发光电路节点 (Chocolate Chips & Cyber Nodes)
    chips = [
        (center_x - int(cookie_r * 0.42), center_y - int(cookie_r * 0.35), int(cookie_r * 0.22)),
        (center_x + int(cookie_r * 0.36), center_y - int(cookie_r * 0.38), int(cookie_r * 0.20)),
        (center_x - int(cookie_r * 0.15), center_y + int(cookie_r * 0.38), int(cookie_r * 0.24)),
        (center_x + int(cookie_r * 0.40), center_y + int(cookie_r * 0.32), int(cookie_r * 0.18)),
        (center_x - int(cookie_r * 0.45), center_y + int(cookie_r * 0.18), int(cookie_r * 0.17)),
    ]
    for cx, cy, cr in chips:
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(120, 53, 15, 255), outline=(69, 26, 3, 200), width=1)

    # 5. 科技芯片微光脉络
    draw.ellipse([center_x - 10, center_y - 10, center_x + 10, center_y + 10], fill=(56, 189, 248, 255))
    draw.line([center_x, center_y, center_x - 30, center_y - 30], fill=(56, 189, 248, 220), width=2)
    draw.line([center_x, center_y, center_x + 35, center_y - 20], fill=(56, 189, 248, 220), width=2)
    draw.line([center_x, center_y, center_x + 25, center_y + 35], fill=(56, 189, 248, 220), width=2)
    draw.line([center_x, center_y, center_x - 35, center_y + 25], fill=(56, 189, 248, 220), width=2)

    return img


def ensure_app_icon() -> Image.Image:
    """确保应用图标已生成并转化为标准的 ICO 和 PNG"""
    os.makedirs(ASSETS_DIR, exist_ok=True)

    if os.path.exists(PNG_PATH):
        try:
            img = Image.open(PNG_PATH).convert("RGBA")
        except Exception:
            img = draw_fallback_icon(256)
            img.save(PNG_PATH, format="PNG")
    else:
        img = draw_fallback_icon(256)
        img.save(PNG_PATH, format="PNG")

    # 导出多尺寸 Windows ICO 图标
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ICO_PATH, format="ICO", sizes=icon_sizes)
    return img


if __name__ == "__main__":
    icon = ensure_app_icon()
    print(f"✅ 图标准备就绪: PNG={PNG_PATH}, ICO={ICO_PATH}, 尺寸={icon.size}")
