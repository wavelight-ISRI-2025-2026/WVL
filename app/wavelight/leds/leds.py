import configparser
import os
import RPi.GPIO as GPIO
import time

cfg_file = os.path.join(os.path.dirname(__file__), "leds.cfg")
config = configparser.ConfigParser()
config.read_string("[DEFAULT]\n" + open(cfg_file).read())

PIN_LED_ON_TIME = int(config["DEFAULT"]["PIN_LED_ON_TIME"])
PIN_LED_IS_LATE = int(config["DEFAULT"]["PIN_LED_IS_LATE"])
START_DELAY = float(config["DEFAULT"]["START_DELAY"])
END_DELAY = float(config["DEFAULT"]["END_DELAY"])
STEPS = int(config["DEFAULT"]["STEPS"])
FINAL_STEP_TIMEOUT = float(config["DEFAULT"]["FINAL_STEP_TIMEOUT"])

# --- GPIO setup ---
GPIO.setmode(GPIO.BOARD)
GPIO.setup(PIN_LED_ON_TIME, GPIO.OUT)
GPIO.setup(PIN_LED_IS_LATE, GPIO.OUT)

def set_led_on_time_powerstate(state: bool):
    GPIO.output(PIN_LED_ON_TIME, GPIO.HIGH if state else GPIO.LOW)

def set_led_is_late_powerstate(state: bool):
    GPIO.output(PIN_LED_IS_LATE, GPIO.HIGH if state else GPIO.LOW)

def turn_leds_off():
    GPIO.output(PIN_LED_ON_TIME, GPIO.LOW)
    GPIO.output(PIN_LED_IS_LATE, GPIO.LOW)

def blink_led(target_led, final_state: bool, times: int, interval: float = 0.5):

    # LED initial state
    initial_state = GPIO.input(target_led)
    
    for _ in range(times):
        # Reversing state
        GPIO.output(target_led, not initial_state)
        time.sleep(interval)
        GPIO.output(target_led, initial_state)
        time.sleep(interval)
    
    # Put back to initial state
    GPIO.output(target_led, initial_state)

def wavelight_blink_leds():

    try:
        pass

    except KeyboardInterrupt:
        print("\nManual arrest.")
    finally:
        GPIO.cleanup()
