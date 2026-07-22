# install-personal-skill.ps1
# numbertales-imagegen を「正本 .agents/skills/ → ミラー .claude/skills/ → パーソナルスキル」の
# 順に配置するインストーラ。
#
#   1. 正本 .agents/skills/numbertales-imagegen/ を確定（.skill 展開版から実行された場合は取り込む）
#   2. repo_path.txt にライブリポジトリの絶対パスを記録
#   3. scripts/sync-agent-skills.ps1 で .claude/skills/ へミラー
#   4. ~/.claude/skills/numbertales-imagegen からジャンクションを張る
#
# ジャンクションなので "git pull" + 同期で SKILL.md 等が自動的に最新化される
# （= 作業フォルダの更新がパーソナルスキルにも常に反映される）。
#
# 使い方（管理者権限不要。ジャンクションは一般ユーザーでも作成可）:
#   1. PowerShell を開く
#   2. このフォルダから実行:  ./install-personal-skill.ps1
#
# アンインストール: ~/.claude/skills/numbertales-imagegen を削除
#   （ジャンクションのみ削除され、リポジトリ側の実体は残る）

[CmdletBinding()]
param(
    # Codex のパーソナルスキル置き場へもジャンクションを張る（既定 OFF）。
    # 参照先ディレクトリは Codex のバージョンによって異なるため、
    # 使う前に実機の Codex がどこを見ているか確認すること。
    [switch]$LinkCodexPersonal,
    [string]$CodexPersonalDir = (Join-Path $env:USERPROFILE '.codex\skills')
)

$ErrorActionPreference = 'Stop'

# --- パス解決 ---------------------------------------------------------------
$src  = (Resolve-Path $PSScriptRoot).Path                  # 実行元（正本 or .skill 展開版）
$repo = (Resolve-Path (Join-Path $src '..\..\..')).Path    # リポジトリルート（3 階層上）

if (-not (Test-Path (Join-Path $repo 'src\pipeline\image_pipeline.py'))) {
    Write-Error "リポジトリルートを特定できません: $repo （src\pipeline\image_pipeline.py が無い）"
    exit 2
}
Write-Host "Repo root: $repo"

# --- 1) 正本 (.agents/skills/) を確定 ---------------------------------------
$canonical = Join-Path $repo '.agents\skills\numbertales-imagegen'
New-Item -ItemType Directory -Force -Path $canonical          | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $canonical 'bin') | Out-Null

if ($src.TrimEnd('\') -ne $canonical.TrimEnd('\')) {
    # .skill 展開版など、正本の外から実行された場合のみ取り込む
    foreach ($f in @('SKILL.md', 'REFERENCE.md', 'INSTALL.md', 'build-skill-package.ps1', 'install-personal-skill.ps1')) {
        $p = Join-Path $src $f
        if (Test-Path $p) { Copy-Item $p $canonical -Force }
    }
    Copy-Item (Join-Path $src 'bin\*') (Join-Path $canonical 'bin') -Force -Recurse
    Write-Host "[OK] 正本へ取り込み: $canonical"
}
else {
    Write-Host "[OK] 正本から実行中: $canonical"
}

# --- 2) repo_path.txt にライブリポジトリの絶対パスを記録 --------------------
# ランチャー(ntimg.ps1/.sh) と .skill 配布版が、任意の cwd / 配置先からでも
# 常にこのリポジトリ（最新の機能）を指せるようにするための基準ファイル。
Set-Content -Path (Join-Path $canonical 'repo_path.txt') -Value $repo -NoNewline -Encoding utf8
Write-Host "[OK] repo_path.txt -> $repo"

# --- 3) .claude/skills/ へミラー同期 ----------------------------------------
$syncScript = Join-Path $repo 'scripts\sync-agent-skills.ps1'
if (-not (Test-Path $syncScript)) {
    Write-Error "同期スクリプトが見つかりません: $syncScript"
    exit 2
}
& $syncScript -Apply
if ($LASTEXITCODE -ne 0) {
    Write-Error "ミラー同期に失敗しました (exit $LASTEXITCODE)"
    exit 1
}

$mirror = Join-Path $repo '.claude\skills\numbertales-imagegen'
Set-Content -Path (Join-Path $mirror 'repo_path.txt') -Value $repo -NoNewline -Encoding utf8

# --- 4) ~/.claude/skills からジャンクション（パーソナルスキル） -------------
function New-SkillJunction {
    param([string]$PersonalDir, [string]$Target, [string]$Label)
    New-Item -ItemType Directory -Force -Path $PersonalDir | Out-Null
    $link = Join-Path $PersonalDir 'numbertales-imagegen'
    if (Test-Path $link) {
        Write-Host "[i] Replacing existing link/folder: $link"
        Remove-Item $link -Force -Recurse
    }
    New-Item -ItemType Junction -Path $link -Target $Target | Out-Null
    Write-Host "[OK] $Label junction: $link  ->  $Target"
}

New-SkillJunction -PersonalDir (Join-Path $env:USERPROFILE '.claude\skills') -Target $mirror -Label 'Claude'

if ($LinkCodexPersonal) {
    New-SkillJunction -PersonalDir $CodexPersonalDir -Target $canonical -Label 'Codex'
}
else {
    Write-Host "[i] Codex はリポジトリ内 .agents/skills/ をプロジェクトスキルとして直接読むため、"
    Write-Host "    パーソナル化は不要です（必要なら -LinkCodexPersonal を付けて再実行）。"
}

Write-Host ""
Write-Host "Done! Settings > Capabilities で Code execution を有効化し、"
Write-Host "スキル一覧の 'numbertales-imagegen' を ON にしてください。"
Write-Host "以後 'git pull' + sync-agent-skills.ps1 -Apply で SKILL.md / ランチャーも最新化されます。"
