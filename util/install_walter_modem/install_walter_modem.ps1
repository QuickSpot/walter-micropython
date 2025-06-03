#!/usr/bin/env pwsh

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Device
)

$ErrorActionPreference = 'Stop'

trap {
    Write-Host "`r" -NoNewline
    [Console]::CursorVisible = $true
    exit 1
}

$BOLDWHITE = "`e[1;37m"
$BLUE = "`e[34m"
$YELLOW = "`e[33m"
$GREEN = "`e[32m"
$RED = "`e[31m"
$RESET = "`e[0m"

$spinner = @('⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏')
$spinnerIndex = 0

function Show-Spinner {
    param(
        [string]$Message,
        [int]$PID
    )
    while (Get-Process -Id $PID -ErrorAction SilentlyContinue) {
        Write-Host "`r  $($spinner[$spinnerIndex]) $Message" -NoNewline
        $script:spinnerIndex = ($spinnerIndex + 1) % $spinner.Count
        Start-Sleep -Milliseconds 100
    }
}

function Invoke-MPRemote {
    param(
        [string[]]$Arguments,
        [switch]$Silent
    )
    
    $params = @{
        ArgumentList = $Arguments
        NoNewWindow  = $true
        PassThru     = $true
        ErrorAction  = 'Stop'
    }
    if ($Silent) { $params.RedirectStandardError = $true }

    $process = Start-Process python -ArgumentList "-m mpremote $($Arguments -join ' ')" @params
    $process.WaitForExit()
    
    if ($process.ExitCode -ne 0) {
        throw "Command failed: mpremote $($Arguments -join ' ')"
    }
}

# Verify dependencies
try {
    if (-not (Get-Command python -ErrorAction Stop)) {
        throw "'python' not found in PATH"
    }

    python -m mpremote version *> $null
}
catch {
    Write-Host "$RED`Error:$RESET $_" -ForegroundColor Red
    exit 1
}

$baseArgs = @()
if ($Device) {
    $baseArgs += "connect", $Device
}

$scriptPath = (Get-Item $PSCommandPath).Directory.Parent.Parent.Parent.FullName
$localDir = Join-Path $scriptPath "walter_modem"
$remoteDir = ":lib/walter_modem"

Write-Host "$BOLDWHITE`Verifying directory structure$RESET"
Invoke-MPRemote @baseArgs "fs" "mkdir" ":lib" -Silent
Invoke-MPRemote @baseArgs "fs" "mkdir" $remoteDir -Silent

# Create all directories (except .)
Get-ChildItem -Path $localDir -Recurse -Directory | ForEach-Object {
    $relativePath = $_.FullName.Substring($localDir.Length + 1).Replace('\', '/')
    $targetDir = "$remoteDir/$relativePath"
    
    try {
        Invoke-MPRemote @baseArgs "fs" "mkdir" $targetDir -Silent
        Write-Host "  $BLUE[DIR]$RESET  $targetDir"
    }
    catch {
        Write-Host "  $YELLOW[WARN]$RESET Failed to create $targetDir"
    }
}

# Copy all files except *.pyi
Write-Host "$BOLDWHITE`Copying files$RESET"
Get-ChildItem -Path $localDir -Recurse -File -Exclude *.pyi | ForEach-Object {
    $relativePath = $_.FullName.Substring($localDir.Length + 1).Replace('\', '/')
    $remotePath = "$remoteDir/$relativePath"
    $localPath = $_.FullName

    Write-Host "  $YELLOW•$RESET $remotePath" -NoNewline
    
    $job = Start-ThreadJob -ScriptBlock {
        param($baseArgs, $localPath, $remotePath)
        python -m mpremote @baseArgs fs cp $localPath $remotePath *> $null
    } -ArgumentList $baseArgs, $localPath, $remotePath
    
    try {
        while ($job.State -eq 'Running') {
            Write-Host "`r  $($spinner[$spinnerIndex]) $YELLOW•$RESET $remotePath" -NoNewline
            $script:spinnerIndex = ($spinnerIndex + 1) % $spinner.Count
            Start-Sleep -Milliseconds 100
        }
        $job | Receive-Job -Wait -AutoRemoveJob -ErrorAction Stop *> $null
        Write-Host "`r  $GREEN✓$RESET $remotePath"
    }
    catch {
        Write-Host "`r  $RED✗$RESET $remotePath"
    }
}

# Clean up remote files/dirs not present locally
Write-Host "$BOLDWHITE`Cleaning up remote files$RESET"
$remoteItems = python -m mpremote @baseArgs fs ls -r $remoteDir | 
    ForEach-Object { $_.Trim() -replace '^/', '' -replace "$remoteDir/", '' } |
    Where-Object { $_ -ne $remoteDir -and $_ -ne '.' }

$localItems = Get-ChildItem -Path $localDir -Recurse |
    ForEach-Object {
        if ($_.PSIsContainer) {
            $_.FullName.Substring($localDir.Length + 1).Replace('\', '/') + '/'
        }
        else {
            $_.FullName.Substring($localDir.Length + 1).Replace('\', '/')
        }
    }

$remoteItems | Where-Object { $_ -notin $localItems } | ForEach-Object {
    $target = "$remoteDir/$_"
    try {
        Invoke-MPRemote @baseArgs "fs" "rm" $target -Silent
        Write-Host "  $RED✗$RESET $target"
    }
    catch {
        try {
            Invoke-MPRemote @baseArgs "fs" "rmdir" $target -Silent
            Write-Host "  $RED✗$RESET $target"
        }
        catch {
            Write-Host "  $YELLOW[WARN]$RESET Failed to remove $target"
        }
    }
}

Write-Host "$BOLDWHITE`Sync complete!$RESET"
