# ntimg.ps1 — numbertales-imagegen launcher (Windows / 実機のローカル CLI エージェント)
#
# 役割: パーソナルスキルが任意の cwd から呼ばれても、リポジトリルートを
#       自動解決して image_pipeline などを実行できるようにするラッパー。
#
# リポジトリルート解決順:
#   1. 環境変数 NUMBERTALES_REPO（明示指定。最優先）
#   2. スキル直下 repo_path.txt（install-personal-skill.ps1 が記録）
#   3. このスクリプト位置から 4 階層上（in-repo / junction 配置時）
#   検証: src\pipeline\image_pipeline.py を含むディレクトリのみ採用。
#
# 使い方（例）:
#   ./ntimg.ps1 --num 57 --form corefolder --skip-canva
#   ./ntimg.ps1 --natural "コアフォルダ姿の57が図書館で本を読んでいる絵"
#   ./ntimg.ps1 -Module src.batch_generate --nums 15,57 --forms both --dry-run
#
# 既定モジュールは src.pipeline.image_pipeline。-Module で切替可能。

[CmdletBinding()]
param(
    [string]$Module = 'src.pipeline.image_pipeline',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PipelineArgs
)

$ErrorActionPreference = 'Stop'

function Test-RepoRoot([string]$path) {
    if ([string]::IsNullOrWhiteSpace($path)) { return $false }
    return Test-Path (Join-Path $path 'src\pipeline\image_pipeline.py')
}

$skillRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path   # numbertales-imagegen\
$repo = $null

# 1) 環境変数 NUMBERTALES_REPO
if (Test-RepoRoot $env:NUMBERTALES_REPO) {
    $repo = (Resolve-Path $env:NUMBERTALES_REPO).Path
}

# 2) repo_path.txt
if (-not $repo) {
    $cfg = Join-Path $skillRoot 'repo_path.txt'
    if (Test-Path $cfg) {
        $candidate = (Get-Content $cfg -Raw).Trim()
        if (Test-RepoRoot $candidate) { $repo = (Resolve-Path $candidate).Path }
    }
}

# 3) スクリプト位置から 4 階層上（bin -> skill -> skills -> .agents|.claude -> repo）
if (-not $repo) {
    $candidate = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
    if (Test-RepoRoot $candidate) { $repo = $candidate }
}

if (-not $repo) {
    Write-Error @"
リポジトリルートを解決できませんでした。次のいずれかで指定してください:
  - 環境変数 NUMBERTALES_REPO にリポジトリの絶対パスを設定
  - スキル直下に repo_path.txt を作成（install-personal-skill.ps1 が自動作成）
検証条件: 指定パスの src\pipeline\image_pipeline.py が存在すること。
"@
    exit 2
}

# Python 実行（cwd 非依存。PROJECT_ROOT / PYTHONPATH を明示）
$env:PROJECT_ROOT = $repo
if ($env:PYTHONPATH) { $env:PYTHONPATH = "$repo;$env:PYTHONPATH" } else { $env:PYTHONPATH = $repo }

$py = if (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { 'py' }

Write-Host "[ntimg] repo   = $repo"
Write-Host "[ntimg] module = $Module"
Push-Location $repo
try {
    & $py -m $Module @PipelineArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
