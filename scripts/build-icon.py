#!/usr/bin/env python3
"""Draw the extension icon images/icon.png with the standard library only.
拡張のアイコン images/icon.png を標準ライブラリだけで描く。

Usage / 使い方:
    python3 scripts/build-icon.py

A shallow dish holding five bars of soap in the theme colors, with a couple of bubbles.
Every shape is tested with plain arithmetic and anti-aliased by 3×3 supersampling, so no
image library is needed.

浅いお皿にテーマ色の石けんが 5 つ乗り、泡が浮いている絵。図形はすべて数式で判定し、
3×3 のスーパーサンプリングでアンチエイリアスを付けて PNG に書き出す。
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images" / "icon.png"

SIZE = 256
SS = 3  # samples per pixel edge / 1 ピクセルあたりの縦横サンプル数

# Palette (theme accents and surfaces) / 配色(テーマのアクセント色と地色)
BG = "#dad9eb"
INDIGO = "#422eb0"
DISH = "#fbfafd"
DISH_SHADE = "#cfcde5"
DISH_RIM = "#9996c8"
RED, YELLOW, GREEN, BLUE, PINK = "#cd112f", "#b08a2e", "#2eb07a", "#2e8fb0", "#b02e73"


def hex_rgb(h: str) -> tuple[float, float, float]:
    return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def mix(c: tuple[float, float, float], to: float, amount: float) -> tuple[float, float, float]:
    """Blend toward white (to=255) or black (to=0) / 白または黒へ寄せる"""
    return tuple(v * (1 - amount) + to * amount for v in c)  # type: ignore[return-value]


def soap_color(h: str) -> tuple[float, float, float]:
    return mix(hex_rgb(h), 255, 0.45)


# --- shape tests / 図形の判定 -----------------------------------------------

def in_round_rect(x: float, y: float, x0: float, y0: float, x1: float, y1: float, r: float) -> bool:
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_circle(x: float, y: float, cx: float, cy: float, r: float) -> bool:
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_ellipse(x: float, y: float, cx: float, cy: float, rx: float, ry: float) -> bool:
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def in_soap(x: float, y: float, cx: float, cy: float, w: float, h: float, deg: float, r: float = 10) -> bool:
    """Rotated rounded rectangle / 回転した角丸四角(石けん 1 個)"""
    a = math.radians(-deg)
    dx, dy = x - cx, y - cy
    lx = dx * math.cos(a) - dy * math.sin(a)
    ly = dx * math.sin(a) + dy * math.cos(a)
    return in_round_rect(lx, ly, -w / 2, -h / 2, w / 2, h / 2, r)


# --- composition / 構図 -------------------------------------------------------

CX = 128
DISH_CY, DISH_RX, DISH_RY = 188, 104, 30
# (color, cx, cy, w, h, angle). Back to front / 奥から手前の順
SOAPS = [
    (PINK, CX - 16, 126, 56, 30, -8),
    (GREEN, CX - 46, 150, 62, 34, -14),
    (BLUE, CX + 46, 152, 62, 34, 12),
    (RED, CX - 12, 162, 72, 38, -5),
    (YELLOW, CX + 22, 128, 64, 34, 7),
]
BUBBLES = [(CX + 76, 66, 16), (CX + 96, 100, 9), (CX - 78, 72, 11), (CX - 58, 100, 6)]


def sample(x: float, y: float) -> tuple[float, float, float] | None:
    """Color of one sample point, None outside the rounded square (transparent).
    1 サンプル点の色。背景の角丸四角の外なら None(透明)"""
    if not in_round_rect(x, y, 0, 0, SIZE, SIZE, 56):
        return None
    color = hex_rgb(BG)

    # Dish shadow and body / 皿の影と本体
    if in_ellipse(x, y, CX, DISH_CY + 10, DISH_RX + 6, DISH_RY + 4):
        color = mix(hex_rgb(BG), 0, 0.10)
    if in_ellipse(x, y, CX, DISH_CY, DISH_RX, DISH_RY):
        color = hex_rgb(DISH_RIM)
    if in_ellipse(x, y, CX, DISH_CY, DISH_RX - 5, DISH_RY - 5):
        color = hex_rgb(DISH)
    # Inner well of the dish / 皿のくぼみ
    if in_ellipse(x, y, CX, DISH_CY - 4, DISH_RX - 18, DISH_RY - 13):
        color = hex_rgb(DISH_SHADE)

    # Soaps: shadow, body, bevel, sheen / 石けん: 影・本体・側面・つや
    for hexcol, cx, cy, w, h, deg in SOAPS:
        base = soap_color(hexcol)
        if in_soap(x, y, cx + 3, cy + 5, w, h, deg):
            color = mix(color, 0, 0.18)
        if in_soap(x, y, cx, cy + 5, w, h, deg):
            color = mix(base, 0, 0.22)  # front face / 側面
        if in_soap(x, y, cx, cy, w, h, deg):
            color = base
        if in_soap(x, y, cx - w * 0.16, cy - h * 0.18, w * 0.42, h * 0.28, deg, r=5):
            color = mix(base, 255, 0.45)  # sheen / つや

    # Front lip of the dish overlaps the soap bottoms / 皿の手前の縁が石けんの底に重なる
    if y > DISH_CY and in_ellipse(x, y, CX, DISH_CY, DISH_RX, DISH_RY) and not in_ellipse(x, y, CX, DISH_CY, DISH_RX - 5, DISH_RY - 5):
        color = hex_rgb(DISH_RIM)
    if y > DISH_CY + 6 and in_ellipse(x, y, CX, DISH_CY, DISH_RX - 5, DISH_RY - 5) and not in_ellipse(x, y, CX, DISH_CY - 4, DISH_RX - 18, DISH_RY - 13):
        color = hex_rgb(DISH)

    # Bubbles: thin ring plus highlight / 泡: 細い輪と光
    for bx, by, r in BUBBLES:
        if in_circle(x, y, bx, by, r):
            color = mix(color, 255, 0.35)
        if in_circle(x, y, bx, by, r) and not in_circle(x, y, bx, by, r - 2.5):
            color = hex_rgb(INDIGO) if r > 8 else mix(hex_rgb(INDIGO), 255, 0.3)
        if in_circle(x, y, bx - r * 0.35, by - r * 0.35, r * 0.25):
            color = hex_rgb(DISH)

    return color


def render() -> bytes:
    rows = []
    step = 1 / SS
    for py in range(SIZE):
        row = bytearray([0])  # filter type None / フィルタ種別: None
        for px in range(SIZE):
            acc = [0.0, 0.0, 0.0]
            cover = 0
            for sy in range(SS):
                for sx in range(SS):
                    c = sample(px + (sx + 0.5) * step, py + (sy + 0.5) * step)
                    if c is None:
                        continue
                    cover += 1
                    acc[0] += c[0]
                    acc[1] += c[1]
                    acc[2] += c[2]
            n = SS * SS
            if cover == 0:
                row += bytes((0, 0, 0, 0))
            else:
                row += bytes((round(acc[0] / cover), round(acc[1] / cover), round(acc[2] / cover), round(255 * cover / n)))
        rows.append(bytes(row))
    return b"".join(rows)


def write_png(path: Path, raw: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


if __name__ == "__main__":
    write_png(OUT, render())
    print(f"wrote {OUT.relative_to(ROOT)} ({SIZE}x{SIZE})")
