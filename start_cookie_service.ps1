param([switch]$OpenDashboard)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$State = Join-Path $Root "runtime_state"
New-Item -ItemType Directory -Force -Path $State | Out-Null

function IsListening([int]$port) {
  return $null -ne (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1)
}

if (-not (IsListening 18888)) {
  $Node = (Get-Command node.exe -ErrorAction Stop).Source
  $ServerJs = Join-Path $Root "extension\server.js"
  $Bridge = Start-Process -FilePath $Node -ArgumentList ('"' + $ServerJs + '"') -WorkingDirectory (Join-Path $Root "extension") -WindowStyle Hidden -PassThru
  Set-Content -Path (Join-Path $State "bridge.pid") -Value $Bridge.Id
}

if (-not (IsListening 18800)) {
  $Python = Join-Path $Root ".venv\Scripts\pythonw.exe"
  if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
  }
  if (-not (Test-Path $Python)) { throw "Python venv not installed: $Python" }
  $Api = Start-Process -FilePath $Python -ArgumentList @('run_service.py','--no-browser') -WorkingDirectory $Root -WindowStyle Hidden -PassThru
  Set-Content -Path (Join-Path $State "api.pid") -Value $Api.Id
}

if ($OpenDashboard) {
  Start-Sleep -Seconds 2
  Start-Process "http://127.0.0.1:18800/"
}
