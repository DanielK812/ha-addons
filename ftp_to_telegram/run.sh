#!/usr/bin/env bash
set -euo pipefail

# Set defaults from config
export FTP_HOST="${FTP_HOST:-""}"
export FTP_USER="${FTP_USER:-""}"
export FTP_PASS="${FTP_PASS:-""}"
export FTP_PORT="${FTP_PORT:-"21"}"
export BOT_TOKEN="${BOT_TOKEN:-""}"
export CHAT_ID="${CHAT_ID:-""}"
export TARGET_FPS="${TARGET_FPS:-"0"}"
export DELETE_AFTER_SUCCESS="${DELETE_AFTER_SUCCESS:-"false"}"

python ./ftp_to_telegram.py
