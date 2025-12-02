<#
.\scripts\run-example.ps1

Run an example script from the `examples/` folder using the project's virtualenv.

Usage:
  .\scripts\run-example.ps1 -script quick_start.py

If a virtual environment is present at `.venv`, it will be activated before
running the example. The script resolves the project root based on the
location of this helper script.
#>

param(
    [string]$script = 'quick_start.py'
)

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectRoot = Resolve-Path (Join-Path $scriptDir '..')
    Set-Location $projectRoot
} catch {
    Write-Error "Could not determine project root: $_"
    exit 1
}

$venvActivate = Join-Path $projectRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $venvActivate) {
    Write-Host "Activating venv: $venvActivate"
    & $venvActivate
} else {
    Write-Warning "Virtualenv activate script not found at $venvActivate. Falling back to system 'python'."
}

$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExe)) {
    $pythonExe = 'python'
}

Write-Host "Running example: examples\$script"
& $pythonExe "examples\$script"
