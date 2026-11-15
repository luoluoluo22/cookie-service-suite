Option Explicit
Dim sh, ps, root, cmd
Set sh = CreateObject("WScript.Shell")
ps = sh.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"
root = "F:\Desktop\kaifa\cookie-service-suite"
cmd = Chr(34) & ps & Chr(34) & " -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File " & Chr(34) & root & "\start_cookie_service.ps1" & Chr(34)
sh.Run cmd, 0, False
