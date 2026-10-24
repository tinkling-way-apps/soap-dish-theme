#!/usr/bin/env python3
"""Generate the other color variants from Purple by rotating hue.
Purple を原本に、色相を回転させて他の色のテーマを生成する。

Usage / 使い方:
    python3 scripts/build-themes.py

Only colors whose hue falls in TINT_RANGE (the purple band) of themes/purple-color-theme.json are
rotated to each variant's hue. Semantic colors (syntax, error red, added green) lie outside the band
and stay untouched. Replacement is textual, comments included, so the JSONC layout is preserved.

原本 themes/purple-color-theme.json の中で、色相が TINT_RANGE(紫の帯)に入る色だけを
各色の色相へ回転させる。構文色やエラー赤・追加緑などの「意味を持つ色」は帯の外に
あるのでそのまま残る。コメント行も含めてテキストのまま置換するので、JSONC の体裁は崩れない。
"""
from __future__ import annotations

import colorsys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / "themes"
SOURCE = THEMES / "purple-color-theme.json"

# Prefix for the "name" field inside each theme JSON (display labels live in package.json)
# テーマ名の頭に付ける拡張名(テーマ JSON の "name" に入る。表示名は package.json の label)
EXTENSION_NAME = "Soap Dish"

# Hue of the source accent #422eb0; deltas are measured from here
# 原本のアクセント色 #422eb0 の色相。ここを基準に差分を取る
BASE_HUE = 249
# Only colors in this hue band are rotated (purplish backgrounds, borders, grays, accent)
# この色相帯に入る色だけを回転させる(紫がかった背景・境界・灰色・アクセント)
TINT_RANGE = (235, 262)

# Variant name -> (file id, target hue, saturation scale[, paleness])
# Saturation scale applies to rotated colors only; 1.0 keeps Purple's vividness, capped at 100%.
# Paleness (0–1, optional) pushes the light rotated colors (lightness above PALE_FROM) toward white,
# so backgrounds and borders fade while text and accents keep their depth.
# 色名 → (ファイル ID, 目標色相, 彩度の倍率[, 淡さ])
# 彩度の倍率は回転対象の色にだけ掛かる。1.0 で Purple と同じ鮮やかさ、上限は 100% で頭打ち。
# 淡さ(0〜1、省略可)は回転対象のうち明るい色(明度 PALE_FROM 以上)だけを白へ寄せる。
# 背景と境界は薄くなり、文字とアクセントの濃さは保たれる
VARIANTS = {
    "Purple": ("purple", 249, 1.0),
    "Red": ("red", 350, 1.45),
    "Pink": ("pink", 328, 1.0),
    "Yellow": ("yellow", 42, 1.0),
    "Green": ("green", 155, 0.75),
    "Blue": ("blue", 195, 1.0),
    "Blue Gray": ("blue-gray", 218, 1.0),
    "Coffee Cream": ("coffee-cream", 25, 0.65),
    "Cream": ("cream", 40, 0.35, 0.3),
}
PALE_FROM = 0.6

HEX_RE = re.compile(r"#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?\b")
NAME_RE = re.compile(r'("name":\s*")[^"]*(")')


def rotate_hex(rgb_hex: str, delta: float, sat_scale: float = 1.0, pale: float = 0.0) -> str:
    r, g, b = (int(rgb_hex[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    hue = h * 360
    if s == 0 or not (TINT_RANGE[0] <= hue <= TINT_RANGE[1]):
        return rgb_hex
    h2 = ((hue + delta) % 360) / 360
    s2 = min(1.0, s * sat_scale)
    l2 = l + (1 - l) * pale if l >= PALE_FROM else l
    r2, g2, b2 = colorsys.hls_to_rgb(h2, l2, s2)
    out = "".join(f"{round(c * 255):02x}" for c in (r2, g2, b2))
    return out.upper() if rgb_hex.isupper() else out


def build(variant: str, file_id: str, hue: int, sat_scale: float, pale: float, source: str) -> Path:
    delta = hue - BASE_HUE

    def repl(m: re.Match) -> str:
        return "#" + rotate_hex(m.group(1), delta, sat_scale, pale) + (m.group(2) or "")

    body = HEX_RE.sub(repl, source)
    body = NAME_RE.sub(lambda m: f"{m.group(1)}{EXTENSION_NAME}: {variant}{m.group(2)}", body, count=1)
    out = THEMES / f"{file_id}-color-theme.json"
    out.write_text(body, encoding="utf-8")
    return out


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for variant, spec in VARIANTS.items():
        file_id, hue, sat_scale = spec[:3]
        pale = spec[3] if len(spec) > 3 else 0.0
        if (THEMES / f"{file_id}-color-theme.json") == SOURCE:
            continue  # the source is edited by hand / 原本は手で編集する
        out = build(variant, file_id, hue, sat_scale, pale, source)
        print(f"wrote {out.relative_to(ROOT)}  (hue {hue}, sat x{sat_scale}, pale {pale})")


if __name__ == "__main__":
    main()
