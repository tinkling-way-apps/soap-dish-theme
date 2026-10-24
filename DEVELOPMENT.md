# Development

[English](#english) | [日本語](#日本語)

## English

**Edit Purple by hand; regenerate the other eight.** `themes/purple-color-theme.json` is the only theme file meant to be edited. The rest are built from it:

```bash
python3 scripts/build-themes.py
```

- `VARIANTS` in `scripts/build-themes.py` lists each variant as `(file id, hue, saturation scale[, paleness])`. Add a line there and register the theme in `package.json` under `contributes.themes` to add a variant.
- Only colors whose hue falls inside `TINT_RANGE` (235°–262° in Purple: backgrounds, borders, purplish grays, the accent) are rotated. Colors outside the band stay the same in every variant.
- Saturation scale multiplies the saturation of rotated colors. Paleness (0–1, optional) pushes only the light rotated colors (lightness ≥ 60%) toward white, so a background can fade without washing out text or accent.
- The generated files are overwritten on every run.

The icon is drawn by `scripts/build-icon.py` with the Python standard library only. Change the composition there and rerun it to refresh `images/icon.png`.

To try a change, open this folder in VS Code and press `F5`; edits to `themes/*.json` apply live in the Extension Development Host. `Developer: Inspect Editor Tokens and Scopes` shows which scope and color a token gets. To package:

```bash
npx --yes @vscode/vsce package --out dist/soap-dish-0.0.1.vsix
```

Theme files are JSONC: comments and trailing commas are allowed, and a long list of unset keys is left commented out at the end of each file. Later rules in `tokenColors` win over earlier ones.

## 日本語

**Purple だけを手で編集し、他の 8 色はスクリプトで作り直す。** 手で編集するテーマファイルは `themes/purple-color-theme.json` だけで、残りはそこから生成する。

```bash
python3 scripts/build-themes.py
```

- `scripts/build-themes.py` の `VARIANTS` に各色を `(ファイル ID, 色相, 彩度の倍率[, 淡さ])` で並べている。色を足すときはここに 1 行足し、`package.json` の `contributes.themes` にも登録する
- 回転するのは色相が `TINT_RANGE`(Purple の 235°〜262°。背景・境界・紫がかった灰・アクセント)に入る色だけ。帯の外の色は全色共通になる
- 彩度の倍率は回転対象の色の彩度に掛かる。淡さ(0〜1、省略可)は回転対象のうち明るい色(明度 60% 以上)だけを白へ寄せるので、文字やアクセントを薄めずに背景だけ淡くできる
- 生成されたファイルは実行のたびに上書きされる

アイコンは `scripts/build-icon.py` が Python の標準ライブラリだけで描く。構図を変えたら再実行して `images/icon.png` を作り直す。

試すときは、このフォルダを VS Code で開いて `F5`。拡張機能開発ホストで `themes/*.json` の編集が即時反映される。`Developer: Inspect Editor Tokens and Scopes` でトークンのスコープと適用色を見られる。パッケージするには:

```bash
npx --yes @vscode/vsce package --out dist/soap-dish-0.0.1.vsix
```

テーマファイルは JSONC で、コメントと末尾カンマが使える。各ファイルの末尾には未設定のキーがコメントアウトのまま並んでいる。`tokenColors` は後に書いたルールが勝つ。
