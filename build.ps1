# Find vswhere.exe
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) {
    Write-Error "vswhere.exe not found. Please install Visual Studio."
    exit 1
}

# Find MSBuild path
$msbuildPath = & $vswhere -latest -requires Microsoft.Component.MSBuild -find MSBuild\Current\Bin\MSBuild.exe
if (-not $msbuildPath) {
    # Try older version if Current is not found
    $msbuildPath = & $vswhere -latest -requires Microsoft.Component.MSBuild -find MSBuild\**\Bin\MSBuild.exe | Select-Object -First 1
}

if (-not $msbuildPath) {
    Write-Error "MSBuild.exe not found."
    exit 1
}

Write-Host "Using MSBuild at: $msbuildPath" -ForegroundColor Cyan

# Define project details
$solutionFile = "mcbe_pccocos_launcher.slnx"
$configuration = "Release"
$platform = "x64"

# Running MSBuild
Write-Host "Building $solutionFile ($configuration|$platform)..." -ForegroundColor Green

& $msbuildPath $solutionFile /p:Configuration=$configuration /p:Platform=$platform /m /t:Build

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build Succeeded!" -ForegroundColor Green
} else {
    Write-Host "Build Failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
