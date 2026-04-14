param(
  [string]$ServerName = "agentRemoteBridge",
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8000,
  [switch]$ExperimentalTools
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$dataDir = Join-Path $projectRoot "data"
$stdoutLog = Join-Path $dataDir "codex-mcp-http.out.log"
$stderrLog = Join-Path $dataDir "codex-mcp-http.err.log"

if (-not (Test-Path $pythonExe)) {
  throw "Python executable not found: $pythonExe"
}

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
  throw "Codex CLI not found in PATH. Install Codex Desktop or codex CLI first."
}

if (-not (Test-Path $dataDir)) {
  New-Item -ItemType Directory -Path $dataDir | Out-Null
}

$portBinding = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($portBinding) {
  $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($portBinding.OwningProcess)" | Select-Object -First 1
  $commandLine = $process.CommandLine
  if (-not ($process.Name -eq "python.exe" -and $commandLine -like "*agent_remote_bridge.main*" -and $commandLine -like "*$Port*")) {
    throw "Port $Port is already in use by process $($process.Name) (PID $($process.ProcessId))."
  }
}
else {
  $arguments = @(
    "-m", "agent_remote_bridge.main",
    "--transport", "streamable-http",
    "--host", $BindHost,
    "--port", "$Port"
  )
  if ($ExperimentalTools) {
    $arguments += "--experimental-tools"
  }

  Start-Process `
    -FilePath $pythonExe `
    -ArgumentList $arguments `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog | Out-Null

  Start-Sleep -Seconds 2

  $portBinding = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $portBinding) {
    if (Test-Path $stderrLog) {
      Get-Content $stderrLog -Tail 50 | Write-Host
    }
    throw "Failed to start Agent Remote Bridge HTTP server on $BindHost`:$Port."
  }
}

$url = "http://$BindHost`:$Port/mcp"
$existingServers = codex mcp list 2>$null | Out-String
if ($existingServers -match "(?m)^\s*$([regex]::Escape($ServerName))\s+") {
  codex mcp remove $ServerName | Out-Null
}
codex mcp add $ServerName --url $url | Out-Null

Write-Host "Agent Remote Bridge is ready for Codex."
Write-Host "Server name: $ServerName"
Write-Host "MCP URL: $url"
Write-Host "Codex config: $env:USERPROFILE\.codex\config.toml"
Write-Host ""
Write-Host "Next step:"
Write-Host "1. Restart Codex Desktop"
Write-Host "2. Open a new chat"
Write-Host "3. Ask: 在 demo-server 上执行 pwd"
