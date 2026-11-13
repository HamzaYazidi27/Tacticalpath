# install.ps1 — one-time setup for autoedit on Windows 10/11 (PowerShell).
# Run from the repository folder:   powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Need($cmd, $wingetId) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    Write-Host "Installing $cmd ($wingetId)…"
    winget install --id $wingetId -e --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
  }
}
Need python "Python.Python.3.12"
Need ffmpeg "Gyan.FFmpeg"          # full build, includes libass (captions)
Need deno   "DenoLand.Deno"        # JavaScript runtime yt-dlp needs for YouTube
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements.txt
& .\.venv\Scripts\pip.exe install -r requirements-vision.txt
& .\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; WhisperModel('small', device='auto', compute_type='auto'); from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32'); print('models ready')"
if (-not (Test-Path autoedit.config.json)) { Copy-Item autoedit.config.example.json autoedit.config.json }
New-Item -ItemType Directory -Force -Path inbox, outbox, broll, music | Out-Null
Write-Host ""
Write-Host "Installed. Edit autoedit.config.json (brand), then run:"
Write-Host "  .\.venv\Scripts\python.exe -m autoedit my_video.mp4"
Write-Host "  .\.venv\Scripts\python.exe -m autoedit --watch inbox --out outbox"
