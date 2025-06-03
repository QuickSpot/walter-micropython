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
    tput civis 2>/dev/null  # Hide cursor
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  %s  " "${spinstr[i]}"
        i=$(( (i+1) % ${#spinstr[@]} ))
        sleep $delay
    done
    printf "\r\033[K"  # Clear line
    tput cnorm 2>/dev/null  # Show cursor
}

# Verify dependencies
if ! command -v mpremote &>/dev/null; then
    echo -e "${RED}Warning:${RESET} 'mpremote' is not installed or not in your PATH." >&2
    exit 1
fi

DEVICE=$1
if [ -n "$DEVICE" ]; then
    DEVICE="connect $DEVICE"
fi

PROJECT_DIR=$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")
LOCAL_DIR="${PROJECT_DIR}/walter_modem"
REMOTE_DIR=":lib/walter_modem"

echo -e "${BOLDWHITE}Verifying directory structure${RESET}"
mpremote $DEVICE fs mkdir ":lib" &>/dev/null || true
mpremote $DEVICE fs mkdir "$REMOTE_DIR" &>/dev/null || true

cd "$LOCAL_DIR"

# Create all directories (except .)
echo -e "${BOLDWHITE}Copying library files${RESET}"
find . -type d | while read -r d; do
    [ "$d" = "." ] && continue
    mpremote $DEVICE fs mkdir "$REMOTE_DIR/${d#./}" &>/dev/null || true
    echo -e "  ${BLUE}[DIR]${RESET}  ${REMOTE_DIR}/${d#./}"
done

# Copy all files except *.pyi
find . -type f ! -name '*.pyi' | while read -r f; do
    printf "  ${YELLOW}•${RESET} ${REMOTE_DIR}/${f#./}"
    (
        mpremote $DEVICE fs cp "$LOCAL_DIR/$f" "$REMOTE_DIR/${f#./}" &>/dev/null
    ) &
    cp_pid=$!
    spinner $cp_pid
    echo -e "\r  ${GREEN}[FILE]${RESET} ${REMOTE_DIR}/${f#./}"
done

echo -e "${BOLDWHITE}Cleaning up remote files not present locally${RESET}"

# ---

REMOTE_LIST=$(mpremote $DEVICE fs ls -r "$REMOTE_DIR" | awk '{$1=""; print substr($0,2)}' | sed 's|^/||')
LOCAL_LIST=$(find . -type f ! -name '*.pyi' -printf "%P\n"; find . -type d -printf "%P/\n")

# Clean up remote files/dirs not present locally
CLEANED_REMOTE_LIST=()
for entry in $REMOTE_LIST; do
    if [[ "$entry" == "$REMOTE_DIR/"* ]]; then
        cleaned="${entry#$REMOTE_DIR/}"
    else
        cleaned="$entry"
    fi
    [[ -z "$cleaned" || "$cleaned" == "$REMOTE_DIR" || "$cleaned" == "." ]] && continue
    [[ "$cleaned" == "$REMOTE_DIR"* ]] && continue
    CLEANED_REMOTE_LIST+=("$cleaned")
done

for remote_item in "${CLEANED_REMOTE_LIST[@]}"; do
    if ! grep -Fxq "$remote_item" <<< "$LOCAL_LIST"; then
        echo -e "  ${RED}[REMOVED]${RESET} ${REMOTE_DIR}/$remote_item"
        mpremote $DEVICE fs rm "$REMOTE_DIR/$remote_item" &>/dev/null || \
        mpremote $DEVICE fs rmdir "$REMOTE_DIR/$remote_item" &>/dev/null || true
    fi
done

echo -e "${BOLDWHITE}Sync Complete!${RESET}"
