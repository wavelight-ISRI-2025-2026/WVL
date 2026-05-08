# wavelight.py

from capteur.bluetooth_server import bluetooth_server
# from led.led import allumer_led

import threading


def main():
    
    print("[WAVELIGHT] Démarrage système")

    # Thread Bluetooth
    bt_thread = threading.Thread(target=bluetooth_server, daemon=True)
    bt_thread.start()

    # Boucle principale (placeholder)
    while True:
        pass


if __name__ == "__main__":
    main()