from datetime import datetime, timezone, timedelta
import socket
import threading
import time
import re
import serial
import csv
import os

from app.wavelight.leds.leds import (
    wavelight_blink_leds,
    turn_leds_off,
    get_on_time_phase_duration,
    blink_green_packet_ok,
    blink_red_packet_error,
)

CSV_LOG_FILE = os.path.expanduser("~/wavelight_tests.csv")

CSV_FIELDS = [
    "log_time",
    "distance_total_m",
    "node_distance_m",
    "target_duration_s",
    "start_time",
    "theoretical_green_on_time",
    "theoretical_green_to_red_time",
    "real_green_on_time",
    "real_green_to_red_time",
    "green_on_error_s",
    "green_to_red_error_s",
]


def dt_to_csv(value):
    if value is None:
        return ""
    return value.isoformat()


def seconds_error(real_time, theoretical_time):
    if real_time is None or theoretical_time is None:
        return ""
    return (real_time - theoretical_time).total_seconds()


def append_test_log(row):
    file_exists = os.path.exists(CSV_LOG_FILE)

    with open(CSV_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)

        if not file_exists or os.path.getsize(CSV_LOG_FILE) == 0:
            writer.writeheader()

        writer.writerow(row)

    print(f"[CSV] Test logged in {CSV_LOG_FILE}")

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

    parts = re.findall(r"\[(.*?)\]", msg)
    if not parts:
        print(f"[{server_type}] No parts found in received message: '{msg}'")
        blink_red_packet_error()
        return 1

    header = parts[0].lower()

    dispatch = {
        "wvl-config": handle_config,
        "wvl-start": handle_start
    }

    handler = dispatch.get(header)

    if handler is None:
        print(f"[{server_type}] Unknown header received: '{header}'")
        blink_red_packet_error()
        return 1

    # Running header parsing method
    if handler:
        handler(parts, node_state, server_type)

# Parsing [WVL-config]
def handle_config(parts, node_state, server_type):

    try:
        if len(parts) != 5:
            print(f"[{server_type}][CONFIG] Invalid number of fields: expected 5, got {len(parts)}")
            blink_red_packet_error()
            return 1

        unit = parts[1].lower()

        if unit not in ("m", "km"):
            print(f"[{server_type}][CONFIG] Invalid unit: {unit}. Expected 'm' or 'km'.")
            blink_red_packet_error()
            return 1

        distance_total = float(parts[2])
        node_distance = float(parts[3])

        if unit == "km":
            distance_total *= 1000
            node_distance *= 1000

        if distance_total <= 0:
            print(f"[{server_type}][CONFIG] distance_total must be > 0")
            blink_red_packet_error()
            return 1

        if node_distance < 0 or node_distance > distance_total:
            print(f"[{server_type}][CONFIG] node_distance invalid")
            blink_red_packet_error()
            return 1

        time_ref = datetime.strptime(parts[4], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        node_state["distance_total"] = distance_total
        node_state["node_distance"] = node_distance
        node_state["time_ref"] = time_ref
        node_state["start_real_time"] = datetime.now(timezone.utc)

        # Output given informations
        print(f"[{server_type}][CONFIG] distance_total={node_state['distance_total']} m")
        print(f"[{server_type}][CONFIG] node_distance={node_state['node_distance']} m")
        print(f"[{server_type}][CONFIG] local_clock={node_state['time_ref']} m")

        blink_green_packet_ok()
        return 0

    # An error occured during parsing
    except Exception as e:
        print(f"[{server_type}][ERROR CONFIG]: {e}")
        blink_red_packet_error()
        return 1


# Parsing [WVL-start]
def handle_start(parts, node_state, server_type):

    if len(parts) != 3:
        print(f"[{server_type}][START] Invalid number of fields: expected 3, got {len(parts)}")
        blink_red_packet_error()
        return 1

    # Include guards
    required_keys = ["distance_total", "node_distance", "time_ref", "start_real_time"]

    for key in required_keys:
        if node_state[key] is None:
            print(f"[{server_type}][START] Missing config value: {key}")
            blink_red_packet_error()
            return 1

    try:

        # Desired time to complete the run
        node_state["target_duration"] = float(parts[1])

        # Check
        if node_state["distance_total"] <= 0:
            print(f"[{server_type}][START] distance_total must be > 0")
            blink_red_packet_error()
            return 1

        if node_state["target_duration"] <= 0:
            print(f"[{server_type}][START] target_duration must be > 0")
            blink_red_packet_error()
            return 1

        if node_state["node_distance"] < 0 or node_state["node_distance"] > node_state["distance_total"]:
            print(f"[{server_type}][START] node_distance invalid")
            blink_red_packet_error()
            return 1

        # Get run start timestamp
        node_state["start_time"] = datetime.strptime(parts[2], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

        print(f"[{server_type}][START] start_time={node_state['start_time']}")
        print(f"[{server_type}][START] target_duration={node_state['target_duration']}")

        blink_green_packet_ok()

        # If a previous start thread exists, stop it
        if node_state["start_thread"] and node_state["start_thread"].is_alive():
            print(f"[{server_type}][START] Stopping previous start thread.")
            node_state["start_stop_event"].set()
            node_state["start_thread"].join()

        # Create a new Event for the new thread
        stop_event = threading.Event()
        node_state["start_stop_event"] = stop_event

        def task():
            # Course officiellement démarrée : on éteint les LEDs au départ
            turn_leds_off()

            # Temps théorique, en secondes, pour atteindre ce nœud
            led_delay = (
                node_state["node_distance"]
                * node_state["target_duration"]
                / node_state["distance_total"]
            )

            # Instant exact où le coureur doit arriver à ce nœud
            target_passage_time = node_state["start_time"] + timedelta(seconds=led_delay)

            # Durée entre le début de la séquence LED et le passage vert -> rouge
            green_phase_duration = get_on_time_phase_duration()

            # Instant exact où il faut lancer la séquence LED
            led_start_time = target_passage_time - timedelta(seconds=green_phase_duration)

            print(f"[{server_type}][LED] Passage attendu : {target_passage_time}")
            print(f"[{server_type}][LED] Début séquence LED : {led_start_time}")
            print(f"[{server_type}][LED] Durée phase verte : {green_phase_duration:.2f}s")

            real_times = {
                "green_on": None,
                "green_to_red": None,
            }


            def mark_green_on():
                now = now_internal(node_state, server_type)
                if not isinstance(now, int):
                    real_times["green_on"] = now
                    print(f"[{server_type}][LED] Real green ON time: {now}")


            def mark_green_to_red():
                now = now_internal(node_state, server_type)
                if not isinstance(now, int):
                    real_times["green_to_red"] = now
                    print(f"[{server_type}][LED] Real green->red time: {now}")

            while not stop_event.is_set():
                now = now_internal(node_state, server_type)

                if isinstance(now, int) and now == -1:
                    print(f"[{server_type}][LED] Cannot run: local clock not initialized.")
                    return

                # On compare l'horloge locale à l'instant absolu prévu
                if now >= led_start_time:
                    break

                time.sleep(0.05)

            if stop_event.is_set():
                print(f"[{server_type}][LED] Start canceled before LED sequence.")
                return

            print(f"[{server_type}][LED] Starting LED sequence now.")

            # La transition vert -> rouge arrivera exactement à target_passage_time,
            # car on a démarré la séquence avec l'avance green_phase_duration.
            wavelight_blink_leds(
                on_green_on=mark_green_on,
                on_green_to_red=mark_green_to_red
            )

            append_test_log({
                "log_time": dt_to_csv(now_internal(node_state, server_type)),
                "distance_total_m": node_state["distance_total"],
                "node_distance_m": node_state["node_distance"],
                "target_duration_s": node_state["target_duration"],
                "start_time": dt_to_csv(node_state["start_time"]),
                "theoretical_green_on_time": dt_to_csv(led_start_time),
                "theoretical_green_to_red_time": dt_to_csv(target_passage_time),
                "real_green_on_time": dt_to_csv(real_times["green_on"]),
                "real_green_to_red_time": dt_to_csv(real_times["green_to_red"]),
                "green_on_error_s": seconds_error(real_times["green_on"], led_start_time),
                "green_to_red_error_s": seconds_error(real_times["green_to_red"], target_passage_time),
            })

        # Launch the new thread
        t = threading.Thread(target=task, daemon=True)
        node_state["start_thread"] = t
        t.start()

        return 0

    except Exception as e:
        print(f"[{server_type}][ERROR START]: {e}")
        blink_red_packet_error()
        return 1

# Send the LoRa message
def send_lora_message(msg, node_state, server_type):

    while True:
        try:
            ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)
            break  # Exit loop if successful
        except serial.SerialException as e:
            print(f"[{server_type}] Error opening serial port: {e}")
            print(f"[{server_type}] Retrying in 5 seconds...")
            time.sleep(5)

    while True:
        try:
            # In case port takes time to open...
            time.sleep(1)

            # Adding \n so that LoRa understands this is
            # the end of the message and sends it
            ser.write((msg + "\n").encode())

            rx = ser.readline().decode(errors="ignore").strip()
            if rx:
                print("[SENT]: ", rx)
            break  # Exit loop after successful send

        except serial.SerialException as e:
            print(f"[{server_type}] Serial port error: {e}")
            print(f"[{server_type}] USB0 disconnected. Restarting...")
            ser.close()
            return send_lora_message(msg, node_state, server_type)

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

    server_type = "LoRa"

    while True:
        try:
            ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)
            print(f"[{server_type}] Serial port opened successfully.")
            break  # Exit loop if successful
        except serial.SerialException as e:
            print(f"[{server_type}] Error opening serial port: {e}")
            print(f"[{server_type}] USB0 disconnected. Retrying...")
            time.sleep(5)

    print(f"[{server_type}] Server ready.")

    while True:
        try:
            data = ser.readline().decode(errors="ignore").strip()

            if not data:
                continue

            msg = data.strip()
            print(f"[{server_type}] Received message: {msg}")

            parse_wvl_protocol(msg, node_state, server_type)

        except serial.SerialException as e:
            print(f"[{server_type}] Serial port error: {e}")
            print(f"[{server_type}] USB0 disconnected. Restarting server...")
            ser.close()
            return lora_server(node_state)

# use command 'nc 127.0.0.1 9999' to test locally without bluetooth.
# example of usage:
# [WVL-config][m][1000][500][2026-05-08 16:20:00]
# [WVL-start][120][2026-05-08 16:20:30]
# def local_server(node_state):

#     server_type="LOCAL"

#     while True: 

#         try: 

#             server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#             server_sock.bind(("127.0.0.1", 9999))
#             server_sock.listen(1)

#             print(f"[{server_type}] Server ready.")

#             client_sock, client_info = server_sock.accept()
#             print(f"[{server_type}] Client connected : {client_info}.")

#             buffer = ""

#             while True:
#                 data = client_sock.recv(1024)
#                 if not data:
#                     break

#                 buffer += data.decode("utf-8", errors="ignore")

#                 while "\n" in buffer:
#                     line, buffer = buffer.split("\n", 1)
#                     line = line.strip()

#                     if line:
#                         parse_wvl_protocol(line, client_sock, node_state, server_type)

#             client_sock.close()

#         except Exception as e:

#             print(f"[{server_type}][ERROR]: {e}")
#             print(f"[{server_type}] Restarting server...")
#             continue  # Restart from 0
