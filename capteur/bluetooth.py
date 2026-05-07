import socket
import re
from datetime import datetime, timedelta
import subprocess
import time
import threading
from queue import Queue

# =========================================================
# FILE DE MESSAGES (thread-safe)
# =========================================================

bt_queue = Queue()


# =========================================================
# GESTION DU TEMPS
# =========================================================

def set_system_time(dt):
    """
    Synchronise l'heure système du Raspberry Pi.
    """
    try:
        subprocess.run(["sudo", "date", "-s", dt.strftime("%Y-%m-%d %H:%M:%S")], check=True)
        subprocess.run(["sudo", "hwclock", "--systohc"], check=True)
        print(f"[TIME] Heure synchronisée : {dt}")
    except Exception as e:
        print(f"[ERREUR] Sync heure : {e}")


# =========================================================
# GESTION LED (simulation)
# =========================================================

def allumer_led_async(temps_sec, heure_allumage):
    """
    Allume la LED à un instant précis (non bloquant).
    """
    def task():
        print(f"[LED] Attente jusqu'à {heure_allumage.time()}")

        while datetime.now() < heure_allumage:
            time.sleep(0.02)

        print("[LED] ALLUMÉ")
        time.sleep(temps_sec)
        print("[LED] ÉTEINT")

    threading.Thread(target=task, daemon=True).start()


# =========================================================
# THREAD RÉCEPTION BLUETOOTH (IMPORTANT)
# =========================================================

def bluetooth_client_handler(client_sock, client_info):
    """
    Gère UN client Bluetooth dans un thread dédié.
    
    Rôle :
    - Lire les données en continu
    - Reconstituer les messages (\n)
    - Les envoyer dans une Queue
    """

    print(f"[BT] Client connecté : {client_info}")

    buffer = ""

    try:
        while True:
            data = client_sock.recv(1024)

            if not data:
                break

            buffer += data.decode("utf-8", errors="ignore")

            # Gestion des messages complets
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()

                if line:
                    print(f"[BT RX] {line}")
                    bt_queue.put((line, client_sock))

    except Exception as e:
        print(f"[BT] Erreur client : {e}")

    finally:
        print(f"[BT] Déconnexion : {client_info}")
        client_sock.close()


# =========================================================
# SERVEUR BLUETOOTH
# =========================================================

def demarrer_serveur():
    """
    Serveur Bluetooth multi-clients.
    
    Chaque client est géré dans un thread séparé.
    """

    server_sock = socket.socket(
        socket.AF_BLUETOOTH,
        socket.SOCK_STREAM,
        socket.BTPROTO_RFCOMM
    )

    server_sock.bind(("00:00:00:00:00:00", 1))
    server_sock.listen(5)

    print("[BT] Serveur prêt (multi-clients)")

    while True:
        client_sock, client_info = server_sock.accept()

        # Thread par client
        threading.Thread(
            target=bluetooth_client_handler,
            args=(client_sock, client_info),
            daemon=True
        ).start()


# =========================================================
# PARSING PROTOCOLE
# =========================================================

# Variable globale (ex: config balise)
dist_balise = None

def parse_wvl_protocol(raw_msg, client_sock):
    """
    Traite les messages du protocole WVL.
    """

    global dist_balise

    parts = re.findall(r"\[(.*?)\]", raw_msg)
    if not parts:
        return

    header = parts[0]

    try:
        match header:

            # =========================================
            # CONFIGURATION
            # =========================================
            case "WVL-conf":
                """
                [WVL-conf][distance][date]
                """

                dist_balise = float(parts[1])
                sync_time = datetime.strptime(parts[2], "%Y-%m-%d %H:%M:%S")

                set_system_time(sync_time)

                print(f"[CONFIG] Distance balise = {dist_balise}")

                # ACK optionnel
                client_sock.send(b"[ACK-CONF]\n")


            # =========================================
            # DÉPART COURSE
            # =========================================
            case "WVL-start":
                """
                [WVL-start][distance_totale][temps_total]
                """

                if dist_balise is None:
                    print("[ERREUR] Balise non configurée")
                    return

                dist_totale = float(parts[1])
                temps_total = float(parts[2])

                print("[START] Départ reçu")

                # Calcul proportionnel
                temps_allumage_sec = dist_balise * temps_total / dist_totale
                heure_allumage = datetime.now() + timedelta(seconds=temps_allumage_sec)

                allumer_led_async(temps_allumage_sec, heure_allumage)

                client_sock.send(b"[ACK-START]\n")

    except (ValueError, IndexError) as e:
        print(f"[ERREUR] Parsing : {e}")


# =========================================================
# BOUCLE PRINCIPALE (CONSOMMATEUR QUEUE)
# =========================================================

def message_dispatcher():
    """
    Thread principal de traitement des messages.
    
    Avantage :
    - Sépare réception (I/O) et logique métier
    - Plus stable et scalable
    """

    while True:
        msg, client_sock = bt_queue.get()
        parse_wvl_protocol(msg, client_sock)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    print("[SYSTEM] Démarrage Bluetooth PRO")

    # Thread serveur Bluetooth
    threading.Thread(target=demarrer_serveur, daemon=True).start()

    # Thread traitement messages
    threading.Thread(target=message_dispatcher, daemon=True).start()

    # Boucle principale
    while True:
        time.sleep(1)
