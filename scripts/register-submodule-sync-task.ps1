<#
.SYNOPSIS
    Windows タスクスケジューラに「100BeautiesLab_SubmoduleSync」を登録/更新する。
    daily-submodule-sync.ps1 の絶対パスをこのスクリプトの場所から自動解決するため、
    リポジトリをどのドライブ (C: / D: 等) に置いても正しいパスで登録できる。

.DESCRIPTION
    /F 付きの schtasks /Create を使い、既存タスクがあれば上書き再登録する。
    実機 (Windows) でのみ実行すること。

.PARAMETER Time
    実行時刻 (HH:mm)。既定は 09:00。

.PARAMETER TaskName
    登録するタスク名。既定は "100BeautiesLab_SubmoduleSync"。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-submodule-sync-task.ps1
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\register-submodule-sync-task.ps1 -Time 08:30
#>
[CmdletBinding()]
param(
    [string]$Time = '09:00',
    [string]$TaskName = '100BeautiesLab_SubmoduleSync'
)

$ErrorActionPreference = 'Stop'

# このスクリプト (scripts/) と同階層にある sync スクリプトの絶対パスを解決
$SyncScript = Join-Path $PSScriptRoot 'daily-submodule-sync.ps1'
if (-not (Test-Path $SyncScript)) {
    Write-Error "同期スクリプトが見つかりません: $SyncScript"
    exit 1
}

Write-Host "== タスク再登録 ==" -ForegroundColor Cyan
Write-Host "タスク名 : $TaskName"
Write-Host "時刻     : $Time"
Write-Host "対象     : $SyncScript"

# Register-ScheduledTask を使うとスペース入りパスも確実にクォートされる
$taskAction  = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$SyncScript`""
$taskTrigger = New-ScheduledTaskTrigger -Daily -At $Time
Register-ScheduledTask -TaskName $TaskName -Action $taskAction -Trigger $taskTrigger `
    -Force | Out-Null

Write-Host "`n登録確認:" -ForegroundColor Green
schtasks /Query /TN $TaskName /V /FO LIST | Select-String "Task To Run|Status|Next Run"
