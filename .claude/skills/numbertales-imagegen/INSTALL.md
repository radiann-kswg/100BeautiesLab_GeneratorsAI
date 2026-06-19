# numbertales-imagegen — 適用手順（実機 Windows で実行）

このフォルダは更新済みのスキル一式（と配布用 `.skill`）です。実機リポジトリへ反映してください。

## 1. リポジトリへ配置
このフォルダの中身を、リポジトリの `.claude/skills/numbertales-imagegen/` へ上書きコピー:
```
SKILL.md / REFERENCE.md / install-personal-skill.ps1 / build-skill-package.ps1 / bin/ntimg.ps1 / bin/ntimg.sh
```
（`INSTALL.md` と `repo_path.txt` はコピー不要。`repo_path.txt` は次の install で自動生成）

## 2. パーソナルスキル化（常に最新・推奨）
```powershell
cd "C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI\.claude\skills\numbertales-imagegen"
./install-personal-skill.ps1
```
→ `~/.claude/skills/numbertales-imagegen` にジャンクションを張り、`repo_path.txt` を生成。
   Settings > Capabilities で Code execution を ON、スキル一覧で `numbertales-imagegen` を ON。

## 3. 動作確認
```powershell
./bin/ntimg.ps1 -Module src.pipeline.natural_parser "コアフォルダ姿の57が図書館で本を読む絵"
```

## 4.（任意）配布用 .skill を作る
```powershell
./build-skill-package.ps1     # numbertales-imagegen.skill を出力（repo_path.txt 除外）
```
同梱の `numbertales-imagegen.skill` をそのまま配布/インストールにも使えます。

## 関連する src 変更（別途コミット）
- `src/utils/dataset.py`: `load_manifest` を `PROJECT_ROOT` 基準に変更（cwd 非依存化）
- `.gitignore`: `repo_path.txt` と `*.skill` を無視
- `docs/setup.md` / `docs/tools.md`: 環境変数とスキルの節を追記
