# Local services only. Never updates the remote Bolna agent.
$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv-native\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'The project Python environment is missing.' }
& $taskPython -B -u (Join-Path $PSScriptRoot 'start_local.py')
if ($LASTEXITCODE -ne 0) { throw 'HaqRecord startup did not complete. See the message above.' }
