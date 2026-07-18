$host.UI.RawUI.WindowTitle = "App Review Insights - Debug"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================"
Write-Host "  App Review Insights - Debug Mode"
Write-Host "========================================"
Write-Host ""
Write-Host "Root: $root"
Write-Host ""

# Check project structure
Write-Host "Checking project structure..."
if (-not (Test-Path "$root\backend")) {
    Write-Host "  [ERROR] backend folder missing"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] backend folder found"

if (-not (Test-Path "$root\frontend")) {
    Write-Host "  [ERROR] frontend folder missing"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  [OK] frontend folder found"
Write-Host ""

# Check Python
Write-Host "Checking Python..."
$pyOk = $null -ne (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pyOk) {
    Write-Host "[ERROR] Python not found"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Python found"
Write-Host ""

# Check Node.js
Write-Host "Checking Node.js..."
$nodeOk = $null -ne (Get-Command node -ErrorAction SilentlyContinue)
if (-not $nodeOk) {
    Write-Host "[ERROR] Node.js not found"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Node.js found"
Write-Host ""

# Check .env
if (-not (Test-Path "$root\backend\.env")) {
    Write-Host "[WARNING] backend\.env not found."
    Write-Host "Copy .env.example to backend\.env and set your API key."
    Write-Host ""
}

# Ask to continue
Write-Host "Do you want to continue starting the services?"
Write-Host "  Press 1 to continue"
Write-Host "  Press 2 to exit"
$choice = Read-Host "Your choice"
if ($choice -ne "1") { exit 0 }

Write-Host ""
Write-Host "Starting services..."
Write-Host ""

# Kill existing processes on ports
Write-Host "Cleaning up existing processes on ports 8000/3000..."
netstat -ano | Select-String ":8000" | ForEach-Object {
    $procId = ($_ -split '\s+')[-1]
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}
netstat -ano | Select-String ":3000" | ForEach-Object {
    $procId = ($_ -split '\s+')[-1]
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}

# Start backend
Write-Host "Starting backend on http://localhost:8000 ..."
$backendProc = Start-Process -FilePath "cmd.exe" -ArgumentList '/k', "cd /d `"$root\backend`" && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Waiting for backend to start..."
Start-Sleep -Seconds 6

# Start frontend
Write-Host "Starting frontend on http://localhost:3000 ..."
$frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList '/k', "cd /d `"$root\frontend`" && npm run dev"

Write-Host "Waiting for frontend to be ready..."
Start-Sleep -Seconds 8

# Open browser
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "========================================"
Write-Host "  Services started!"
Write-Host "========================================"
Write-Host ""
Write-Host "   Frontend: http://localhost:3000"
Write-Host "   Backend:  http://localhost:8000"
Write-Host ""
Write-Host "   Services are running in their own windows."
Read-Host "Press Enter to close this window"
