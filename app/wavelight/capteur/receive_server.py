from datetime import datetime, timezone
import socket
import threading
import time
import re
import serial

from app.wavelight.leds.leds import wavelight_blink_leds, turn_leds_off, get_on_time_phase_duration

# Return elapsed time since given clock start time (placeholder)
def now_internal(node_state, server_type):

    # If local clock has not been init yet
    if node_state['time_ref'] is None or node_state['start_real_time'] is None:
        print(f"[{server_type}] Local clock not initialized. Please user [WVL-config] header to set it.")
        return -1  # Will count as expired anyway
    
    # Else return elapsed time
    elapsed = datetime.now(timezone.utc) - node_state['start_real_time']
    return node_state['time_ref'] + elapsed

# Launch proper wavelight parsing, depending of protocol header
# TODO: replace for JSON instead of regex ???
def parse_wvl_protocol(msg, node_state, server_type):

    # Gathering number of parts (a part is between '[...]')
    parts = re.findall(r"\[(.*?)\]", msg)
    if not parts:
        print(f"[{server_type}] No parts found in received message: '{msg}'")
        # client_sock.send(b"[ERROR-HANDLING]\n")
        return 1

    # Extracting header 
    header = parts[0].lower()
    
    # Set handler parsing methods
    dispatch = {
        "wvl-config": handle_config,
        "wvl-start": handle_start
    }

    # Get method name of the handler, given header
    handler = dispatch.get(header)
    
    # Include guard to prevent unknown header
    if handler is None:
        print(f"[{server_type}] Unknown header received: '{header}'")
        return 1

    # Running header parsing method
    if handler:
        handler(parts, node_state, server_type)

# Parsing [WVL-config]
def handle_config(parts, node_state, server_type):

    try:

        # KM ou meters
        unit = parts[1].lower()

        # Get total distance, convertion in meters if required
        distance_total = float(parts[2])
        if unit == "km":
            distance_total *= 1000  # conversion km -> m 
        node_state["distance_total"] = distance_total

        # Get total distance, convertion in meters if required
        node_distance = float(parts[3])
        if unit == "km":
            node_distance *= 1000
        node_state["node_distance"] = node_distance

        # Get desired local clock
        node_state['time_ref'] = datetime.strptime(parts[4], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        node_state['start_real_time'] = datetime.now(timezone.utc)

        # Output given informations
        print(f"[{server_type}][CONFIG] distance_total={node_state['distance_total']} m")
        print(f"[{server_type}][CONFIG] node_distance={node_state['node_distance']} m")
        print(f"[{server_type}][CONFIG] local_clock={node_state['time_ref']} m")

    # An error occured during parsing
    except Exception as e:
        print(f"[{server_type}][ERROR CONFIG]: {e}")
        return 1


# Parsing [WVL-start]
def handle_start(parts, node_state, server_type):

    # Include guards
    if node_state["distance_total"] is None:
        print(f"[{server_type}][START] Total distance not defined. Please configure it using [WVL-config] header.")
        return 1

    try:

        # Desired time to complete the run
        node_state["target_duration"] = float(parts[1])

        # Get run start timestamp
        node_state["start_time"] = datetime.strptime(parts[2], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        print(f"[{server_type}][START] start_time={node_state['start_time']}")
        print(f"[{server_type}][START] target_duration={node_state['target_duration']}")

        # If a previous start thread exists, stop it
        if node_state["start_thread"] and node_state["start_thread"].is_alive():
            print(f"[{server_type}][START] Stopping previous start thread.")
            node_state["start_stop_event"].set()
            node_state["start_thread"].join()

        # Create a new Event for the new thread
        stop_event = threading.Event()
        node_state["start_stop_event"] = stop_event

        # Define the new task
        def task():
            now = now_internal(node_state, server_type)
            if isinstance(now, int) and now == -1:
                print(f"[{server_type}][LED] Cannot run: local clock not initialized.")
                return

            # Course officialy started. We turn both leds off
            turn_leds_off()

            # Theoretical time to reach this point in the race
            led_delay = node_state["node_distance"] * node_state['target_duration'] / node_state["distance_total"]

            # Adding offset so that transition between the two LED
            # is THE best moment for the pacing. Basically we start
            # LEDs a bit sooner to be in the right pace when blinking
            ideal_offset = get_on_time_phase_duration()

            # In case the race already started --- we
            # have to remove a bit of waiting time else 0 removed delay
            elapsed_since_start = (now - node_state["start_time"]).total_seconds()
            elapsed_since_start = max(0, elapsed_since_start)  # Ignoring advance

            # We can compute the final waiting time
            # before blinking LEDs on this node.
            final_wait = max(0, led_delay - ideal_offset - elapsed_since_start)

            print(f"[{server_type}][LED] Raw delay: {led_delay:.2f}s")
            print(f"[{server_type}][LED] Offset: {ideal_offset:.2f}s")
            print(f"[{server_type}][LED] Elapsed: {elapsed_since_start:.2f}s")
            print(f"[{server_type}][LED] Final delay: {final_wait:.2f}s")

            print(f"[{server_type}][LED] Proportional waiting, based on node distance from start point: {final_wait:.2f}s")
            if stop_event.wait(timeout=final_wait):
                print(f"[{server_type}][LED] Start canceled during proportional wait.")
                return

            # Timeout reached. Now blinking leds...
            wavelight_blink_leds()

        # Launch the new thread
        t = threading.Thread(target=task, daemon=True)
        node_state["start_thread"] = t
        t.start()

    except Exception as e:
        print(f"[{server_type}][ERROR START]: {e}")
        return 1

# Send the LoRa message
def send_lora_message(msg, node_state, server_type):

    ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)

    # In case port take time to open...
    time.sleep(1)

    # Adding \n so that LoRa understand this is
    # the end of the message and send it
    ser.write((msg + "\n").encode())

    rx = ser.readline().decode(errors="ignore").strip()
    if rx:
        print("[SENT]: ", rx)

# Using appinventor app
def bluetooth_server(node_state, callback):

    server_type="BLUETOOTH"

    server_sock = socket.socket(
        socket.AF_BLUETOOTH,
        socket.SOCK_STREAM,
        socket.BTPROTO_RFCOMM
    )

    server_sock.bind(("00:00:00:00:00:00", 1))
    server_sock.listen(1)

    print(f"[{server_type}] Server ready.")

    try:

        while True:

            client_sock, client_info = server_sock.accept()
            print(f"[{server_type}] Client connected : {client_info}.")

            try:

                while True:

                    data = client_sock.recv(1024)

                    if not data:
                        print(f"[{server_type}] Client disconnected.")
                        break

                    msg = data.decode("utf-8").strip()
                    print(f"[{server_type}] Received message: {msg}")

                    callback(msg, node_state, server_type)

            except ConnectionResetError:
                print(f"[{server_type}] Client disconnected abruptly.")

            except Exception as e:
                print(f"[{server_type}] Error with client : {e}")

            finally:
                try:
                    client_sock.close()
                except Exception:
                    pass

                print(f"[{server_type}] Connection closed. Waiting for new connection...")

    except KeyboardInterrupt:
        print(f"\n[{server_type}] Manual stop initiated.")

    finally:
        try:
            server_sock.close()
        except Exception:
            pass

# Using master raspberry pi
def lora_server(node_state):

    server_type="LoRa"

    # TODO: remove hardcoded ttyUSB0 and
    # baudrate, read from conf file instead
    ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)

    print(f"[{server_type}] Server ready.")

    while True:

        data = ser.readline().decode(errors="ignore").strip()

        if not data:
            print(f"[{server_type}] Message received but no data.")
            continue

        msg = data.decode("utf-8").strip()
        print(f"[{server_type}] Received message: {msg}")

        parse_wvl_protocol(msg, node_state, server_type)

# use command 'nc 127.0.0.1 9999' to test locally without bluetooth.
# example of usage:
# [WVL-config][m][1000][500][2026-05-08 16:20:00]
# [WVL-start][120][2026-05-08 16:20:30]
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
                parse_wvl_protocol(line, node_state, server_type)

    client_sock.close()
