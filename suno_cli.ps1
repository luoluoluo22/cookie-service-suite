<#
.SYNOPSIS
Suno AI 独立免服务客户端 (PowerShell 专用启动脚本)
用法:
  .\suno_cli.ps1 quota
  .\suno_cli.ps1 gen "一段欢快的吉他弹唱"
  .\suno_cli.ps1 login
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$PythonExe = "py"
$CustomPy = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"

if (Test-Path $CustomPy) {
    $PythonExe = $CustomPy
}

$ScriptPath = Join-Path $PSScriptRoot "suno_cli.py"
& $PythonExe $ScriptPath @ArgsList
