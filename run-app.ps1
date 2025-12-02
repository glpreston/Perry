<#
.\run-app.ps1 - Activate .venv and start the Streamlit app
#>
param(
    [int]$Port = 2000
)

Write-Host "Starting Peacemaker Guild (Streamlit) on port $Port"

$venvActivate = Join-Path -Path $PSScriptRoot -ChildPath '.venv\Scripts\Activate.ps1'
if (Test-Path $venvActivate) {
    Write-Host "Activating virtual environment .venv"
    # Dot-source to activate in this session
    . $venvActivate
} else {
    Write-Host ".venv not found — creating virtual environment"
    python -m venv .venv
    . $venvActivate
    Write-Host "Upgrading pip and installing requirements (if present)"
    python -m pip install --upgrade pip
    if (Test-Path "requirements.txt") {
        python -m pip install -r requirements.txt
    } else {
        Write-Host "requirements.txt not found — skipping dependency install"
    }
}

Write-Host "Running Streamlit: python -m streamlit run app.py --server.port $Port"
python -m streamlit run app.py --server.port $Port

Write-Host "Streamlit exited."
