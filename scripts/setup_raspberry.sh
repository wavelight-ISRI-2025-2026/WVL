#!/bin/bash

set -e

PROJECT_DIR="/opt/all-code"
VENV_DIR="${PROJECT_DIR}/.venv"
USER_NAME="$(whoami)"

echo "======================================"
echo "     WAVELIGHT RASPBERRY SETUP"
echo "======================================"
echo "Utilisateur : $USER_NAME"
echo "Projet      : $PROJECT_DIR"
echo "Venv        : $VENV_DIR"
echo

echo "[1/8] Mise à jour des paquets..."
sudo apt update

echo
echo "[2/8] Installation des paquets système..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-rpi.gpio \
    bluetooth \
    bluez \
    bluez-tools \
    pi-bluetooth \
    openssh-server \
    git \
    net-tools

echo
echo "[3/8] Activation du service SSH..."
sudo systemctl enable ssh
sudo systemctl start ssh

if systemctl is-active --quiet ssh; then
    echo "[OK] SSH actif"
else
    echo "[ERROR] SSH n'est pas actif"
    exit 1
fi

echo
echo "[4/8] Activation et configuration du service Bluetooth..."

# --- AJOUT : Automatisation du mode de compatibilité (-C) et profil SPP ---
echo "[Bluetooth] Application du mode de compatibilité -C dans systemd..."
# Ajoute "-C" à la ligne ExecStart si ce n'est pas déjà fait
BLUETOOTHD_PATH="$(command -v bluetoothd)"

if [ -z "$BLUETOOTHD_PATH" ]; then
    echo "[ERROR] bluetoothd introuvable"
    exit 1
fi

echo "[OK] bluetoothd trouvé : $BLUETOOTHD_PATH"

sudo mkdir -p /etc/systemd/system/bluetooth.service.d

sudo tee /etc/systemd/system/bluetooth.service.d/override.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=${BLUETOOTHD_PATH} -C
ExecStartPost=-/usr/bin/sdptool add SP
EOF

# --- Configuration optionnelle du nom de la machine ---
CURRENT_HOSTNAME="$(hostname)"

echo
echo "[Système] Nom actuel de la machine : $CURRENT_HOSTNAME"
read -p "Nouveau nom de la balise ? Appuie sur Entrée pour garder '$CURRENT_HOSTNAME' : " NEW_HOSTNAME

if [ -n "$NEW_HOSTNAME" ] && [ "$NEW_HOSTNAME" != "$CURRENT_HOSTNAME" ]; then
    echo "[Système] Changement du hostname vers : $NEW_HOSTNAME"

    echo "$NEW_HOSTNAME" | sudo tee /etc/hostname > /dev/null

    if grep -q "^127.0.1.1" /etc/hosts; then
        sudo sed -i "s/^127.0.1.1.*/127.0.1.1	$NEW_HOSTNAME/g" /etc/hosts
    else
        echo -e "127.0.1.1\t$NEW_HOSTNAME" | sudo tee -a /etc/hosts > /dev/null
    fi

    sudo hostnamectl set-hostname "$NEW_HOSTNAME"

    echo "[OK] Hostname configuré : $NEW_HOSTNAME"
    echo "[INFO] Le nouveau nom sera complètement appliqué après redémarrage."
else
    echo "[OK] Hostname conservé : $CURRENT_HOSTNAME"
fi

# Rechargement de systemd pour appliquer les modifications du service Bluetooth
sudo systemctl daemon-reload
sudo systemctl enable --force bluetooth
sudo systemctl restart bluetooth
sleep 2

# Configuration des timeouts Bluetooth standard
if grep -q "^#\?DiscoverableTimeout" /etc/bluetooth/main.conf; then
    sudo sed -i 's/^#\?DiscoverableTimeout.*/DiscoverableTimeout = 0/' /etc/bluetooth/main.conf
else
    sudo sed -i '/^\[General\]/a DiscoverableTimeout = 0' /etc/bluetooth/main.conf
fi

if grep -q "^#\?PairableTimeout" /etc/bluetooth/main.conf; then
    sudo sed -i 's/^#\?PairableTimeout.*/PairableTimeout = 0/' /etc/bluetooth/main.conf
else
    sudo sed -i '/^\[General\]/a PairableTimeout = 0' /etc/bluetooth/main.conf
fi

sudo systemctl restart bluetooth
sleep 2

if systemctl is-active --quiet bluetooth; then
    echo "[OK] Bluetooth actif avec mode -C et profil SPP"
else
    echo "[ERROR] Bluetooth n'est pas actif après configuration"
    exit 1
fi

sudo bluetoothctl <<EOF
power on
pairable on
discoverable on
show
EOF

echo "[OK] Bluetooth configuré en pairable/discoverable"

echo
echo "[Bluetooth] Installation de l'agent d'appairage automatique NoInputNoOutput..."

if command -v bt-agent >/dev/null 2>&1; then
    echo "[OK] bt-agent disponible"
else
    echo "[ERROR] bt-agent introuvable. Vérifie que bluez-tools est bien installé."
    exit 1
fi

sudo tee /usr/local/bin/bt-auto-agent.sh > /dev/null <<'EOF'
#!/bin/bash

# Agent Bluetooth automatique pour système sans écran.
# Il maintient la Raspberry visible, pairable, et accepte les appairages en NoInputNoOutput.

while true; do
    rfkill unblock bluetooth || true
    systemctl start bluetooth || true

    bluetoothctl power on || true
    bluetoothctl discoverable on || true
    bluetoothctl pairable on || true

    bt-agent --capability=NoInputNoOutput

    # Si bt-agent s'arrête/crash, on attend un peu puis on relance.
    sleep 2
done
EOF

sudo chmod +x /usr/local/bin/bt-auto-agent.sh

sudo tee /etc/systemd/system/bt-auto-agent.service > /dev/null <<EOF
[Unit]
Description=Bluetooth Auto Pairing Agent
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/local/bin/bt-auto-agent.sh
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable bt-auto-agent.service
sudo systemctl restart bt-auto-agent.service
sleep 1

if systemctl is-active --quiet bt-auto-agent.service; then
    echo "[OK] Agent Bluetooth automatique actif"
else
    echo "[ERROR] Agent Bluetooth automatique inactif"
    exit 1
fi

echo
echo "[Bluetooth] Vérification du profil Serial Port..."

sudo chmod 777 /var/run/sdp || true
sudo sdptool add SP || true

if sudo sdptool browse local | grep -q "Service Name: Serial Port"; then
    echo "[OK] Service Serial Port présent"
else
    echo "[ERROR] Service Serial Port absent"
    exit 1
fi
echo
echo "[5/8] Ajout de l'utilisateur aux groupes gpio/bluetooth/dialout..."
sudo usermod -aG gpio,bluetooth,dialout "$USER_NAME"
echo "[OK] Groupes ajoutés à $USER_NAME"
echo "[INFO] Redémarrage nécessaire pour appliquer les groupes."

echo
echo "[Sécurité] Configuration des privilèges sudo sans mot de passe pour $USER_NAME..."

SUDOERS_FILE="/etc/sudoers.d/wavelight-nopasswd"

sudo tee "$SUDOERS_FILE" > /dev/null <<EOF
$USER_NAME ALL=(ALL) NOPASSWD: ALL
EOF

sudo chmod 0440 "$SUDOERS_FILE"

if sudo visudo -cf "$SUDOERS_FILE" && sudo visudo -c; then
    echo "[OK] Privilèges sudo sans mot de passe validés et actifs pour $USER_NAME."
else
    echo "[ERROR] Erreur de syntaxe détectée dans la configuration sudo, suppression par sécurité."
    sudo rm -f "$SUDOERS_FILE"
    exit 1
fi

echo
echo "[6/8] Vérification du dossier projet..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo "[ERROR] Le dossier projet n'existe pas : $PROJECT_DIR"
    echo
    echo "Copie d'abord ton projet dans /opt/all-code."
    echo "Exemple si ton projet est dans ~/all-code :"
    echo "  sudo mkdir -p /opt"
    echo "  sudo cp -r ~/all-code /opt/all-code"
    echo "  sudo chown -R $USER_NAME:$USER_NAME /opt/all-code"
    exit 1
fi

sudo chown -R "$USER_NAME:$USER_NAME" "$PROJECT_DIR"
echo "[OK] Projet trouvé"

echo
echo "[7/8] Création de l'environnement Python virtuel..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
    echo "[OK] Environnement virtuel créé : $VENV_DIR"
else
    echo "[OK] Environnement virtuel déjà existant : $VENV_DIR"
fi

echo
echo "[8/8] Installation des dépendances Python..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    "$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
    echo "[OK] requirements.txt installé"
else
    echo "[WARN] Aucun requirements.txt trouvé."
    echo "[WARN] Ce n'est pas bloquant si tu n'as pas de dépendances pip."
fi

echo
echo "======================================"
echo "          VÉRIFICATION RAPIDE"
echo "======================================"

PYTHONPATH="$PROJECT_DIR" "$VENV_DIR/bin/python" - <<EOF
import sys
import socket

print("Python utilisé :", sys.executable)

try:
    import RPi.GPIO
    print("[OK] RPi.GPIO disponible")
except Exception as e:
    print("[ERROR] RPi.GPIO indisponible :", e)

try:
    test_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    test_sock.close()
    print("[OK] Socket Bluetooth RFCOMM disponible")
except Exception as e:
    print("[ERROR] Socket Bluetooth RFCOMM indisponible :", e)

try:
    import app.wavelight.wavelight
    print("[OK] Import app.wavelight.wavelight réussi")
except Exception as e:
    print("[ERROR] Import app.wavelight.wavelight impossible :", e)
EOF

echo
echo "======================================"
echo "          SETUP TERMINÉ"
echo "======================================"
echo
echo "IMPORTANT : redémarre la Raspberry pour appliquer les groupes :"
echo
echo "  sudo reboot"
echo
echo "Après redémarrage, lance ton programme avec :"
echo
echo "  cd ${PROJECT_DIR}"
echo "  source .venv/bin/activate"
echo "  python3 -m app.wavelight.wavelight"
echo
echo "Ou sans activer le venv :"
echo
echo "  cd ${PROJECT_DIR}"
echo "  PYTHONPATH=${PROJECT_DIR} ${VENV_DIR}/bin/python -m app.wavelight.wavelight"