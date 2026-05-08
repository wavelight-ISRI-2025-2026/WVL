import RPi.GPIO as GPIO
import time

# Configuration
GPIO.setmode(GPIO.BOARD)
PIN_LED_1  = 27
PIN_LED_2  = 17
GPIO.setup(PIN_LED_1, GPIO.OUT)
GPIO.setup(PIN_LED_2, GPIO.OUT)

# Paramètres de la séquence
DELAI_DEBUT   = 1.0    # secondes entre clignotements au départ 
DELAI_FIN     = 0.05   # secondes entre clignotements à la fin 
ETAPES        = 10     # nombre d'étapes d'accélération
DUREE_CONTINU = 5.0    # secondes allumée en continu avant d'inverser

def clignoter(pin, delai, nb_fois):
    """Fait clignoter une LED nb_fois avec un délai donné."""
    for _ in range(nb_fois):
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(delai)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(delai)

try:
    print("Séquence démarrage...")

    # Phase 1 : LED verte accélère progressivement 
    for i in range(ETAPES):
        # Interpolation exponentielle : lent -> rapide
        t = i / (ETAPES - 1)
        delai = DELAI_DEBUT * ((DELAI_FIN / DELAI_DEBUT) ** t)
        clignoter(PIN_LED_1, delai, 1)

    # Phase 2 : LED verte allumée en continu (moitié du temps) 
    print("LED verte : continu")
    GPIO.output(PIN_LED_1, GPIO.HIGH)
    time.sleep(DUREE_CONTINU / 2)

    # Phase 3 : LED jaune prend le relais (moitié du temps)
    print("LED jaune : continu, LED verte éteinte")
    GPIO.output(PIN_LED_2, GPIO.HIGH)
    GPIO.output(PIN_LED_1, GPIO.LOW)
    time.sleep(DUREE_CONTINU / 2)

    # Phase 4 : LED jaune décélère progressivement 
    for i in range(ETAPES):
        t = i / (ETAPES - 1)
        delai = DELAI_FIN * ((DELAI_DEBUT / DELAI_FIN) ** t)  # rapide -> lent
        clignoter(PIN_LED_2, delai, 1)

    # Fin : tout éteint
    GPIO.output(PIN_LED_2, GPIO.LOW)
    print("Séquence terminée.")

except KeyboardInterrupt:
    print("\nArrêt manuel.")

finally:
    GPIO.cleanup()

# TODO
# TURN ON LED 1 AT RASPBERRY START TO SAY SYSTEM OK
# BLINK LED 2 AT RASPBERRY TO SAY A PROBLEM IS OCCURING
# WHEN COURSE START TURN OF ALL LEDS, WAIT FOR MY TURN TO BLINK --> ALSO CHANGE BLINK PROCESS ?
# WHEN COURSE END, ENABLE BACK LED 1 TO SAY SYSTEM OK
