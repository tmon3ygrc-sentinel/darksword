# DARKSWORD — Automated Daily Run
# Invoked by Windows Task Scheduler every weekday at 9 AM.
# Logs all output (stdout + stderr) to a dated file in the darksword folder.

$ScriptDir = "C:\Work\GRC-OCEG\darksword"
$Python    = "C:\Work\GRC-OCEG\.venv\Scripts\python.exe"
$LogFile   = Join-Path $ScriptDir "darksword_$(Get-Date -Format 'yyyy-MM-dd').log"

function Write-Log ($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    $line | Out-File -FilePath $LogFile -Append -Encoding utf8
    Write-Host $line
}

Write-Log "=== DARKSWORD auto-run starting ==="
Set-Location $ScriptDir

$env:PYTHONIOENCODING = "utf-8"
& $Python "notion_logger_v7.py" --auto *>&1 | ForEach-Object {
    $_ | Out-File -FilePath $LogFile -Append -Encoding utf8
    Write-Host $_
}

$ExitCode = $LASTEXITCODE
Write-Log "=== Auto-run finished — exit code: $ExitCode ==="

if ($ExitCode -ne 0) { exit $ExitCode }
