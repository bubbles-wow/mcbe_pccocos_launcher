# Define Python download details
$url = "https://github.com/astral-sh/python-build-standalone/releases/download/20260203/cpython-3.14.3+20260203-x86_64-pc-windows-msvc-install_only_stripped.tar.gz"
$tempTarGz = Join-Path $PSScriptRoot "python_standalone.tar.gz"
$targetDir = Join-Path $PSScriptRoot "python-embed"

# Create target directory if it doesn't exist
if (-not (Test-Path $targetDir)) {
    Write-Host "Creating directory: $targetDir" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

# Download Python Standalone
Write-Host "Downloading Python standalone build..." -ForegroundColor Green
try {
    Invoke-WebRequest -Uri $url -OutFile $tempTarGz -ErrorAction Stop
} catch {
    Write-Error "Failed to download Python from $url."
    exit 1
}

# Extract the tar.gz using Windows built-in tar command
Write-Host "Extracting to $targetDir..." -ForegroundColor Green
$extractTemp = Join-Path $PSScriptRoot "temp_extract"
if (Test-Path $extractTemp) { Remove-Item -Path $extractTemp -Recurse -Force }
New-Item -ItemType Directory -Path $extractTemp | Out-Null

tar -xf $tempTarGz -C $extractTemp

# Move contents from temp_extract/python to targetDir
$sourcePath = Join-Path $extractTemp "python"
if (Test-Path $sourcePath) {
    Write-Host "Moving files to $targetDir..." -ForegroundColor Cyan
    if (Test-Path $targetDir) { Remove-Item -Path $targetDir -Recurse -Force }
    Move-Item -Path $sourcePath -Destination $targetDir
} else {
    Move-Item -Path "$extractTemp\*" -Destination $targetDir -Force
}

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor Cyan
Remove-Item -Path $tempTarGz -Force
Remove-Item -Path $extractTemp -Recurse -Force

Write-Host "Python standalone build has been successfully installed to $targetDir." -ForegroundColor Green

