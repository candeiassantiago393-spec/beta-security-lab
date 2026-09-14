$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
py -3 -m uvicorn server.app:app --host 127.0.0.1 --port 8080
