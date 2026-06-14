import threading
import time
from pathlib import Path

from app.wavelight.leds import leds
from app.wavelight.capteur import healthcheck
from app.wavelight.capteur.receive_server import bluetooth_server, lora_server, local_server, send_lora_message, parse_wvl_protocol

# Where the node store locally sent data
# This is set here so that thread share the same variables.
node_state = {
    "distance_total": None,   # in meters
    "node_distance": None,    # in meters
    "start_time": None,       # datetime format
    "target_duration": None,  # in secondes
    "time_ref": None,         # placeholder
    "start_real_time": None,  # placeholder
    "start_thread": None,     # Thread qui gère l’allumage de la LED
    "start_stop_event": None  # Event pour arrêter le thread si WVL-start arrive
}

def main():

    print("[WAVELIGHT] Starting system")

    # Clearing previous execution, if required
    # We turn both LEDs off, in case they are on
    leds.turn_leds_off()

    # Do one-shot healthcheck
    healthcheck.healthcheck()

    # We are either master or slave
    # 1 - A master can only send LoRa messages
    # 2 - Slaves can receives bluetooth and LoRa messages
    # Status is determined by the existance of '/master' file.

    if Path("/master").exists():

        # Only accept bluetooth.
        threading.Thread(target=bluetooth_server, args=(node_state,send_lora_message), daemon=True).start()

    else:

        # A raspberry can receive data:
        #
        # - using bluetooth
        # - using lora
        # - locally at 127.0.0.1:9999

        # Thread for bluetooth, LoRa and local
        # We pass node_state here so that every thread share the same variables.
        threading.Thread(target=lora_server, args=(node_state,), daemon=True).start()
        threading.Thread(target=local_server, args=(node_state,), daemon=True).start()
        threading.Thread(target=bluetooth_server, args=(node_state,parse_wvl_protocol), daemon=True).start()

        # Do not stop process until CTRL+C
        while True:
            time.sleep(1)


if __name__ == "__main__":
    main()