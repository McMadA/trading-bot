#!/bin/bash

# setup_pi.sh - Setup script for Paper Trading System on Raspberry Pi

set -e  # Exit on error

# Ensure we are in the correct directory
if [ ! -f "main.py" ]; then
    echo "Error: Please run this script from the 'paper-trading' directory where main.py resides."
    exit 1
fi

USER=$(whoami)
WORKING_DIR=$(pwd)
VENV_DIR="$WORKING_DIR/venv"
SERVICE_NAME="paper-trading.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"

echo "Setting up Paper Trading System for user: $USER in $WORKING_DIR"

# 1. Update system and install python3-venv if needed
echo "--> Checking for python3-venv..."
if ! dpkg -s python3-venv >/dev/null 2>&1; then
    echo "python3-venv not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y python3-venv
else
    echo "python3-venv is already installed."
fi

# 2. Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "--> Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# 3. Install dependencies
echo "--> Installing dependencies from requirements.txt..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

# 4. Create systemd service file
echo "--> Creating systemd service file..."

cat <<EOF > paper-trading.service
[Unit]
Description=Paper Trading System
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$WORKING_DIR
ExecStart=$VENV_DIR/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 5. Install and start service
echo "--> Installing service to $SERVICE_FILE..."
sudo mv paper-trading.service "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo "---------------------------------------------------"
echo "Setup Complete!"
echo "Service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager
echo ""
echo "You can check logs with: sudo journalctl -u $SERVICE_NAME -f"
echo "Web dashboard should be available at http://$(hostname -I | awk '{print $1}'):5000"
echo "---------------------------------------------------"
