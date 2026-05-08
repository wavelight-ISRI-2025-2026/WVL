import configparser
import os
# import RPi.GPIO as GPIO
import time

# Chargement global au moment de l'import
cfg_file = os.path.join(os.path.dirname(__file__), "leds.cfg")
config = configparser.ConfigParser()
config.read_string("[DEFAULT]\n" + open(cfg_file).read())  # Trick pour lire key=value sans section

PIN_LED_ON_TIME = int(config["DEFAULT"]["PIN_LED_ON_TIME"])
PIN_LED_IS_LATE = int(config["DEFAULT"]["PIN_LED_IS_LATE"])
START_DELAY = float(config["DEFAULT"]["START_DELAY"])
END_DELAY = float(config["DEFAULT"]["END_DELAY"])
STEPS = int(config["DEFAULT"]["STEPS"])
FINAL_STEP_TIMEOUT = float(config["DEFAULT"]["FINAL_STEP_TIMEOUT"])


def wavelight_blink_leds():
    pass

# # --- GPIO setup ---
# GPIO.setmode(GPIO.BOARD)
# GPIO.setup(PIN_LED_ON_TIME, GPIO.OUT)
# GPIO.setup(PIN_LED_IS_LATE, GPIO.OUT)

# def clignoter(pin, delai, nb_fois):
#     """Fait clignoter une LED nb_fois avec un délai donné."""
#     for _ in range(nb_fois):
#         GPIO.output(pin, GPIO.HIGH)
#         time.sleep(delai)
#         GPIO.output(pin, GPIO.LOW)
#         time.sleep(delai)

# def wavelight_blink_leds():
#     try:
#         print("Séquence démarrage...")

#         # Phase 1 : LED verte accélère progressivement 
#         for i in range(STEPS):
#             t = i / (STEPS - 1)
#             delai = START_DELAY * ((END_DELAY / START_DELAY) ** t)
#             clignoter(PIN_LED_ON_TIME, delai, 1)

#         # Phase 2 : LED verte allumée en continu (moitié du temps) 
#         print("LED verte : continu")
#         GPIO.output(PIN_LED_ON_TIME, GPIO.HIGH)
#         time.sleep(FINAL_STEP_TIMEOUT / 2)

#         # Phase 3 : LED jaune prend le relais (moitié du temps)
#         print("LED jaune : continu, LED verte éteinte")
#         GPIO.output(PIN_LED_IS_LATE, GPIO.HIGH)
#         GPIO.output(PIN_LED_ON_TIME, GPIO.LOW)
#         time.sleep(FINAL_STEP_TIMEOUT / 2)

#         # Phase 4 : LED jaune décélère progressivement 
#         for i in range(STEPS):
#             t = i / (STEPS - 1)
#             delai = END_DELAY * ((START_DELAY / END_DELAY) ** t)
#             clignoter(PIN_LED_IS_LATE, delai, 1)

#         # Fin : tout éteint
#         GPIO.output(PIN_LED_IS_LATE, GPIO.LOW)
#         print("Séquence terminée.")

#     except KeyboardInterrupt:
#         print("\nArrêt manuel.")
#     finally:
#         GPIO.cleanup()
