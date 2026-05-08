from datetime import datetime, timezone
import socket
import threading
import time
import re

# Return elapsed time since given clock start time (placeholder)
def now_internal(node_state, server_type):

    # If local clock has not been init yet
    if node_state['time_ref'] is None or node_state['start_real_time'] is None:
        print(f"[{server_type}] Local clock not initialized. Please user [WVL-config] header to set it.")
        return -1  # Will count as expired anyway
    
    # Else return elapsed time
    elapsed = datetime.now(timezone.utc) - node_state['start_real_time']
    return node_state['time_ref'] + elapsed

# placeholder for leds. replace using ./led/led.py
def run_led_logic(server_type):
    print(f"[{server_type}][LED] ON")
    time.sleep(1)
    print(f"[{server_type}][LED] OFF")

# Launch proper wavelight parsing, depending of protocol header
# TODO: replace for JSON instead of regex ???
def parse_wvl_protocol(msg, client_sock, node_state, server_type):

    # Gathering number of parts (a part is between '[...]')
    parts = re.findall(r"\[(.*?)\]", msg)
    if not parts:
        print(f"[{server_type}] No parts found in received message: '{msg}'")
        client_sock.send(b"[ERROR-HANDLING]\n")
        return 1

    # Extracting header 
    header = parts[0].lower()
    
    # Set handler parsing methods
    dispatch = {
        "wvl-config": handle_config,
        "wvl-distance": handle_distance,
        "wvl-start": handle_start
    }

    # Get method name of the handler, given header
    handler = dispatch.get(header)
    
    # Include guard to prevent unknown header
    if handler is None:
        print(f"[{server_type}] Unknown header received: '{header}'")
        client_sock.send(b"[ERROR-HANDLING]\n")
        return 1

    # Running header parsing method
    if handler:
        handler(parts, client_sock, node_state, server_type)

# Parsing [WVL-config]
def handle_config(parts, client_sock, node_state, server_type):

    try:

        # KM ou meters
        unit = parts[1].lower()

        # Get total distance, convertion in meters if required
        distance_total = float(parts[2])
        if unit == "km":
            distance_total *= 1000  # conversion km -> m 
        node_state["distance_total"] = distance_total

        # Get desired local clock
        node_state['time_ref'] = datetime.fromisoformat(parts[3])
        node_state['start_real_time'] = datetime.now(timezone.utc)

        # Output given informations
        print(f"[{server_type}][CONFIG] distance_total={node_state['distance_total']} m")
        print(f"[{server_type}][CONFIG] local_clock={node_state['time_ref']} m")

        # Acknowledging client that distance has been set successfully
        client_sock.send(b"[ACK-CONFIG]\n")

    # An error occured during parsing
    except Exception as e:
        print(f"[{server_type}][ERROR CONFIG]: {e}")
        client_sock.send(b"[ERROR-CONFIG]\n")
        return 1

# Parsing [WVL-distance]
def handle_distance(parts, client_sock, node_state, server_type):

    try:

        # KM ou meters
        unit = parts[1].lower()

        # Get total distance, convertion in meters if required
        node_distance = float(parts[2])
        if unit == "km":
            node_distance *= 1000
        node_state["node_distance"] = node_distance

        # Output given informations
        print(f"[{server_type}][DISTANCE] node_distance={node_state['node_distance']} m")

        # Acknowledging client that distance has been set successfully
        client_sock.send(b"[ACK-DISTANCE]\n")

    # An error occured during parsing
    except Exception as e:
        print(f"[{server_type}][ERROR DISTANCE]: {e}")
        client_sock.send(b"[ERROR-DISTANCE]\n")
        return 1

# Parsing [WVL-start]
def handle_start(parts, client_sock, node_state, server_type):

    # Include guards
    if node_state["distance_total"] is None:
        print(f"[{server_type}][START] Total distance not defined. Please configure it using [WVL-config] header.")
        client_sock.send(b"[ERROR-START]\n")
        return 1
        
    if node_state["node_distance"] is None:
        print(f"[{server_type}][START] Local distance not defined. Please configure it using [WVL-distance] header.")
        client_sock.send(b"[ERROR-START]\n")
        return 1

    try:

        # Get run start timestamp
        node_state["start_time"] = datetime.fromisoformat(parts[1])

        # Desired time to complete the run
        node_state["target_duration"] = float(parts[2])

        print(f"[{server_type}][START] start_time={node_state['start_time']}")
        print(f"[{server_type}][START] target_duration={node_state['target_duration']}")

        # Acknowledging client
        client_sock.send(b"[ACK-START]\n")

        # compute delay for LED for this node
        def task():

            now = now_internal(node_state, server_type)  # we get the local clock
            # We then compute delay before making led blink
            delay = (node_state['start_time'] - now).total_seconds()

            # Note: maybe this condition should be removed.
            # what if a raspberry glitch mid run ? we won't be able to set it up
            if delay < 0:  # Error if start timestamp has expired
                print(f"[LED] Invalid start time: timestamp already expired.")
                return 1

            # Before waiting for LEd blink,
            # we have to wait for run to start
            if delay > 0:
                print(f"[LED] Waiting before run start: {delay:.2f} seconds.")
                time.sleep(delay)

            # Wait to blink LED
            led_delay = node_state["node_distance"] * node_state['target_duration'] / node_state["distance_total"]
            print(f"[{server_type}][LED] Attente proportionnelle à la distance du noeud: {led_delay:.2f}s")
            time.sleep(led_delay)

            run_led_logic()

        threading.Thread(target=task, daemon=True).start()

    except Exception as e:
        print(f"[{server_type}][ERROR START]: {e}")
        client_sock.send(b"[ERROR-START]\n")
        return 1

# Using appinventor app
def bluetooth_server(node_state):
    
    server_type="BLUETOOTH"
    server_sock = socket.socket(
        socket.AF_BLUETOOTH,
        socket.SOCK_STREAM,
        socket.BTPROTO_RFCOMM
    )
    server_sock.bind(("00:00:00:00:00:00", 1))
    server_sock.listen(1)

    print(f"[{server_type}] Server ready.")

    client_sock, client_info = server_sock.accept()
    print(f"[{server_type}] Client connected : {client_info}.")

    buffer = ""

    while True:
        data = client_sock.recv(1024)
        if not data:
            break

        buffer += data.decode("utf-8", errors="ignore")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()

            if line:
                parse_wvl_protocol(line, client_sock, node_state, server_type)

    client_sock.close()

# TODO: lora
# Using master raspberry pi
def lora_server(node_state):
    print("[LORA] Server not implemented yet.")

# use command 'nc 127.0.0.1 9999' to test locally without bluetooth.
# example of usage:
# [WVL-config][m][1000][2026-05-08T16:20:00+00:00]
# [WVL-distance][m][500]
# [WVL-start][2026-05-08T16:20:30+00:00][120]
def local_server(node_state):

    server_type="LOCAL"
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 9999))
    server_sock.listen(1)

    print(f"[{server_type}] Server ready.")

    client_sock, client_info = server_sock.accept()
    print(f"[{server_type}] Client connected : {client_info}.")

    buffer = ""

    while True:
        data = client_sock.recv(1024)
        if not data:
            break

        buffer += data.decode("utf-8", errors="ignore")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()

            if line:
                parse_wvl_protocol(line, client_sock, node_state, server_type)

    client_sock.close()
