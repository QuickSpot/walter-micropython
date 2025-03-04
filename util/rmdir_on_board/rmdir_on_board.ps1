#!/usr/bin/env pwsh
[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)]
    [string]$DIR_NAME,

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

$pythonScript = @"
import os

def remove_dir(path):
    for filename in os.listdir(path):
        filepath = path + '/' + filename
        if os.stat(filepath)[0] & 0x4000:
            remove_dir(filepath)
        else:
            os.remove(filepath)
    os.rmdir(path)

remove_dir('$DIR_NAME')
"@

if ($DEVICE) {
    # If a device is provided, use "connect <DEVICE>" before exec.
    & python -m mpremote connect $DEVICE exec $pythonScript
} else {
    & python -m mpremote exec $pythonScript
}