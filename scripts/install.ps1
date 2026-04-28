param(
  [string]$CodexHome = "$HOME\.codex",
  [string]$ClaudeHome = "$HOME\.claude"
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$skillSource = Join-Path $repo "skill\video-understanding-ingest"
$commandSource = Join-Path $repo "commands\video-learn.md"

if (-not (Test-Path -LiteralPath $skillSource)) {
  throw "Skill source not found: $skillSource"
}

$codexSkillDest = Join-Path $CodexHome "skills\video-understanding-ingest"
$codexCommandDest = Join-Path $CodexHome "commands\video-learn.md"
$claudeSkillDest = Join-Path $ClaudeHome "skills\video-understanding-ingest"
$claudeCommandDest = Join-Path $ClaudeHome "commands\video-learn.md"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $codexSkillDest) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $codexCommandDest) | Out-Null
Copy-Item -Recurse -Force -LiteralPath $skillSource -Destination (Split-Path -Parent $codexSkillDest)
Copy-Item -Force -LiteralPath $commandSource -Destination $codexCommandDest

if (Test-Path -LiteralPath $ClaudeHome) {
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $claudeSkillDest) | Out-Null
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $claudeCommandDest) | Out-Null
  Copy-Item -Recurse -Force -LiteralPath $skillSource -Destination (Split-Path -Parent $claudeSkillDest)
  Copy-Item -Force -LiteralPath $commandSource -Destination $claudeCommandDest
}

Write-Host "Installed video-understanding-ingest skill and /video-learn command."
