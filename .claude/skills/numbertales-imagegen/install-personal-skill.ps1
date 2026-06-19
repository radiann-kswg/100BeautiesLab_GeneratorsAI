# install-personal-skill.ps1
# numbertales-imagegen をプロジェクトスキルとして配置し、
# ~/.claude/skills/numbertales-imagegen からジャンクションを張って
# パーソナルスキルとしても使えるようにする。
# ジャンクションなので "git pull" で SKILL.md 等が自動的に最新化される
# （= 作業フォルダの更新がパーソナルスキルにも常に反映される）。
#
# 使い方（管理者権限不要。ジャンクションは一般ユーザーでも作成可）:
#   1. PowerShell を開く
#   2. このフォルダから実行:  ./install-personal-skill.ps1
#
# アンインストール: ~/.claude/skills/numbertales-imagegen を削除
#   （ジャンクションのみ削除され、リポジトリ側の実体は残る）

$ErrorActionPreference = 'Stop'

# --- パス解決 ---------------------------------------------------------------
$src  = $PSScriptRoot                                      # .claude\skills\numbertales-imagegen
$repo = (Resolve-Path (Join-Path $src '..\..\..')).Path    # リポジトリルート（3 階層上）

if (-not (Test-Path (Join-Path $repo 'src\pipeline\image_pipeline.py'))) {
    Write-Error "リポジトリルートを特定できません: $repo （src\pipeline\image_pipeline.py が無い）"
    exit 2
}
Write-Host "Repo root: $repo"

# --- 1) プロジェクトスキルとして .claude/skills 配下に配置 -------------------
$projSkill = Join-Path $repo '.claude\skills\numbertales-imagegen'
New-Item -ItemType Directory -Force -Path $projSkill          | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $projSkill 'bin') | Out-Null
Copy-Item (Join-Path $src 'SKILL.md')                 $projSkill -Force
Copy-Item (Join-Path $src 'REFERENCE.md')             $projSkill -Force
Copy-Item (Join-Path $src 'build-skill-package.ps1')  $projSkill -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $src 'bin\*')                    (Join-Path $projSkill 'bin') -Force -Recurse
Write-Host "[OK] Project skill placed: $projSkill"

# --- 2) repo_path.txt にライブリポジトリの絶対パスを記録 --------------------
# ランチャー(ntimg.ps1/.sh) と .skill 配布版が、任意の cwd / 配置先からでも
# 常にこのリポジトリ（最新の機能）を指せるようにするための基準ファイル。
Set-Content -Path (Join-Path $projSkill 'repo_path.txt') -Value $repo -NoNewline -Encoding utf8
Write-Host "[OK] repo_path.txt -> $repo"

# --- 3) ~/.claude/skills からジャンクション（パーソナルスキル） -------------
$personalDir = Join-Path $env:USERPROFILE '.claude\skills'
New-Item -ItemType Directory -Force -Path $personalDir | Out-Null

$link = Join-Path $personalDir 'numbertales-imagegen'
if (Test-Path $link) {
    Write-Host "[i] Replacing existing link/folder: $link"
    Remove-Item $link -Force -Recurse
}
New-Item -ItemType Junction -Path $link -Target $projSkill | Out-Null
Write-Host "[OK] Personal skill junction: $link  ->  $projSkill"

Write-Host ""
Write-Host "Done! Settings > Capabilities で Code execution を有効化し、"
Write-Host "スキル一覧の 'numbertales-imagegen' を ON にしてください。"
Write-Host "以後 'git pull' で SKILL.md / ランチャーも自動更新されます。"
