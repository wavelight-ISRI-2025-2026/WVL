#!/bin/bash

set -e

PROJECT_DIR="/opt/all-code"
RUN_SCRIPT="${PROJECT_DIR}/scripts/run_wavelight_checked.sh"
SERVICE_FILE="/etc/systemd/system/wavelight.service"
USER_NAME="${SUDO_USER:-$(whoami)}"

echo "======================================"
echo "   INSTALLATION AUTOSTART WAVELIGHT"
echo "======================================"
echo "Utilisateur : $USER_NAME"
echo "Projet      : $PROJECT_DIR"
echo "Script run  : $RUN_SCRIPT"
echo

if [ ! -d "$PROJECT_DIR" ]; then
    echo "[ERROR] Projet introuvable : $PROJECT_DIR"
    exit 1
fi

if [ ! -f "$RUN_SCRIPT" ]; then
    echo "[ERROR] Script de vérification introuvable : $RUN_SCRIPT"
    exit 1
fi

chmod +x "$RUN_SCRIPT"

echo "[1/3] Création du service systemd..."

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Wavelight auto start
After=multi-user.target bluetooth.service bt-auto-agent.service network-online.target
Wants=bluetooth.service bt-auto-agent.service network-online.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=$PROJECT_DIR
ExecStartPre=/bin/sleep 10
ExecStart=/bin/bash $RUN_SCRIPT
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "[2/3] Activation du service..."

sudo systemctl daemon-reload
sudo systemctl enable wavelight.service

echo "[3/3] Vérification..."

if systemctl is-enabled --quiet wavelight.service; then
    echo "[OK] wavelight.service activé au démarrage"
else
    echo "[ERROR] wavelight.service non activé"
    exit 1
fi

echo
echo "======================================"
echo "        AUTOSTART INSTALLÉ"
echo "======================================"
echo
echo "Pour tester maintenant :"
echo "  sudo systemctl start wavelight.service"
echo
echo "Pour voir les logs :"
echo "  journalctl -u wavelight.service -f"
echo
echo "Pour désactiver :"
echo "  sudo systemctl disable wavelight.service"
echo "  sudo systemctl stop wavelight.service"