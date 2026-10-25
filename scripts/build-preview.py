#!/usr/bin/env python3
"""Draw schematic VS Code windows in each theme's colors.
各テーマの色で VS Code の窓を模式的に描く。

Usage / 使い方:
    python3 scripts/build-preview.py

For every theme registered in package.json, reads its JSONC and paints the title bar, activity bar,
side bar, tab strip, editor with indent guides and token-colored "code" bars, panel and status bar
as flat rectangles into images/preview-<id>.png. Then tiles all of them at half size into
images/preview.png. There is no text rendering; words are drawn as bars. It exists so the themes
can be compared at a glance without opening VS Code, and so the README has pictures.
The previews are not packaged into the .vsix; the README links to them on GitHub.

package.json に登録された各テーマの JSONC を読み、タイトルバー・アクティビティバー・サイドバー・
タブ列・エディタ(インデントガイドとトークン色の「コード」の帯)・パネル・ステータスバーを
平らな矩形で images/preview-<id>.png に塗る。続けて全部を半分の大きさで並べた images/preview.png を
作る。文字は描かず、単語は帯で表す。VS Code を開かずに 9 色を見比べるため、そして README に
絵を載せるためにある。プレビューは .vsix には含めず、README から GitHub 上の画像を参照する。
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "package.json"
IMAGES = ROOT / "images"
SHEET = IMAGES / "preview.png"

W, H = 960, 600
SHEET_COLUMNS = 3
SHEET_GAP = 12
SHEET_BG = (255, 255, 255)
Color = tuple[int, int, int]


def parse_jsonc(text: str) -> dict:
    """Drop full-line // comments and trailing commas. Inline comments are not used in these files.
    行頭の // コメントと末尾カンマを落とす。これらのファイルは行中コメントを使っていない"""
    no_comments = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", no_comments))


class Canvas:
    def __init__(self, w: int, h: int, bg: Color) -> None:
        self.w, self.h = w, h
        self.rows = [bytearray(bytes(bg) * w) for _ in range(h)]

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: str) -> None:
        """Fill [x0,x1)×[y0,y1) with a #rrggbb or #rrggbbaa color, compositing alpha over what is there.
        #rrggbb または #rrggbbaa で矩形を塗る。アルファは下の色に重ねる"""
        x0, x1 = max(0, x0), min(self.w, x1)
        y0, y1 = max(0, y0), min(self.h, y1)
        if x0 >= x1 or y0 >= y1:
            return
        rgb, a = split(color)
        if a >= 255:
            run = bytes(rgb) * (x1 - x0)
            for y in range(y0, y1):
                self.rows[y][3 * x0 : 3 * x1] = run
            return
        f = a / 255
        for y in range(y0, y1):
            row = self.rows[y]
            for x in range(x0, x1):
                i = 3 * x
                row[i] = round(row[i] * (1 - f) + rgb[0] * f)
                row[i + 1] = round(row[i + 1] * (1 - f) + rgb[1] * f)
                row[i + 2] = round(row[i + 2] * (1 - f) + rgb[2] * f)

    def blit_half(self, other: "Canvas", x0: int, y0: int) -> None:
        """Paste another canvas at half size (2×2 average) with its top-left at (x0, y0).
        別のキャンバスを半分の大きさ(2×2 平均)で (x0, y0) に貼る"""
        for y in range(other.h // 2):
            dst = self.rows[y0 + y]
            a, b = other.rows[2 * y], other.rows[2 * y + 1]
            for x in range(other.w // 2):
                i = 6 * x
                j = 3 * (x0 + x)
                dst[j] = (a[i] + a[i + 3] + b[i] + b[i + 3]) >> 2
                dst[j + 1] = (a[i + 1] + a[i + 4] + b[i + 1] + b[i + 4]) >> 2
                dst[j + 2] = (a[i + 2] + a[i + 5] + b[i + 2] + b[i + 5]) >> 2

    def png(self) -> bytes:
        raw = b"".join(b"\x00" + bytes(r) for r in self.rows)

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)  # 8-bit RGB
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def split(color: str) -> tuple[Color, int]:
    h = color.lstrip("#")
    rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    a = int(h[6:8], 16) if len(h) == 8 else 255
    return rgb, a  # type: ignore[return-value]


def token_color(theme: dict, scope: str, fallback: str) -> str:
    """Foreground of the last tokenColors rule whose scope list contains exactly this scope.
    Later rules win in VS Code, so the last match is the one that applies.
    scope の一覧にこのスコープがそのまま入っている最後の tokenColors ルールの前景色。
    VS Code では後のルールが勝つので、最後に一致したものが効く"""
    found = fallback
    for rule in theme["tokenColors"]:
        scopes = rule.get("scope", [])
        if isinstance(scopes, str):
            scopes = [s.strip() for s in scopes.split(",")]
        if scope in scopes and "foreground" in rule.get("settings", {}):
            found = rule["settings"]["foreground"]
    return found


def draw(theme: dict) -> Canvas:
    c = theme["colors"]

    def col(key: str, default: str = "#ff00ff") -> str:
        return c.get(key, default)

    fg = col("editor.foreground")
    kw = token_color(theme, "keyword.control", fg)
    st = token_color(theme, "string", fg)
    fn = token_color(theme, "entity.name.function", fg)
    ty = token_color(theme, "entity.name.type", fg)
    cm = token_color(theme, "comment", fg)
    nm = token_color(theme, "constant.numeric", fg)
    va = token_color(theme, "variable", fg)
    # Soap Dish has one indent guide color; fall back along the usual keys
    # Soap Dish のインデントガイドは 1 色。よくあるキーの順に探す
    guide = col("editorIndentGuide.background1", col("editorIndentGuide.background", fg + "33"))

    bg_rgb, _ = split(col("editor.background"))
    cv = Canvas(W, H, bg_rgb)

    TITLE_H, STATUS_H, ACT_W, SIDE_W, TAB_H, PANEL_Y = 30, 24, 48, 220, 36, 430
    EDITOR_X = ACT_W + SIDE_W
    BODY_Y0, BODY_Y1 = TITLE_H, H - STATUS_H

    # Title bar / タイトルバー
    cv.rect(0, 0, W, TITLE_H, col("titleBar.activeBackground"))
    cv.rect(0, TITLE_H - 1, W, TITLE_H, col("titleBar.border"))
    for i, x in enumerate((14, 36, 58)):  # traffic lights / 信号
        cv.rect(x, 9, x + 12, 21, ("#ec6a5e", "#f4bf4f", "#61c554")[i])
    cv.rect(W // 2 - 130, 7, W // 2 + 130, TITLE_H - 7, col("commandCenter.background"))
    cv.rect(W // 2 - 130, 7, W // 2 + 130, 8, col("commandCenter.border"))
    cv.rect(W // 2 - 130, TITLE_H - 8, W // 2 + 130, TITLE_H - 7, col("commandCenter.border"))
    cv.rect(W // 2 - 60, 14, W // 2 + 60, 17, col("titleBar.activeForeground"))

    # Activity bar / アクティビティバー
    cv.rect(0, BODY_Y0, ACT_W, BODY_Y1, col("activityBar.background"))
    cv.rect(ACT_W - 1, BODY_Y0, ACT_W, BODY_Y1, col("activityBar.border"))
    for i in range(5):
        y = BODY_Y0 + 14 + i * 48
        icon = col("activityBar.foreground") if i == 0 else col("activityBar.inactiveForeground")
        cv.rect(14, y, 34, y + 20, icon)
        if i == 0:
            cv.rect(0, y - 8, 2, y + 28, col("activityBar.activeBorder"))
    bx, by = 26, BODY_Y0 + 14 + 2 * 48 + 12
    cv.rect(bx, by, bx + 14, by + 12, col("activityBarBadge.background"))

    # Side bar / サイドバー
    cv.rect(ACT_W, BODY_Y0, EDITOR_X, BODY_Y1, col("sideBar.background"))
    cv.rect(EDITOR_X - 1, BODY_Y0, EDITOR_X, BODY_Y1, col("sideBar.border"))
    cv.rect(ACT_W + 14, BODY_Y0 + 12, ACT_W + 90, BODY_Y0 + 20, col("sideBarTitle.foreground"))
    cv.rect(ACT_W, BODY_Y0 + 34, EDITOR_X - 1, BODY_Y0 + 56, col("sideBarSectionHeader.background"))
    cv.rect(ACT_W, BODY_Y0 + 56, EDITOR_X - 1, BODY_Y0 + 57, col("sideBarSectionHeader.border"))
    cv.rect(ACT_W + 14, BODY_Y0 + 41, ACT_W + 110, BODY_Y0 + 49, col("sideBarSectionHeader.foreground"))
    rows = [(0, 70), (1, 90), (1, 60), (2, 80), (2, 110), (1, 75), (0, 95), (1, 65), (1, 100), (0, 85)]
    for i, (depth, width) in enumerate(rows):
        y = BODY_Y0 + 66 + i * 24
        if i == 4:
            cv.rect(ACT_W, y - 4, EDITOR_X - 1, y + 16, col("list.activeSelectionBackground"))
        if i == 7:
            cv.rect(ACT_W, y - 4, EDITOR_X - 1, y + 16, col("list.hoverBackground"))
        if depth:
            cv.rect(ACT_W + 10 + depth * 8, y - 4, ACT_W + 11 + depth * 8, y + 16, col("tree.indentGuidesStroke"))
        x = ACT_W + 18 + depth * 14
        tint = col("gitDecoration.modifiedResourceForeground") if i == 2 else col("sideBar.foreground")
        cv.rect(x, y + 2, x + width, y + 10, tint)

    # Tab strip / タブ列
    cv.rect(EDITOR_X, BODY_Y0, W, BODY_Y0 + TAB_H, col("editorGroupHeader.tabsBackground"))
    cv.rect(EDITOR_X, BODY_Y0 + TAB_H - 1, W, BODY_Y0 + TAB_H, col("editorGroupHeader.tabsBorder"))
    x = EDITOR_X
    for i, w in enumerate((130, 110, 120)):
        if i == 0:
            cv.rect(x, BODY_Y0, x + w, BODY_Y0 + TAB_H, col("tab.activeBackground"))
            cv.rect(x, BODY_Y0, x + w, BODY_Y0 + 2, col("tab.activeBorderTop"))
            cv.rect(x + 14, BODY_Y0 + 14, x + w - 24, BODY_Y0 + 22, col("tab.activeForeground"))
        else:
            cv.rect(x, BODY_Y0, x + w, BODY_Y0 + TAB_H, col("tab.inactiveBackground"))
            cv.rect(x + 14, BODY_Y0 + 14, x + w - 24, BODY_Y0 + 22, col("tab.inactiveForeground"))
        cv.rect(x + w - 1, BODY_Y0, x + w, BODY_Y0 + TAB_H, col("tab.border"))
        x += w
    # Breadcrumb / パンくず
    cv.rect(EDITOR_X, BODY_Y0 + TAB_H, W, BODY_Y0 + TAB_H + 22, col("breadcrumb.background"))
    cv.rect(EDITOR_X + 16, BODY_Y0 + TAB_H + 8, EDITOR_X + 200, BODY_Y0 + TAB_H + 13, col("editorLineNumber.activeForeground"))

    # Editor / エディタ
    ED_Y0 = BODY_Y0 + TAB_H + 22
    cv.rect(EDITOR_X, ED_Y0, W, PANEL_Y, col("editor.background"))
    gutter = EDITOR_X + 56
    code_x = gutter + 16
    line_h = 22
    # (indent, [(color, width), ...]) one line of pretend code; width 10 is a bracket
    # (インデント, [(色, 幅), ...]) 1 行分のつもりのコード。幅 10 は括弧
    lines = [
        (0, [(cm, 220)]),
        (0, [(kw, 48), (fn, 90), (fg, 10), (va, 60), (fg, 14), (ty, 50), (fg, 10)]),
        (1, [(kw, 40), (va, 70), (fg, 12), (nm, 30)]),
        (1, [(kw, 36), (fg, 10), (va, 54), (fg, 24), (st, 110), (fg, 10)]),
        (2, [(kw, 50), (fn, 80), (fg, 10), (va, 40), (fg, 10)]),
        (3, [(va, 70), (fg, 12), (st, 150)]),
        (3, [(kw, 48), (va, 60), (fg, 12), (nm, 24), (fg, 14), (nm, 36)]),
        (4, [(fn, 90), (fg, 10), (va, 46), (fg, 10)]),
        (3, [(fg, 10)]),
        (2, [(fg, 10)]),
        (1, [(kw, 52), (va, 70)]),
        (0, [(fg, 10)]),
        (0, []),
        (0, [(cm, 160)]),
        (0, [(kw, 40), (ty, 110), (fg, 10)]),
        (1, [(va, 60), (fg, 10), (ty, 50)]),
    ]
    for i, (indent, parts) in enumerate(lines):
        y = ED_Y0 + 10 + i * line_h
        if i == 6:
            cv.rect(EDITOR_X, y - 4, W, y + line_h - 4, col("editor.lineHighlightBackground"))
            cv.rect(EDITOR_X, y - 4, W, y - 3, col("editor.lineHighlightBorder"))
            cv.rect(EDITOR_X, y + line_h - 5, W, y + line_h - 4, col("editor.lineHighlightBorder"))
        num = col("editorLineNumber.activeForeground") if i == 6 else col("editorLineNumber.foreground")
        cv.rect(gutter - 24, y + 4, gutter - 6, y + 10, num)
        for d in range(indent):
            gx = code_x + d * 28
            cv.rect(gx, y - 4, gx + 2, y + line_h - 4, guide)
        x = code_x + indent * 28
        for color, width in parts:
            if width == 10:  # a bracket: paint it in the depth's bracket-pair color / 括弧は深さの対の色
                color = col(f"editorBracketHighlight.foreground{indent % 6 + 1}", fg)
            cv.rect(x, y + 2, x + width, y + 12, color)
            x += width + 8
        if i == 5:
            cv.rect(code_x + indent * 28 + 82, y + 2, code_x + indent * 28 + 232, y + 12, col("editor.selectionBackground"))
    # Cursor / カーソル
    cy = ED_Y0 + 10 + 6 * line_h
    cv.rect(code_x + 3 * 28 + 200, cy - 2, code_x + 3 * 28 + 202, cy + 16, col("editorCursor.foreground"))
    # Minimap and scrollbar / ミニマップとスクロールバー
    cv.rect(W - 70, ED_Y0, W - 14, PANEL_Y, col("minimap.background", col("editor.background")))
    for i, (indent, parts) in enumerate(lines):
        y = ED_Y0 + 8 + i * 4
        total = sum(w for _, w in parts) // 6
        if total:
            cv.rect(W - 66 + indent * 3, y, W - 66 + indent * 3 + total, y + 2, fg[:7] + "55")
    cv.rect(W - 14, ED_Y0, W, PANEL_Y, col("editorOverviewRuler.border"))
    cv.rect(W - 13, ED_Y0 + 6, W - 1, ED_Y0 + 90, col("scrollbarSlider.background"))

    # Panel (terminal) / パネル(ターミナル)
    cv.rect(EDITOR_X, PANEL_Y, W, BODY_Y1, col("panel.background"))
    cv.rect(EDITOR_X, PANEL_Y, W, PANEL_Y + 1, col("panel.border"))
    px = EDITOR_X + 16
    for i, w in enumerate((70, 60, 80, 56)):
        color = col("panelTitle.activeForeground") if i == 1 else col("panelTitle.inactiveForeground")
        cv.rect(px, PANEL_Y + 14, px + w, PANEL_Y + 21, color)
        if i == 1:
            cv.rect(px - 6, PANEL_Y + 34, px + w + 6, PANEL_Y + 35, col("panelTitle.activeBorder"))
        px += w + 24
    cv.rect(EDITOR_X, PANEL_Y + 36, W, BODY_Y1, col("terminal.background", col("panel.background")))
    tfg = col("terminal.foreground", fg)
    term = [
        [(col("terminal.ansiGreen"), 60), (tfg, 150)],
        [(tfg, 240)],
        [(col("terminal.ansiBlue"), 90), (tfg, 120)],
        [(col("terminal.ansiRed"), 50), (tfg, 200)],
        [(col("terminal.ansiGreen"), 60), (tfg, 90), (col("terminalCursor.foreground", fg), 8)],
    ]
    for i, parts in enumerate(term):
        y = PANEL_Y + 50 + i * 20
        x = EDITOR_X + 16
        for color, width in parts:
            cv.rect(x, y, x + width, y + 8, color)
            x += width + 8

    # Status bar / ステータスバー
    cv.rect(0, BODY_Y1, W, H, col("statusBar.background"))
    cv.rect(0, BODY_Y1, W, BODY_Y1 + 1, col("statusBar.border"))
    cv.rect(0, BODY_Y1, 40, H, col("statusBarItem.remoteBackground"))
    cv.rect(12, BODY_Y1 + 8, 28, BODY_Y1 + 16, col("statusBarItem.remoteForeground"))
    x = 54
    for w in (60, 40, 90):
        cv.rect(x, BODY_Y1 + 9, x + w, BODY_Y1 + 15, col("statusBar.foreground"))
        x += w + 20
    x = W - 20
    for w in (50, 36, 70, 60):
        x -= w
        cv.rect(x, BODY_Y1 + 9, x + w, BODY_Y1 + 15, col("statusBar.foreground"))
        x -= 20
    cv.rect(x - 70, BODY_Y1, x - 6, H, col("statusBarItem.warningBackground"))
    cv.rect(x - 58, BODY_Y1 + 9, x - 18, BODY_Y1 + 15, col("statusBarItem.warningForeground"))
    return cv


def main() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    entries = package["contributes"]["themes"]
    IMAGES.mkdir(parents=True, exist_ok=True)
    canvases: list[Canvas] = []
    for entry in entries:
        path = ROOT / entry["path"]
        file_id = path.name.replace("-color-theme.json", "")
        theme = parse_jsonc(path.read_text(encoding="utf-8"))
        cv = draw(theme)
        out = IMAGES / f"preview-{file_id}.png"
        out.write_bytes(cv.png())
        print(f"wrote {out.relative_to(ROOT)} ({W}x{H})  {theme['name']}")
        canvases.append(cv)

    # Contact sheet: all themes at half size, SHEET_COLUMNS per row
    # 一覧: 全テーマを半分の大きさで 1 行 SHEET_COLUMNS 枚ずつ並べる
    rows = (len(canvases) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
    cols = min(SHEET_COLUMNS, len(canvases))
    sheet = Canvas(cols * (W // 2) + (cols + 1) * SHEET_GAP, rows * (H // 2) + (rows + 1) * SHEET_GAP, SHEET_BG)
    for i, cv in enumerate(canvases):
        r, cidx = divmod(i, SHEET_COLUMNS)
        sheet.blit_half(cv, SHEET_GAP + cidx * (W // 2 + SHEET_GAP), SHEET_GAP + r * (H // 2 + SHEET_GAP))
    SHEET.write_bytes(sheet.png())
    print(f"wrote {SHEET.relative_to(ROOT)} ({sheet.w}x{sheet.h}, {len(canvases)} themes)")


if __name__ == "__main__":
    main()
