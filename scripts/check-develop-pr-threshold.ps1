<#
.SYNOPSIS
    develop に累積した (既定ブランチ未反映の) 変更量を測り、PR 送付の閾値に達したか判定する。

.DESCRIPTION
    比較範囲は merge-base(origin/<既定ブランチ>, develop)..develop。
      - サブモジュール側 (創作DB側): 変化した gitlink ごとに、サブモジュール内の旧..新 の追加+削除行数を合算
        (ネストのサブモジュールも再帰的に合算)。既定閾値 500 行。
      - 本体側: 親リポジトリの追加+削除行数。gitlink と _tasks/ (日次ログ) は除外。既定閾値 200 行。
    どちらか一方でも閾値以上なら exit 10、未満なら exit 0、エラーは exit 1。
    GeneratorsAI / ShapeChangerAI のどちらにも使えるよう、既定ブランチは origin/HEAD から解決する。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\check-develop-pr-threshold.ps1
    powershell -ExecutionPolicy Bypass -File scripts\check-develop-pr-threshold.ps1 -RepoRoot "C:\Visual Studio Code UserFile\100BeautiesLab_ShapeChangerAI"
#>
[CmdletBinding()]
param(
    [string]$RepoRoot,
    [string]$Head = 'develop',
    [int]$SubmoduleThreshold = 500,
    [int]$BodyThreshold = 200,
    [switch]$NoFetch
)

$ErrorActionPreference = 'Stop'
# PS 5.1 は param 既定値の評価時に $PSScriptRoot が空なので本体で解決する
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }

# git の成功メッセージ (stderr) で PS 5.1 が例外を出さないよう、成否は終了コードで判定する
function Invoke-Git {
    param([Parameter(Mandatory = $true, Position = 0)][string[]]$GitArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = (& git @GitArgs 2>&1 | Out-String)
        return [pscustomobject]@{ ExitCode = $LASTEXITCODE; Output = $out.Trim() }
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

# numstat の追加+削除を合算 (バイナリの "-" は 0 扱い)
function Get-NumstatTotal {
    param([string]$Text)
    $total = 0
    foreach ($line in ($Text -split '\r?\n')) {
        if ($line -match '^(\d+|-)\t(\d+|-)\t') {
            if ($Matches[1] -ne '-') { $total += [int]$Matches[1] }
            if ($Matches[2] -ne '-') { $total += [int]$Matches[2] }
        }
    }
    return $total
}

$Zero = '0' * 40

# repo の old..new で変化した gitlink を列挙し、各サブモジュール内の差分行数を再帰的に集計する
function Measure-Gitlinks {
    param([string]$Repo, [string]$Old, [string]$New, [string]$Prefix = '')
    $rows = @()
    $raw = Invoke-Git @('-C', $Repo, 'diff', '--raw', '--no-abbrev', $Old, $New)
    if ($raw.ExitCode -ne 0) { throw "diff --raw 失敗 ($Repo): $($raw.Output)" }
    foreach ($line in ($raw.Output -split '\r?\n')) {
        if ($line -notmatch '^:(\d{6}) (\d{6}) ([0-9a-f]{40}) ([0-9a-f]{40}) \S+\t(.+)$') { continue }
        if ($Matches[1] -ne '160000' -and $Matches[2] -ne '160000') { continue }
        $smOld = $Matches[3]; $smNew = $Matches[4]; $path = $Matches[5]
        $smRepo = Join-Path $Repo $path
        $label = "$Prefix$path"
        if ($smOld -eq $Zero -or $smNew -eq $Zero) {
            # 追加/削除されたサブモジュールは行数を測れないので 0 とし、備考で知らせる
            $rows += [pscustomobject]@{ Path = $label; Range = "$($smOld.Substring(0,7))..$($smNew.Substring(0,7))"; Lines = 0; Note = 'サブモジュール追加/削除 (行数対象外)' }
            continue
        }
        $num = Invoke-Git @('-C', $smRepo, 'diff', '--numstat', '--ignore-submodules', $smOld, $smNew)
        if ($num.ExitCode -ne 0) {
            $rows += [pscustomobject]@{ Path = $label; Range = "$($smOld.Substring(0,7))..$($smNew.Substring(0,7))"; Lines = 0; Note = '差分を取得できない (未 fetch の可能性)' }
            continue
        }
        $rows += [pscustomobject]@{ Path = $label; Range = "$($smOld.Substring(0,7))..$($smNew.Substring(0,7))"; Lines = (Get-NumstatTotal $num.Output); Note = '' }
        $rows += Measure-Gitlinks -Repo $smRepo -Old $smOld -New $smNew -Prefix "$label/"
    }
    return $rows
}

try {
    if (-not $NoFetch) {
        $f = Invoke-Git @('-C', $RepoRoot, 'fetch', 'origin', '--prune')
        if ($f.ExitCode -ne 0) { Write-Warning "fetch 失敗: $($f.Output)" }
    }
    $baseRef = (Invoke-Git @('-C', $RepoRoot, 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD')).Output
    if (-not $baseRef) { throw 'origin/HEAD を解決できません (git remote set-head origin -a を実行してください)' }
    $mb = Invoke-Git @('-C', $RepoRoot, 'merge-base', $baseRef, $Head)
    if ($mb.ExitCode -ne 0) { throw "merge-base 失敗: $($mb.Output)" }
    $mergeBase = $mb.Output

    $bodyNum = Invoke-Git @('-C', $RepoRoot, 'diff', '--numstat', '--ignore-submodules', $mergeBase, $Head, '--', '.', ':(exclude)_tasks')
    if ($bodyNum.ExitCode -ne 0) { throw "本体側 diff 失敗: $($bodyNum.Output)" }
    $bodyLines = Get-NumstatTotal $bodyNum.Output

    $smRows = @(Measure-Gitlinks -Repo $RepoRoot -Old $mergeBase -New $Head)
    $smLines = ($smRows | Measure-Object -Property Lines -Sum).Sum
    if (-not $smLines) { $smLines = 0 }
}
catch {
    Write-Error $_
    exit 1
}

$commits = (Invoke-Git @('-C', $RepoRoot, 'rev-list', '--count', "$mergeBase..$Head")).Output
$reached = ($smLines -ge $SubmoduleThreshold) -or ($bodyLines -ge $BodyThreshold)

Write-Host "== develop 累積変更量 ==" -ForegroundColor Cyan
Write-Host "リポジトリ : $RepoRoot"
Write-Host "比較範囲   : $baseRef ($($mergeBase.Substring(0,7))) .. $Head  [$commits commits]"
Write-Host ("本体側     : {0} 行 / 閾値 {1} (gitlink・_tasks/ 除外)" -f $bodyLines, $BodyThreshold)
Write-Host ("サブモジュール側: {0} 行 / 閾値 {1}" -f $smLines, $SubmoduleThreshold)
if ($smRows.Count -gt 0) { $smRows | Format-Table Path, Range, Lines, Note -AutoSize | Out-String | Write-Host }
Write-Host ("判定: {0}" -f $(if ($reached) { 'THRESHOLD-REACHED (PR 送付対象)' } else { 'BELOW-THRESHOLD (develop に累積継続)' }))

exit $(if ($reached) { 10 } else { 0 })
