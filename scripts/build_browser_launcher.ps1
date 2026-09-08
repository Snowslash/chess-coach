# Run on Windows from a small venv with this project, build and PyInstaller installed.
# No Stockfish, Torch, Maia or model weights should be present in this build venv.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    python -m PyInstaller --noconfirm --onedir --name chess-coach-browser `
        --collect-all chess_coach --collect-submodules uvicorn `
        --exclude-module torch --exclude-module maia2 scripts/run_web_gui.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)" }
} finally {
    Pop-Location
}
