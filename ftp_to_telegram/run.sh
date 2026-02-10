#!/usr/bin/with-contenv bashio

echo "Starte FTP to Telegram Bridge..."

# 1. Werte aus der Home Assistant Config (options.json) auslesen
# 2. Als Environment-Variable exportieren (Großschreibung für Python)

export FTP_HOST=$(bashio::config 'ftp_host')
export FTP_USER=$(bashio::config 'ftp_user')
export FTP_PASS=$(bashio::config 'ftp_pass')
export FTP_PORT=$(bashio::config 'ftp_port')

export BOT_TOKEN=$(bashio::config 'bot_token')
export CHAT_ID=$(bashio::config 'chat_id')

export TARGET_FPS=$(bashio::config 'target_fps')
export DELETE_AFTER_SUCCESS=$(bashio::config 'delete_after_success')

# Startet dein Python-Programm
python3 /ftp_to_telegram.py