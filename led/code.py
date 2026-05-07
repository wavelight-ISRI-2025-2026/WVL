import RPi.GPIO as GPIO
import time

# Configuration
GPIO.setmode(GPIO.BCM)
PIN_VERTE  = 27
PIN_JAUNE  = 17
GPIO.setup(PIN_VERTE, GPIO.OUT)
GPIO.setup(PIN_JAUNE, GPIO.OUT)

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
        clignoter(PIN_VERTE, delai, 1)

    # Phase 2 : LED verte allumée en continu (moitié du temps) 
    print("LED verte : continu")
    GPIO.output(PIN_VERTE, GPIO.HIGH)
    time.sleep(DUREE_CONTINU / 2)

    # Phase 3 : LED jaune prend le relais (moitié du temps)
    print("LED jaune : continu, LED verte éteinte")
    GPIO.output(PIN_JAUNE, GPIO.HIGH)
    GPIO.output(PIN_VERTE, GPIO.LOW)
    time.sleep(DUREE_CONTINU / 2)

    # Phase 4 : LED jaune décélère progressivement 
    for i in range(ETAPES):
        t = i / (ETAPES - 1)
        delai = DELAI_FIN * ((DELAI_DEBUT / DELAI_FIN) ** t)  # rapide -> lent
        clignoter(PIN_JAUNE, delai, 1)

    # Fin : tout éteint
    GPIO.output(PIN_JAUNE, GPIO.LOW)
    print("Séquence terminée.")

except KeyboardInterrupt:
    print("\nArrêt manuel.")

finally:
    GPIO.cleanup()
