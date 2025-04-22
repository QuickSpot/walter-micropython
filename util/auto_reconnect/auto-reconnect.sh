#!/bin/bash
if ! mpremote version &> /dev/null; then
    echo "Warning: 'mpremote' is not installed or not in your PATH." >&2
    exit 1
fi

DEVICE=$1

if [ -n "$DEVICE" ]; then
    DEVICE="connect $DEVICE"
fi

trap "echo; echo 'Exiting...'; exit" SIGINT

while true; do
    mpremote $DEVICE
    if [ $? -ne 0 ]; then
        tput cuu1 && tput el
    fi
    sleep 0.5
done