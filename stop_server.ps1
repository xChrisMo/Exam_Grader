#!/usr/bin/env powershell
# PowerShell script for graceful shutdown of Exam Grader server

Write-Host "🛑 Stopping Exam Grader server gracefully..." -ForegroundColor Yellow

# Function to stop processes gracefully
function Stop-ProcessGracefully {
    param($ProcessName, $Description)
    
    $processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "📋 Found $($processes.Count) $Description process(es)" -ForegroundColor Cyan
        
        foreach ($process in $processes) {
            try {
                Write-Host "🔄 Gracefully stopping $Description (PID: $($process.Id))" -ForegroundColor Green
                
                # Try graceful shutdown first
                $process.CloseMainWindow() | Out-Null
                
                # Wait up to 5 seconds for graceful shutdown
                if (!$process.WaitForExit(5000)) {
                    Write-Host "⚡ Force stopping $Description (PID: $($process.Id))" -ForegroundColor Red
                    $process.Kill()
                }
                
                Write-Host "✅ Stopped $Description (PID: $($process.Id))" -ForegroundColor Green
            }
            catch {
                Write-Host "❌ Error stopping $Description (PID: $($process.Id)): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "ℹ️  No $Description processes found" -ForegroundColor Gray
    }
}

# Function to stop processes by port
function Stop-ProcessByPort {
    param($Port)
    
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($connections) {
            Write-Host "🔌 Found processes using port $Port" -ForegroundColor Cyan
            
            foreach ($conn in $connections) {
                $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "🔄 Stopping process using port $Port (PID: $($process.Id), Name: $($process.ProcessName))" -ForegroundColor Green
                    try {
                        $process.CloseMainWindow() | Out-Null
                        if (!$process.WaitForExit(3000)) {
                            $process.Kill()
                        }
                        Write-Host "✅ Stopped process on port $Port" -ForegroundColor Green
                    }
                    catch {
                        Write-Host "❌ Error stopping process on port $Port: $($_.Exception.Message)" -ForegroundColor Red
                    }
                }
            }
        }
        else {
            Write-Host "ℹ️  No processes found using port $Port" -ForegroundColor Gray
        }
    }
    catch {
        Write-Host "❌ Error checking port $Port: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Stop Python processes (general)
Stop-ProcessGracefully -ProcessName "python" -Description "Python"

# Stop processes using specific ports
Stop-ProcessByPort -Port 8501
Stop-ProcessByPort -Port 5000

# Additional cleanup - find processes by command line
Write-Host "🔍 Searching for Exam Grader processes by command line..." -ForegroundColor Cyan

try {
    $examGraderProcesses = Get-WmiObject Win32_Process | Where-Object { 
        $_.CommandLine -like "*run_app.py*" -or 
        $_.CommandLine -like "*exam_grader_app*" 
    }
    
    if ($examGraderProcesses) {
        foreach ($proc in $examGraderProcesses) {
            Write-Host "🎯 Found Exam Grader process (PID: $($proc.ProcessId)): $($proc.CommandLine)" -ForegroundColor Yellow
            try {
                Stop-Process -Id $proc.ProcessId -Force
                Write-Host "✅ Stopped Exam Grader process (PID: $($proc.ProcessId))" -ForegroundColor Green
            }
            catch {
                Write-Host "❌ Error stopping process (PID: $($proc.ProcessId)): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "ℹ️  No Exam Grader processes found by command line" -ForegroundColor Gray
    }
}
catch {
    Write-Host "❌ Error searching for processes: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "✅ Shutdown process completed!" -ForegroundColor Green
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")