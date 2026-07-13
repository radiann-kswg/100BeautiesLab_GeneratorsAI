<#
.SYNOPSIS
    サブモジュール (_creations-ai / ネストの creations-db) を毎朝同期し、更新があれば取り込んで
    _tasks/ にログを生成し、コミット (push なし) するメンテナンススクリプト。

.DESCRIPTION
    Windows 実機 (git が GitHub に到達でき、改行コード CRLF が正常に扱える環境) で動かす前提。
    クラウドサンドボックスでは GitHub 到達不可 / FUSE マウントによる git ロック不可 /
    全ファイル CRLF<->LF 差分の問題で git 操作が破綻するため、必ず実機で実行すること。

    処理フロー:
      1. 各サブモジュールを fetch
      2. 追跡ブランチ (.gitmodules の branch、無ければ origin/HEAD) のリモート最新と現在を比較
      3. fast-forward 可能な場合のみ取り込み。非 FF / ブランチ不一致はスキップして記録
      4. _tasks/yyyyMMdd_submodule-sync.md にログ生成
      5. 変更があれば commit (push は行わない)

.PARAMETER DryRun
    取り込み・コミットを行わず、判定結果のみ表示する。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\daily-submodule-sync.ps1 -DryRun
    powershell -ExecutionPolicy Bypass -File scripts\daily-submodule-sync.ps1

.NOTES
    Windows タスクスケジューラ登録例 (毎朝 9:00):
      schtasks /Create /TN "100BeautiesLab_SubmoduleSync" /SC DAILY /ST 09:00 ^
        /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\Visual Studio Code UserFile\100BeautiesLab_GeneratorsAI\scripts\daily-submodule-sync.ps1\""

    ドライブ移動に強い登録は scripts\register-submodule-sync-task.ps1 を利用 (実行場所からパスを自動解決)。
#>
[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# --- リポジトリルートを解決 (このスクリプトは scripts/ 配下にある想定) ---
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

# git は成功時にも stderr へ出力する (例: "Already on 'master'", "Previous HEAD position was ...")。
# PowerShell 5.1 は native コマンドの stderr をリダイレクトすると各行を ErrorRecord (NativeCommandError) に
# 変換するため、$ErrorActionPreference = 'Stop' 下では成功メッセージでも例外が飛ぶ。
# ここでは一時的に Continue へ落とし、成否は必ず終了コードで判定する。
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

if (-not (Test-Path (Join-Path $RepoRoot '.git'))) {
    Write-Error "git リポジトリが見つかりません: $RepoRoot"
    exit 1
}

Write-Host "== 100BeautiesLab サブモジュール同期 ==" -ForegroundColor Cyan
Write-Host "リポジトリ: $RepoRoot"
Write-Host ("モード: {0}" -f ($(if ($DryRun) { 'DryRun (変更なし)' } else { '本実行' })))

# --- .gitmodules からサブモジュール一覧と追跡ブランチを取得 ---
$submodules = @()
$gmPath = Join-Path $RepoRoot '.gitmodules'
if (-not (Test-Path $gmPath)) {
    Write-Host "サブモジュールがありません。終了します。"
    exit 0
}

$names = & git config -f .gitmodules --get-regexp 'submodule\..*\.path'
foreach ($line in $names) {
    if ($line -match '^submodule\.(.+)\.path\s+(.+)$') {
        $name = $Matches[1]
        $path = $Matches[2]
        $branch = (& git config -f .gitmodules --get "submodule.$name.branch") 2>$null
        $submodules += [pscustomobject]@{ Name = $name; Path = $path; Branch = $branch }
    }
}

# --- fetch ---
Write-Host "`n-- fetch --" -ForegroundColor Yellow
$syncResult = Invoke-Git @('submodule', 'sync', '--recursive')
if ($syncResult.ExitCode -ne 0) {
    Write-Warning ("submodule sync 失敗: {0}" -f $syncResult.Output)
}
foreach ($sm in $submodules) {
    Write-Host ("fetch {0} ..." -f $sm.Path)
    $fetchResult = Invoke-Git @('-C', $sm.Path, 'fetch', '--all', '--prune')
    if ($fetchResult.ExitCode -ne 0) {
        Write-Warning ("fetch 失敗 {0}: {1}" -f $sm.Path, $fetchResult.Output)
    }
}

# --- 判定 & 取り込み ---
# Markdown テーブルへ埋める備考は 1 行に潰す (git の出力は複数行になりうる)
function Format-Reason {
    param([string]$Text)
    return ($Text -replace '\r?\n', ' ' -replace '\|', '/').Trim()
}

$results = @()
foreach ($sm in $submodules) {
    $cur = (Invoke-Git @('-C', $sm.Path, 'rev-parse', 'HEAD')).Output
    if ($sm.Branch) {
        $trackRef = "origin/$($sm.Branch)"
    }
    else {
        $headRef = Invoke-Git @('-C', $sm.Path, 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD')
        $trackRef = if ($headRef.ExitCode -eq 0 -and $headRef.Output) { $headRef.Output } else { 'origin/HEAD' }
    }
    $remoteResult = Invoke-Git @('-C', $sm.Path, 'rev-parse', $trackRef)
    if ($remoteResult.ExitCode -ne 0 -or -not $remoteResult.Output) {
        $results += [pscustomobject]@{ Name=$sm.Name; Path=$sm.Path; Track=$trackRef; Old=$cur; New='(unknown)'; Action='SKIP'; Reason='追跡ブランチのリモートrefが解決不可' }
        continue
    }
    $remote = $remoteResult.Output

    if ($cur -eq $remote) {
        $results += [pscustomobject]@{ Name=$sm.Name; Path=$sm.Path; Track=$trackRef; Old=$cur; New=$remote; Action='NO-CHANGE'; Reason='最新' }
        continue
    }

    # fast-forward 可能か (現在が追跡先の祖先か)
    $ffCheck = Invoke-Git @('-C', $sm.Path, 'merge-base', '--is-ancestor', $cur, $remote)
    $isFF = ($ffCheck.ExitCode -eq 0)

    if (-not $isFF) {
        $results += [pscustomobject]@{ Name=$sm.Name; Path=$sm.Path; Track=$trackRef; Old=$cur; New=$remote; Action='SKIP'; Reason='非 FF (枝分かれ/別ブランチ)。手動判断が必要' }
        continue
    }

    if ($DryRun) {
        $results += [pscustomobject]@{ Name=$sm.Name; Path=$sm.Path; Track=$trackRef; Old=$cur; New=$remote; Action='WOULD-UPDATE'; Reason='FF 可能 (DryRun)' }
        continue
    }

    # 取り込み: 追跡ブランチへ checkout して ff-only
    $localBranch = if ($sm.Branch) { $sm.Branch } else { ($trackRef -replace '^origin/','') }

    $checkout = Invoke-Git @('-C', $sm.Path, 'checkout', $localBranch)
    if ($checkout.ExitCode -ne 0) {
        $results += [pscustomobject]@{ Name=$sm.Name; Path=$sm.Path; Track=$trackRef; Old=$cur; New=$remote; Action='SKIP'; Reason=(Format-Reason ("checkout 失敗 ({0}): {1}" -f $localBranch, $checkout.Output)) }
        continue
    }

    $merge = Invoke-Git @('-C', $sm.Path, 'merge', '--ff-only', $trackRef)
    if ($merge.ExitCode -ne 0) {
        $results += [pscustomobject]@{ Name=$sm.Name; Path=$sm.Path; Track=$trackRef; Old=$cur; New=$remote; Action='SKIP'; Reason=(Format-Reason ("ff-only merge 失敗: {0}" -f $merge.Output)) }
        continue
    }

    # ネストサブモジュール (_creations-ai/creations-db) を新ポインタへ再帰的に追従させる。
    $nested = Invoke-Git @('-C', $sm.Path, 'submodule', 'update', '--init', '--recursive')
    if ($nested.ExitCode -ne 0) {
        Write-Warning ("ネストサブモジュール更新に失敗 {0}: {1}" -f $sm.Path, $nested.Output)
    }

    $newCur = (Invoke-Git @('-C', $sm.Path, 'rev-parse', 'HEAD')).Output
    $results += [pscustomobject]@{ Name=$sm.Name; Path=$sm.Path; Track=$trackRef; Old=$cur; New=$newCur; Action='UPDATED'; Reason='FF 取り込み完了' }
}

# --- 結果表示 ---
Write-Host "`n-- 判定結果 --" -ForegroundColor Yellow
$results | Format-Table Name, Action, @{N='Old';E={$_.Old.Substring(0,7)}}, @{N='New';E={ if($_.New -match '^[0-9a-f]{7,}'){$_.New.Substring(0,7)}else{$_.New} }}, Reason -AutoSize

$updated = $results | Where-Object { $_.Action -eq 'UPDATED' }

# --- ログ生成 ---
$today = Get-Date -Format 'yyyyMMdd'
$tasksDir = Join-Path $RepoRoot '_tasks'
if (-not (Test-Path $tasksDir)) { New-Item -ItemType Directory -Path $tasksDir | Out-Null }
$logPath = Join-Path $tasksDir "${today}_submodule-sync.md"

$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# サブモジュール同期ログ — $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("> 実機 PowerShell スクリプト ``scripts/daily-submodule-sync.ps1`` による自動実行。")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## フェッチ・判定結果')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('| サブモジュール | 追跡先 | 旧 | 新 | 判定 | 備考 |')
[void]$sb.AppendLine('|---|---|---|---|---|---|')
foreach ($r in $results) {
    $oldS = if ($r.Old.Length -ge 7) { $r.Old.Substring(0,7) } else { $r.Old }
    $newS = if ($r.New -match '^[0-9a-f]{7,}') { $r.New.Substring(0,7) } else { $r.New }
    [void]$sb.AppendLine("| ``$($r.Name)`` | $($r.Track) | $oldS | $newS | $($r.Action) | $($r.Reason) |")
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## 取り込んだ更新の内容')
[void]$sb.AppendLine('')
if ($updated) {
    foreach ($u in $updated) {
        [void]$sb.AppendLine("### ``$($u.Name)`` $($u.Old.Substring(0,7))..$($u.New.Substring(0,7))")
        [void]$sb.AppendLine('')
        [void]$sb.AppendLine('```')
        $log = (Invoke-Git @('-C', $u.Path, 'log', '--oneline', "$($u.Old)..$($u.New)")).Output
        [void]$sb.AppendLine($log)
        [void]$sb.AppendLine('```')
        [void]$sb.AppendLine('')
        [void]$sb.AppendLine('変更ファイル:')
        [void]$sb.AppendLine('')
        [void]$sb.AppendLine('```')
        $stat = (Invoke-Git @('-C', $u.Path, 'diff', '--stat', "$($u.Old)..$($u.New)")).Output
        [void]$sb.AppendLine($stat)
        [void]$sb.AppendLine('```')
        [void]$sb.AppendLine('')
    }
}
else {
    [void]$sb.AppendLine('今回取り込んだ更新はありません。')
    [void]$sb.AppendLine('')
}
[void]$sb.AppendLine('## 最適化メモ')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('> 取り込んだ差分がスキーマ / `manifest-training.jsonl` / API に影響する場合は、')
[void]$sb.AppendLine('> Cowork の `daily-submodule-sync-optimize` タスク (Claude) に差分レビューを依頼し、')
[void]$sb.AppendLine('> `src/` ・ `docs/` 側の追従最適化を行うこと。本スクリプトは git 同期とログ・コミットのみ担当。')
[void]$sb.AppendLine('')

if ($DryRun) {
    Write-Host "`n[DryRun] ログ未書き込み。生成予定パス: $logPath" -ForegroundColor DarkGray
    Write-Host ($sb.ToString())
    exit 0
}

# UTF-8 (BOMなし) で書き込み
[System.IO.File]::WriteAllText($logPath, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "`nログ生成: $logPath" -ForegroundColor Green

# --- コミット (push なし) ---
$addResult = Invoke-Git @('add', '-A')
if ($addResult.ExitCode -ne 0) {
    Write-Error ("git add 失敗: {0}" -f $addResult.Output)
    exit 1
}
$staged = (Invoke-Git @('diff', '--cached', '--name-only')).Output
if (-not $staged) {
    Write-Host "コミット対象なし。終了します。"
    exit 0
}

$msg = "chore: サブモジュール更新に追従しログ生成 ($today)`n`n" + (($results | ForEach-Object { "- $($_.Name): $($_.Action) ($($_.Reason))" }) -join "`n") + "`n- push なし"
$commitResult = Invoke-Git @('commit', '-m', $msg)
if ($commitResult.ExitCode -ne 0) {
    Write-Error ("git commit 失敗: {0}" -f $commitResult.Output)
    exit 1
}
Write-Host "コミット完了 (push なし):" -ForegroundColor Green
Write-Host (Invoke-Git @('log', '--oneline', '-1')).Output
Write-Host "`n※ リモート反映が必要なら手動で 'git push' してください。"
