#!/bin/bash

set -e

PROJECT_DIR="/opt/all-code"
VENV_DIR="${PROJECT_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
USER_NAME="$(whoami)"

ERRORS=0

prepare_bluetooth_visibility() {
    echo
    echo "[Bluetooth] Préparation de la visibilité Bluetooth..."

    # On s'assure que systemd a bien pris en compte le mode -C au cas où
    sudo systemctl daemon-reload
    sudo rfkill unblock bluetooth || true
    sudo systemctl start bluetooth
    sleep 2

    # Force le contrôleur à adopter le nom configuré dans la machine (balise001)
    CURRENT_HOSTNAME=$(hostname)
    echo "[Bluetooth] Forçage du nom de diffusion Bluetooth à : $CURRENT_HOSTNAME"
    
    sudo bluetoothctl <<EOF
power on
system-alias $CURRENT_HOSTNAME
agent on
default-agent
pairable on
discoverable on
show
EOF

    if sudo bluetoothctl show | grep -q "Discoverable: yes"; then
        ok "Bluetooth discoverable : yes"
    else
        fail "Bluetooth n'est pas discoverable"
    fi

    if sudo bluetoothctl show | grep -q "Pairable: yes"; then
        ok "Bluetooth pairable : yes"
    else
        fail "Bluetooth n'est pas pairable"
    fi
}

ok() {
    echo "[OK] $1"
}

warn() {
    echo "[WARN] $1"
}

fail() {
    echo "[ERROR] $1"
    ERRORS=$((ERRORS + 1))
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        ok "Commande disponible : $1"
    else
        fail "Commande manquante : $1"
    fi
}

check_service_active() {
    if systemctl is-active --quiet "$1"; then
        ok "Service actif : $1"
    else
        fail "Service inactif : $1"
    fi
}

check_file() {
    if [ -f "$1" ]; then
        ok "Fichier trouvé : $1"
    else
        fail "Fichier manquant : $1"
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        ok "Dossier trouvé : $1"
    else
        fail "Dossier manquant : $1"
    fi
}

check_group() {
    if groups "$USER_NAME" | grep -qw "$1"; then
        ok "Utilisateur $USER_NAME dans le groupe : $1"
    else
        warn "Utilisateur $USER_NAME absent du groupe : $1"
        warn "Si tu viens de lancer setup_raspberry.sh, fais : sudo reboot"
    fi
}

echo "======================================"
echo "     WAVELIGHT CHECK + RUN"
echo "======================================"
echo "Utilisateur : $USER_NAME"
echo "Projet      : $PROJECT_DIR"
echo "Venv        : $VENV_DIR"
echo

echo "[1/8] Vérification des commandes système..."
check_command python3
check_command bluetoothctl
check_command systemctl
check_command sdptool
check_command rfkill

echo
echo "[2/8] Vérification des services..."
check_service_active ssh
check_service_active bluetooth

prepare_bluetooth_visibility

echo
echo "[Bluetooth] Vérification du profil Serial Port..."

sudo chmod 777 /var/run/sdp || true
sudo sdptool add SP || true

if sudo sdptool browse local | grep -q "Service Name: Serial Port"; then
    ok "Service Serial Port présent"
else
    fail "Service Serial Port absent"
fi

echo
echo "[3/8] Vérification des groupes utilisateur..."
check_group gpio
check_group bluetooth
check_group dialout

echo
echo "[4/8] Vérification des dossiers..."
check_dir "$PROJECT_DIR"
check_dir "$VENV_DIR"

echo
echo "[5/8] Vérification des fichiers du projet..."
check_file "$PROJECT_DIR/app/wavelight/wavelight.py"
check_file "$PROJECT_DIR/app/wavelight/leds/leds.py"
check_file "$PROJECT_DIR/app/wavelight/leds/leds.cfg"
check_file "$PROJECT_DIR/app/wavelight/capteur/receive_server.py"
check_file "$PROJECT_DIR/app/wavelight/capteur/healthcheck.py"

echo
echo "[6/8] Vérification de l'environnement Python..."
if [ -x "$PYTHON_BIN" ]; then
    ok "Python du venv disponible : $PYTHON_BIN"
else
    fail "Python du venv introuvable : $PYTHON_BIN"
fi

echo
echo "[7/8] Vérification des imports Python..."

if [ -x "$PYTHON_BIN" ]; then
    set +e
    PYTHONPATH="$PROJECT_DIR" "$PYTHON_BIN" - <<EOF
import sys
import socket

errors = 0

def ok(msg):
    print(f"[OK] {msg}")

def fail(msg):
    global errors
    errors += 1
    print(f"[ERROR] {msg}")

print("Python utilisé :", sys.executable)

try:
    import RPi.GPIO
    ok("Module RPi.GPIO disponible")
except Exception as e:
    fail(f"Module RPi.GPIO indisponible : {e}")

try:
    import app.wavelight.leds.leds
    ok("Import app.wavelight.leds.leds réussi")
except Exception as e:
    fail(f"Import app.wavelight.leds.leds impossible : {e}")

try:
    import app.wavelight.capteur.healthcheck
    ok("Import app.wavelight.capteur.healthcheck réussi")
except Exception as e:
    fail(f"Import app.wavelight.capteur.healthcheck impossible : {e}")

try:
    import app.wavelight.capteur.receive_server
    ok("Import app.wavelight.capteur.receive_server réussi")
except Exception as e:
    fail(f"Import app.wavelight.capteur.receive_server impossible : {e}")

try:
    test_sock = socket.socket(
        socket.AF_BLUETOOTH,
        socket.SOCK_STREAM,
        socket.BTPROTO_RFCOMM
    )
    test_sock.close()
    ok("Socket Bluetooth RFCOMM disponible")
except Exception as e:
    fail(f"Socket Bluetooth RFCOMM indisponible : {e}")

sys.exit(errors)
EOF
    PYTHON_CHECK_RESULT=$?
    set -e

    if [ "$PYTHON_CHECK_RESULT" -ne 0 ]; then
        ERRORS=$((ERRORS + PYTHON_CHECK_RESULT))
    fi
fi

echo
echo "[8/8] Vérification qu'aucune autre instance ne tourne..."
if pgrep -f "app.wavelight.wavelight" >/dev/null 2>&1; then
    fail "Une instance de Wavelight semble déjà tourner."
    echo "Pour l'arrêter :"
    echo "  pkill -f app.wavelight.wavelight"
else
    ok "Aucune autre instance Wavelight détectée"
fi

echo
echo "======================================"
echo "              RÉSUMÉ"
echo "======================================"

if [ "$ERRORS" -ne 0 ]; then
    echo "[ERROR] Environnement non prêt : $ERRORS erreur(s)."
    echo "Le programme ne sera pas lancé."
    exit 1
fi

echo "[OK] Environnement prêt."
echo
echo "Lancement de Wavelight..."
echo

cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR"
exec "$PYTHON_BIN" -m app.wavelight.wavelight