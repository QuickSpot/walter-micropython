#!/bin/bash
if ! mpremote version &> /dev/null; then
    echo "Warning: 'mpremote' is not installed or not in your PATH." >&2
    exit 1
fi

DEVICE=$1

if [ -n "$DEVICE" ]; then
    DEVICE="connect $DEVICE"
fi

PROJECT_DIR=$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")

mpremote $DEVICE mkdir :lib
mpremote $DEVICE cp -r "${PROJECT_DIR}/walter_modem" :lib/