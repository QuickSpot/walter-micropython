#!/bin/bash
if ! mpremote version &> /dev/null; then
    echo "Warning: 'mpremote' is not installed or not in your PATH." >&2
    exit 1
fi

DIR_NAME=$1
DEVICE=$2

if [ -n "$DEVICE" ]; then
    DEVICE="connect $DEVICE"
fi

mpremote $DEVICE exec "import os

def remove_dir(path):
    for filename in os.listdir(path):
        filepath = path + '/' + filename
        if os.stat(filepath)[0] & 0x4000:
            remove_dir(filepath)
        else:
            os.remove(filepath)
    os.rmdir(path)

remove_dir('${DIR_NAME}')
" 