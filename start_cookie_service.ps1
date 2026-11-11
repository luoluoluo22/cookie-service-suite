param([switch]$OpenDashboard)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$State = Join-Path $Root "runtime_state"
New-Item -ItemType Directory -Force -Path $State | Out-Null

function IsListening([int]$port) {
  return $null -ne (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Start-DetachedProcess([string]$cmdLine, [string]$workDir) {
  try {
    $proc = [wmiclass]"win32_process"
    $res = $proc.Create($cmdLine, $workDir)
    if ($res.ReturnValue -eq 0 -and $res.ProcessId) {
      return [int]$res.ProcessId
    }
  } catch {}
  return $null
}

if (-not (IsListening 18888)) {
  $Node = (Get-Command node.exe -ErrorAction Stop).Source
  $ServerJs = Join-Path $Root "extension\server.js"
  $cmdLine = "`"$Node`" `"$ServerJs`""
  $workDir = Join-Path $Root "extension"
  $pidVal = Start-DetachedProcess $cmdLine $workDir
  if (-not $pidVal) {
    $Bridge = Start-Process -FilePath $Node -ArgumentList @($ServerJs) -WorkingDirectory $workDir -WindowStyle Hidden -PassThru
    $pidVal = $Bridge.Id
  }
  Set-Content -Path (Join-Path $State "bridge.pid") -Value $pidVal
}

if (-not (IsListening 18800)) {
  $Python = Join-Path $Root ".venv\Scripts\pythonw.exe"
  if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
  }
  if (-not (Test-Path $Python)) {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source }
  }
  if (-not $Python -or -not (Test-Path $Python)) {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source }
  }
  if (-not $Python -or -not (Test-Path $Python)) { throw "Python not found in venv or system PATH" }

  $cmdLine = "`"$Python`" `"$Root\run_service.py`" --no-browser"
  $pidVal = Start-DetachedProcess $cmdLine $Root
  if (-not $pidVal) {
    $Api = Start-Process -FilePath $Python -ArgumentList @('run_service.py','--no-browser') -WorkingDirectory $Root -WindowStyle Hidden -PassThru
    $pidVal = $Api.Id
  }
  Set-Content -Path (Join-Path $State "api.pid") -Value $pidVal
}

if ($OpenDashboard) {
  Start-Sleep -Seconds 2
  Start-Process "http://127.0.0.1:18800/"
}
