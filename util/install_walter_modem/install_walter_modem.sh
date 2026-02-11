#!/bin/bash
set -e

cleanup() {
    tput cnorm 2>/dev/null
}
trap cleanup EXIT INT TERM

BOLDWHITE='\033[1;37m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
RESET='\033[0m'

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0
    tput civis 2>/dev/null
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  %s  " "${spinstr[i]}"
        i=$(( (i+1) % ${#spinstr[@]} ))
        sleep $delay
    done
    printf "\r\033[K"
    tput cnorm 2>/dev/null
}

# Verify dependencies
if ! command -v mpremote &>/dev/null; then
    echo -e "${RED}Error:${RESET} 'mpremote' is not installed or not in your PATH." >&2
    exit 1
fi

# Build device connection argument
DEVICE_ARG=""
if [ -n "$1" ]; then
    DEVICE_ARG="connect $1"
fi

PROJECT_DIR=$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")
LOCAL_DIR="${PROJECT_DIR}/walter_modem"
REMOTE_DIR=":lib/walter_modem"

# Clean and prepare remote directory
echo -e "${BOLDWHITE}Preparing remote directory${RESET}"
mpremote $DEVICE_ARG fs rm -r "$REMOTE_DIR" &>/dev/null || true
mpremote $DEVICE_ARG fs mkdir ":lib" &>/dev/null || true
mpremote $DEVICE_ARG fs mkdir "$REMOTE_DIR" &>/dev/null || true
echo -e "  ${RED}[CLEAN]${RESET}${REMOTE_DIR}"

cd "$LOCAL_DIR"

# Create subdirectories
echo -e "${BOLDWHITE}Creating directory structure${RESET}"
find . -type d ! -name '.' | sort | while read -r d; do
    mpremote $DEVICE_ARG fs mkdir "$REMOTE_DIR/${d#./}" &>/dev/null || true
    echo -e "  ${BLUE}[DIR]${RESET}  ${REMOTE_DIR}/${d#./}"
done

# Copy all files except *.pyi
echo -e "${BOLDWHITE}Copying library files${RESET}"
find . -type f ! -name '*.pyi' | sort | while read -r f; do
    printf "  ${YELLOW}•${RESET} ${REMOTE_DIR}/${f#./}"
    (mpremote $DEVICE_ARG fs cp "$f" "$REMOTE_DIR/${f#./}" &>/dev/null) &
    spinner $!
    echo -e "\r  ${GREEN}[FILE]${RESET} ${REMOTE_DIR}/${f#./}"
done

echo -e "${BOLDWHITE}Sync Complete!${RESET}"
