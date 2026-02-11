# Project path
$projectPath = Join-Path -Path $PSScriptRoot -ChildPath "launcher"
$srcPath = Join-Path -Path $projectPath -ChildPath "src"

# python path
$PY_ROOT = Join-Path -Path $PSScriptRoot -ChildPath "python-embed"
$libPath = Join-Path -Path $PY_ROOT -ChildPath "Lib"
$dllPath = Join-Path -Path $PY_ROOT -ChildPath "DLLs"
$includePath = Join-Path -Path $PY_ROOT -ChildPath "Include"
$libsPath = Join-Path -Path $PY_ROOT -ChildPath "libs"

# copy include and lib to project
Write-Host "Syncing include and libs to project..." -ForegroundColor Cyan
Remove-Item -Path (Join-Path -Path $projectPath -ChildPath "include") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path (Join-Path -Path $projectPath -ChildPath "lib") -Recurse -Force -ErrorAction SilentlyContinue

if (Test-Path $includePath) {
    Copy-Item -Path $includePath -Destination $projectPath -Recurse -Force
    # Ensure nested directory is avoided and casing is correct
    $destInclude = Join-Path -Path $projectPath -ChildPath (Split-Path $includePath -Leaf)
    if (Test-Path $destInclude) {
        Rename-Item -Path $destInclude -NewName "include" -Force -ErrorAction SilentlyContinue
    }
}

if (Test-Path $libsPath) {
    Copy-Item -Path $libsPath -Destination $projectPath -Recurse -Force
    $destLibs = Join-Path -Path $projectPath -ChildPath (Split-Path $libsPath -Leaf)
    if (Test-Path $destLibs) {
        Rename-Item -Path $destLibs -NewName "lib" -Force -ErrorAction SilentlyContinue
    }
}
Remove-Item -Path $includePath -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path $libsPath -Recurse -Force -ErrorAction SilentlyContinue

# install requirements
$pythonExe = Join-Path -Path $PY_ROOT -ChildPath "python.exe"

# Ensure pip is available
Write-Host "Checking for pip..." -ForegroundColor Cyan
$pipCheck = & $pythonExe -m pip --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pip not found. Installing via ensurepip..." -ForegroundColor Yellow
    & $pythonExe -m ensurepip
}

$pipArgs = @("-m", "pip", "install", "--no-cache-dir", "-r", (Join-Path -Path $srcPath -ChildPath "requirements.txt"))
Write-Host "Installing Python dependencies..." -ForegroundColor Green
try {
    & $pythonExe @pipArgs
} catch {
    Write-Error "Failed to install Python dependencies."
    exit 1
}
# uninstall pip and setuptools
$pipUninstallArgs = @("-m", "pip", "uninstall", "-y", "pip", "setuptools")
try {    & $pythonExe @pipUninstallArgs
} catch {
    Write-Error "Failed to uninstall pip and setuptools."
    exit 1
}
# cleanup dist-info and pip cache
$distInfoPath = Join-Path -Path $libPath -ChildPath "site-packages"
Get-ChildItem -Path $distInfoPath -Filter "*pip*" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $distInfoPath -Filter "*setuptools*" -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
$pipCachePath = Join-Path -Path $PY_ROOT -ChildPath "pip_cache"
if (Test-Path $pipCachePath) {
    Write-Host "Removing pip cache..." -ForegroundColor Yellow
    Remove-Item -Path $pipCachePath -Recurse -Force
}
# foreach ($item in Get-ChildItem -Path $distInfoPath -Filter "*.dist-info" -Recurse) {
#     Write-Host "Removing pip dist-info: $($item.FullName)" -ForegroundColor Yellow
#     Remove-Item -Path $item.FullName -Recurse -Force
# }

# List of libs to remove
$removeLibs = @(
    "ensurepip",
    "distutils",
    "idlelib",
    "pydoc_data",
    "sqlite3",
    "venv",
    "__pycache__"
)
# Get all directories in the Lib folder
$dirs = Get-ChildItem -Path $libPath -Directory
foreach ($dir in $dirs) {
    if ($removeLibs -contains $dir.Name) {
        Write-Host "Removing directory: $($dir.FullName)" -ForegroundColor Yellow
        Remove-Item -Path $dir.FullName -Recurse -Force
    }
}

# Remove test pyd in DLLs
$pydFiles = Get-ChildItem -Path $dllPath -Filter "*.pyd"
foreach ($pyd in $pydFiles) {
    if ($pyd.Name -like "_test*") {
        Write-Host "Removing test pyd: $($pyd.FullName)" -ForegroundColor Yellow
        Remove-Item -Path $pyd.FullName -Force
    }
}

# compile python files to pyc
$compileArgs = @("-m", "compileall", "-b", "-q", $libPath)
Write-Host "Compiling Python files to bytecode..." -ForegroundColor Green
try {
    & $pythonExe @compileArgs
} catch {
    Write-Error "Failed to compile Python files."
    exit 1
}
# cleanup py files
$pyFiles = Get-ChildItem -Path $libPath -Filter "*.py" -Recurse
foreach ($py in $pyFiles) {
    Write-Host "Removing py file: $($py.FullName)" -ForegroundColor Yellow
    Remove-Item -Path $py.FullName -Force
}

# cleanup pyi, pyo file
$pyiFiles = Get-ChildItem -Path $libPath -Filter "*.pyi" -Recurse
foreach ($pyi in $pyiFiles) {
    Write-Host "Removing pyi file: $($pyi.FullName)" -ForegroundColor Yellow
    Remove-Item -Path $pyi.FullName -Force
}
$pyoFiles = Get-ChildItem -Path $libPath -Filter "*.pyo" -Recurse
foreach ($pyo in $pyoFiles) {
    Write-Host "Removing pyo file: $($pyo.FullName)" -ForegroundColor Yellow
    Remove-Item -Path $pyo.FullName -Force
}

# compile project python files to pyc
$compileArgs = @("-m", "compileall", "-b", "-q", $srcPath)
Write-Host "Compiling project Python files to bytecode..." -ForegroundColor Green
try {    
    & $pythonExe @compileArgs
} catch {
    Write-Error "Failed to compile project Python files."
    exit 1
}
$mainPycPath = Join-Path -Path $srcPath -ChildPath "main.pyc"
Move-Item $mainPycPath -Destination $PY_ROOT -Force

# Remove all __pycache__ folders in Lib
Write-Host "Removing __pycache__ from standard library..." -ForegroundColor Yellow
Get-ChildItem -Path $libPath -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force

# dont zip site-packages
$sitePackagesPath = Join-Path -Path $libPath -ChildPath "site-packages"
Move-Item -Path $sitePackagesPath -Destination (Join-Path -Path $PY_ROOT -ChildPath "site-packages") -Force
# zipped python standard library
$baseZipPath = Join-Path -Path $PY_ROOT -ChildPath "base.zip"
Write-Host "Creating zip for Python standard library: $baseZipPath" -ForegroundColor Green
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path $baseZipPath) { Remove-Item $baseZipPath -Force }
[System.IO.Compression.ZipFile]::CreateFromDirectory($libPath, $baseZipPath)

# zipped project pyc files
$launcherZipPath = Join-Path -Path $PY_ROOT -ChildPath "launcher.zip"
if (Test-Path $launcherZipPath) { Remove-Item $launcherZipPath -Force }

Write-Host "Creating project zip (pyc only): $launcherZipPath" -ForegroundColor Green
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$archive = [System.IO.Compression.ZipFile]::Open($launcherZipPath, [System.IO.Compression.ZipArchiveMode]::Create)
foreach ($py in Get-ChildItem -Path $srcPath -Filter "*.pyc" -Recurse) {
    $relativePath = $py.FullName.Substring($srcPath.Length).TrimStart('\')
    Write-Host "Adding to zip: $relativePath" -ForegroundColor Yellow
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $py.FullName, $relativePath)
    Remove-Item -Path $py.FullName -Force
}
$archive.Dispose()

# cleanup unzipped standard library
Remove-Item -Path $libPath -Recurse -Force
New-Item -Path $libPath -ItemType Directory | Out-Null
Move-Item -Path $baseZipPath -Destination (Join-Path -Path $libPath -ChildPath "base.zip") -Force
Move-Item -Path $launcherZipPath -Destination (Join-Path -Path $libPath -ChildPath "launcher.zip") -Force
Move-Item -Path (Join-Path -Path $PY_ROOT -ChildPath "site-packages") -Destination (Join-Path -Path $libPath -ChildPath "site-packages") -Force

# Move tcl to DLLs
$tclPath = Join-Path -Path $PY_ROOT -ChildPath "tcl"
if (Test-Path $tclPath) {
    foreach ($item in Get-ChildItem -Path $tclPath) {
        if ($item.Name -like "tcl*" -or $item.Name -like "tk*") {
            Move-Item -Path $item.FullName -Destination $dllPath -Force
        }
        Write-Host "Moving tcl item: $($item.FullName)" -ForegroundColor Yellow
    }
    Remove-Item -Path $tclPath -Recurse -Force
} else {
    Write-Host "Tcl directory not found, skipping..." -ForegroundColor Gray
}

# Move dlls to bin
$binPath = Join-Path -Path $PY_ROOT -ChildPath "bin"
if (-not (Test-Path $binPath)) {
    Write-Host "Creating bin directory: $binPath" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $binPath | Out-Null
}
$dllFiles = Get-ChildItem -Path $dllPath -Filter "*.dll"
foreach ($dll in $dllFiles) {
    if ($dll.Name -eq "sqlite3.dll") {
        Remove-Item -Path $dll.FullName -Force
        continue
    }
    Write-Host "Moving dll: $($dll.FullName)" -ForegroundColor Yellow
    Move-Item -Path $dll.FullName -Destination $binPath -Force
}

# move project bin to python bin
Copy-Item -Path (Join-Path -Path $srcPath -ChildPath "bin\*") -Destination $binPath -Recurse -Force

# create _pth file
$pthFile = Join-Path -Path $PY_ROOT -ChildPath "python314._pth"
$pthContent = @(
    ".",
    "DLLs",
    "Lib",
    "Lib/base.zip",
    "Lib/launcher.zip",
    "",
    "# Uncomment the following line to run site.main() automatically",
    "import site"
)
Set-Content -Path $pthFile -Value $pthContent -Encoding ASCII

# Remove unuse files
Remove-Item -Path "$PY_ROOT\*.exe" -Force
Remove-Item -Path "$PY_ROOT\Scripts" -Recurse -Force
Remove-Item -Path "$PY_ROOT\LICENSE.txt" -Force