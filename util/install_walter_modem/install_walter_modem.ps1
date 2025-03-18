#!/usr/bin/env pwsh

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$DEVICE
)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Error: 'python' is not installed or not in your PATH."
    exit 1
}

try {
    & python -m mpremote version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Warning: 'mpremote' is not installed or not available through Python."
        exit 1
    }
} catch {
    Write-Error "Error: Unable to run 'python -m mpremote'. Ensure Python is installed and the mpremote module is available."
    exit 1
}

$baseArgs = @()
if ($DEVICE) {
    $baseArgs += "connect"
    $baseArgs += $DEVICE
}

$scriptPath = $MyInvocation.MyCommand.Path
$dirInfo = (Get-Item -Path $scriptPath).Directory
for ($i = 0; $i -lt 2; $i++) {
    if ($null -ne $dirInfo.Parent) {
        $dirInfo = $dirInfo.Parent
    }
}
$projectDir = $dirInfo.FullName

$mkdirArgs = $baseArgs + "mkdir" + ":lib"
Write-Host "Executing: python -m mpremote $($mkdirArgs -join ' ')"
& python -m mpremote @mkdirArgs

$sourcePath = Join-Path $projectDir "walter_modem"
$cpArgs = $baseArgs + "cp" + "-r" + $sourcePath + ":lib/"
Write-Host "Executing: python -m mpremote $($cpArgs -join ' ')"
& python -m mpremote @cpArgs