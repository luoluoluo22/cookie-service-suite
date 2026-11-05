<#
.SYNOPSIS
Suno AI CLI 快捷启动器 (PowerShell)
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)
$ScriptPath = Join-Path $PSScriptRoot "suno_cli.ps1"
& $ScriptPath @ArgsList
