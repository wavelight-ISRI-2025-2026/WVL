import time
from app.wavelight.leds import leds
import socket


# One-shot healthcheck at process startup.
# Turn LED2 off/blink if problem.
def healthcheck():

    # No error by default.
    error_code = 0

    # Check 1: is bluetooth active ?
    try:
        test_sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        test_sock.close()
    except Exception:
        print("[HEALTHCHECK] Bluetooth unavailable.")
        error_code = 1  # 1 blink = Bluetooth problem

    # Check 2: ...

    # If an error as occured
    if error_code != 0:

        # Problem detected: blink LED2 according to error_code
        leds.set_led_on_time_powerstate(True)  # LED1 always ON
        leds.blink_led(leds.PIN_LED_IS_LATE, final_state=True, times=error_code, interval=0.5)
        print(f"[HEALTHCHECK] Error detected: code {error_code}")
        return 0

    # Everything OK
    leds.set_led_on_time_powerstate(True)
    leds.set_led_is_late_powerstate(True)
    print("[HEALTHCHECK] All systems OK.")