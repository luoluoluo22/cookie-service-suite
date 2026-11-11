$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$State = Join-Path $Root "runtime_state"
foreach ($target in @(@("api.pid","python"),@("bridge.pid","node"))) {
  $pidFile = Join-Path $State $target[0]
  if (Test-Path $pidFile) {
    $servicePid = [int](Get-Content $pidFile -Raw)
    $p = Get-Process -Id $servicePid -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -like "$($target[1])*") {
      $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$servicePid" -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "$($target[1])*" })
      foreach ($child in $children) { Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue }
      Stop-Process -Id $servicePid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  }
}
