import threading

from app.wavelight.leds import leds
from app.wavelight.capteur.receive_server import bluetooth_server, lora_server, local_server

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

    # TODO
    # LED INIT HERE ???
    # TURN ON LED 1 AT RASPBERRY START TO SAY SYSTEM OK
    # BLINK LED 2 AT RASPBERRY TO SAY A PROBLEM IS OCCURING
    # WHEN COURSE START TURN OF ALL LEDS, WAIT FOR MY TURN TO BLINK --> ALSO CHANGE BLINK PROCESS ?
    # WHEN COURSE END, ENABLE BACK LED 1 TO SAY SYSTEM OK
    # MAKE BOTH LEDS BLINK WHEN SENDING MSG TO SERVER ? ([WVL-config/distance/start]?)

    print("[WAVELIGHT] Starting system")

    # A raspberry can receive data:
    #
    # - using bluetooth
    # - using lora
    # - locally at 127.0.0.1:9999

    # Thread for bluetooth, LoRa and local
    # We pass node_state here so that every thread share the same variables.
    threading.Thread(target=lora_server, args=(node_state,), daemon=True).start()
    threading.Thread(target=local_server, args=(node_state,), daemon=True).start()
    threading.Thread(target=bluetooth_server, args=(node_state,), daemon=True).start()

    # Do not stop process until CTRL+C
    while True:
        pass


if __name__ == "__main__":
    main()