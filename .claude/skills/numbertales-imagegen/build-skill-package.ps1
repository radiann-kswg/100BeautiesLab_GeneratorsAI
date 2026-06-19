# build-skill-package.ps1
# numbertales-imagegen スキル一式を配布用 .skill（zip）にまとめる。
# .skill は SKILL.md を含むスキルディレクトリの zip アーカイブで、
# Cowork / デスクトップ版 Claude の "Save skill" でインストールできる。
#
# 使い方:
#   ./build-skill-package.ps1                 # 既定: リポジトリ直下に出力
#   ./build-skill-package.ps1 -OutDir C:\tmp  # 出力先を指定
#
# 注意:
#   - repo_path.txt は機種固有のため必ず除外する（配布版は NUMBERTALES_REPO
#     もしくは設置先 4 階層上で解決される）。
#   - .skill はライブリポジトリのスナップショット。常に最新で使うなら
#     install-personal-skill.ps1 のジャンクション方式を推奨。

[CmdletBinding()]
param(
    [string]$OutDir
)
$ErrorActionPreference = 'Stop'

$src  = $PSScriptRoot
$repo = (Resolve-Path (Join-Path $src '..\..\..')).Path
if (-not $OutDir) { $OutDir = $repo }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# 一時ステージング（除外ファイルを抜いた複製を作ってから zip 化）
$stage = Join-Path ([System.IO.Path]::GetTempPath()) ("nt-skill-" + [guid]::NewGuid().ToString('N'))
$pkgDir = Join-Path $stage 'numbertales-imagegen'
New-Item -ItemType Directory -Force -Path $pkgDir | Out-Null

$exclude = @('repo_path.txt')
Get-ChildItem -Path $src -Force | Where-Object {
    $_.Name -notin $exclude -and $_.Extension -ne '.skill'
} | Copy-Item -Destination $pkgDir -Recurse -Force

$zip = Join-Path $OutDir 'numbertales-imagegen.skill'
if (Test-Path $zip) { Remove-Item $zip -Force }

# .skill は zip。拡張子 .skill のままアーカイブを作る。
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip)

Remove-Item $stage -Recurse -Force
Write-Host "[OK] Built: $zip"
Write-Host "  インストール: デスクトップ版 Claude で .skill を開き 'Save skill' を実行、"
Write-Host "  または ~/.claude/skills/ に展開してください。"
