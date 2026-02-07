param(
    [string]$PythonExe = "C:\Apps\Python312\python.exe",
    [string]$VenvPath = ".venv312",
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $PythonExe)) {
    throw "Python not found: $PythonExe"
}

$venvPython = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating venv with $PythonExe ..."
    try {
        & $PythonExe -m venv $VenvPath
    }
    catch {
        Write-Host "venv failed, falling back to virtualenv ..."
        $bootstrap = "C:\Apps\Python313\python.exe"
        if (-not (Test-Path $bootstrap)) {
            throw "Fallback python not found: $bootstrap"
        }

        $tmp = ".tmp_venv312"
        $appData = ".venv312_appdata"
        New-Item -ItemType Directory -Force $tmp | Out-Null
        New-Item -ItemType Directory -Force $appData | Out-Null
        $env:TEMP = (Resolve-Path $tmp).Path
        $env:TMP = $env:TEMP

        & $bootstrap -m pip install virtualenv
        & $bootstrap -m virtualenv $VenvPath -p $PythonExe --app-data $appData
    }
}

Write-Host "Installing dev dependencies into $VenvPath ..."
& $PythonExe -m pip --python $venvPython install --upgrade pip -r requirements-dev.txt

if ($RunTests) {
    Write-Host "Running tests ..."
    & $venvPython -m pytest -q
}

Write-Host "Done."
