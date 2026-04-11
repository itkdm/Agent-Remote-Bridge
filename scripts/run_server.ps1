$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\\Scripts\\python.exe"
if (-not (Test-Path $pythonExe)) {
  throw "Python executable not found: $pythonExe"
}
& $pythonExe "-m" "agent_remote_bridge.main" @args
