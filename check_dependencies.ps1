# PowerShell script to check and fix dependencies for Exam Grader application

Write-Host "\n===== Exam Grader Dependency Checker =====\n" -ForegroundColor Cyan

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "Python version: $pythonVersion" -ForegroundColor Green

# Check if running in virtual environment
$inVenv = $env:VIRTUAL_ENV -ne $null
if ($inVenv) {
    Write-Host "Running in virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Green
} else {
    Write-Host "Warning: Not running in a virtual environment" -ForegroundColor Yellow
    Write-Host "Consider using: python -m venv venv && .\venv\Scripts\Activate" -ForegroundColor Yellow
}

# Check installed packages
Write-Host "\nChecking key package versions..." -ForegroundColor Cyan
$flaskVersion = pip show flask 2>$null | Select-String -Pattern "Version:"
$flaskBabelVersion = pip show flask-babel 2>$null | Select-String -Pattern "Version:"
$werkzeugVersion = pip show werkzeug 2>$null | Select-String -Pattern "Version:"

Write-Host "$flaskVersion" -ForegroundColor Green
Write-Host "$flaskBabelVersion" -ForegroundColor Green
Write-Host "$werkzeugVersion" -ForegroundColor Green

# Check for compatibility issues
Write-Host "\nChecking for compatibility issues..." -ForegroundColor Cyan

$flaskVersionNumber = $flaskVersion -replace "Version: ", ""
if ($flaskVersionNumber -match "^3") {
    Write-Host "Warning: Flask 3.x detected, which may not be compatible with Flask-Babel 2.0.0" -ForegroundColor Yellow
    Write-Host "The application is configured to work with Flask 2.3.x" -ForegroundColor Yellow
    
    $fixDependencies = Read-Host "Would you like to downgrade Flask to version 2.3.2? (y/n)"
    if ($fixDependencies -eq "y") {
        Write-Host "Installing Flask 2.3.2..." -ForegroundColor Cyan
        pip install flask==2.3.2 werkzeug==2.3.0
        Write-Host "Flask downgraded to 2.3.2" -ForegroundColor Green
    }
} elseif ($flaskVersionNumber -match "^2.3") {
    Write-Host "Flask 2.3.x detected - compatible with current Flask-Babel setup" -ForegroundColor Green
} else {
    Write-Host "Unknown Flask version compatibility. Please check README.md for details." -ForegroundColor Yellow
}

# Check requirements.txt vs installed packages
Write-Host "\nChecking requirements.txt against installed packages..." -ForegroundColor Cyan
$requirementsContent = Get-Content -Path "requirements.txt"
$flaskRequirement = $requirementsContent | Where-Object { $_ -match "^Flask" }

Write-Host "Requirements.txt specifies: $flaskRequirement" -ForegroundColor Green
Write-Host "Installed: Flask $flaskVersionNumber" -ForegroundColor Green

Write-Host "\n===== Dependency Check Complete =====\n" -ForegroundColor Cyan