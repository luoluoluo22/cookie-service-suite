$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Process explorer.exe -ArgumentList @((Join-Path $root 'extension'))
Start-Process msedge.exe -ArgumentList @('edge://extensions/')
Write-Host 'Edge 扩展页已打开。开启开发人员模式，点击「加载解压缩的扩展」，选择：' (Join-Path $root 'extension')
