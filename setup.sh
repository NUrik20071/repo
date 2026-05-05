#!/data/data/com.termux/files/usr/bin/bash
echo "=== Miyabi Bot — первый запуск ==="
read -p "Вставьте TELEGRAM_BOT_TOKEN: " TOKEN
read -p "Вставьте ваш ADMIN_ID: " ADMIN_ID
echo "export TELEGRAM_BOT_TOKEN="\"" >> ~/.bashrc
echo "export ADMIN_ID="\8434752311"" >> ~/.bashrc
export TELEGRAM_BOT_TOKEN="$TOKEN"
export ADMIN_ID="$ADMIN_ID"
pip install -r requirements.txt
python main.py
