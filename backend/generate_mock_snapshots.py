"""
生成模拟缺陷图片（用于测试报告中的证据照片功能）
使用 Pillow 生成带有缺陷模拟效果的织物截图。
"""

import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SNAPSHOT_DIR = Path(__file__).parent / "snapshots" / "defects"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def generate_fabric_background(width=640, height=480):
    """生成模拟织物纹理背景"""
    img = Image.new("RGB", (width, height), color=(235, 228, 215))
    draw = ImageDraw.Draw(img)

    # 绘制织物经纬纹理线条
    for x in range(0, width, 6):
        opacity = random.randint(190, 215)
        draw.line([(x, 0), (x, height)], fill=(opacity, opacity - 10, opacity - 20), width=1)
    for y in range(0, height, 6):
        opacity = random.randint(200, 225)
        draw.line([(0, y), (width, y)], fill=(opacity, opacity - 5, opacity - 15), width=1)

    return img


def generate_hole_image(filename: str):
    """生成破洞缺陷模拟图"""
    img = generate_fabric_background()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    cx, cy = w // 2 + random.randint(-30, 30), h // 2 + random.randint(-30, 30)
    r = random.randint(12, 22)

    # 破洞：黑色不规则圆
    for i in range(3):
        offset = random.randint(-3, 3)
        draw.ellipse([cx - r + offset, cy - r + offset, cx + r + offset, cy + r + offset],
                     fill=(10, 5, 5), outline=(60, 40, 30), width=2)
    # 边缘纤维脱落效果
    for _ in range(20):
        angle = random.uniform(0, 3.14 * 2)
        length = random.randint(r, r + 15)
        import math
        ex = int(cx + math.cos(angle) * length)
        ey = int(cy + math.sin(angle) * length)
        draw.line([(cx, cy), (ex, ey)], fill=(80, 60, 40), width=1)

    # 标注框
    draw.rectangle([cx - r - 20, cy - r - 20, cx + r + 20, cy + r + 20],
                   outline=(255, 50, 50), width=3)
    draw.text((cx - r - 18, cy - r - 38), "HOLE [4pt]", fill=(255, 50, 50))

    img.save(SNAPSHOT_DIR / filename)
    return str(SNAPSHOT_DIR / filename)


def generate_stain_image(filename: str, length_cm: float = 30.0):
    """生成污渍缺陷模拟图"""
    img = generate_fabric_background()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    cx, cy = w // 2 + random.randint(-40, 40), h // 2 + random.randint(-30, 30)
    # 不规则污渍形状
    stain_w = random.randint(60, 130)
    stain_h = random.randint(20, 50)
    for _ in range(5):
        ox, oy = random.randint(-15, 15), random.randint(-10, 10)
        r_col = random.randint(80, 120)
        draw.ellipse([cx - stain_w // 2 + ox, cy - stain_h // 2 + oy,
                      cx + stain_w // 2 + ox, cy + stain_h // 2 + oy],
                     fill=(r_col, r_col - 30, r_col - 50))

    draw.rectangle([cx - stain_w // 2 - 10, cy - stain_h // 2 - 10,
                    cx + stain_w // 2 + 10, cy + stain_h // 2 + 10],
                   outline=(255, 160, 0), width=3)
    draw.text((cx - stain_w // 2 - 8, cy - stain_h // 2 - 28),
              f"STAIN {length_cm:.0f}cm [4pt]", fill=(255, 160, 0))

    img.save(SNAPSHOT_DIR / filename)
    return str(SNAPSHOT_DIR / filename)


def generate_warp_break_image(filename: str, length_cm: float = 20.0):
    """生成断经缺陷模拟图"""
    img = generate_fabric_background()
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # 竖向断经线
    cx = w // 2 + random.randint(-50, 50)
    line_len = random.randint(80, 160)
    cy_top = h // 2 - line_len // 2
    cy_bot = h // 2 + line_len // 2

    # 主断裂线（白色缺失）
    draw.line([(cx, cy_top), (cx, cy_bot)], fill=(250, 248, 240), width=5)
    # 周围纤维乱散
    for _ in range(10):
        sx = cx + random.randint(-3, 3)
        sy = cy_top + random.randint(0, line_len)
        draw.line([(sx, sy), (sx + random.randint(-8, 8), sy + random.randint(-8, 8))],
                  fill=(200, 190, 170), width=1)

    draw.rectangle([cx - 25, cy_top - 10, cx + 25, cy_bot + 10],
                   outline=(255, 80, 80), width=2)
    draw.text((cx - 23, cy_top - 28), f"WARP {length_cm:.0f}cm [3pt]", fill=(255, 80, 80))

    img.save(SNAPSHOT_DIR / filename)
    return str(SNAPSHOT_DIR / filename)


def generate_all_mock_snapshots():
    """生成所有测试缺陷照片"""
    snapshots = {
        "defect_hole_01.jpg": generate_hole_image("defect_hole_01.jpg"),
        "defect_hole_02.jpg": generate_hole_image("defect_hole_02.jpg"),
        "defect_stain_35cm.jpg": generate_stain_image("defect_stain_35cm.jpg", 35.0),
        "defect_warp_20cm.jpg": generate_warp_break_image("defect_warp_20cm.jpg", 20.0),
    }
    print(f"✅ 成功生成 {len(snapshots)} 张模拟缺陷图片:")
    for name, path in snapshots.items():
        print(f"   {name} -> {path}")
    return snapshots


if __name__ == "__main__":
    generate_all_mock_snapshots()
