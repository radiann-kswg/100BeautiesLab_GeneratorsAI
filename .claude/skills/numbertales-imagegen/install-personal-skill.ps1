# install-personal-skill.ps1
# Place numbertales-imagegen as a project skill and create a junction from
# ~/.claude/skills/numbertales-imagegen so it works as a personal skill too.
# Because it's a junction, "git pull" keeps SKILL.md automatically up to date.
#
# Usage (no admin rights required; junctions can be created by standard users):
#   1. Open PowerShell
#   2. Run from this folder:  ./install-personal-skill.ps1
#
# To uninstall: remove ~/.claude/skills/numbertales-imagegen
# (only the junction is deleted; the repo files remain intact)

$ErrorActionPreference = 'Stop'

# --- Resolve paths -----------------------------------------------------------
$src  = $PSScriptRoot                                   # .claude\skills\numbertales-imagegen
$repo = (Resolve-Path (Join-Path $src '..\..')).Path    # repository root

Write-Host "Repo root: $repo"

# --- 1) Place as project skill under .claude/skills -------------------------
$projSkill = Join-Path $repo '.claude\skills\numbertales-imagegen'
New-Item -ItemType Directory -Force -Path $projSkill | Out-Null
Copy-Item (Join-Path $src 'SKILL.md')     $projSkill -Force
Copy-Item (Join-Path $src 'REFERENCE.md') $projSkill -Force
Write-Host "[OK] Project skill placed: $projSkill"

# --- 2) Create junction from ~/.claude/skills (personal skill) ---------------
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
Write-Host "Done! Go to Settings > Capabilities, enable Code execution,"
Write-Host "then turn ON 'numbertales-imagegen' in the skill list."
Write-Host "From now on, 'git pull' will auto-update SKILL.md as well."
