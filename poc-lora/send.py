import serial
import time

PORT = "/dev/ttyUSB0"
BAUDRATE = 9600

ser = serial.Serial(PORT, BAUDRATE, timeout=1)
time.sleep(2)

counter = 0

while True:
    message = f"Hello LoRa {counter}"
    ser.write((message + "\n").encode("utf-8"))

    print("Envoyé :", message)

    response = ser.readline().decode("utf-8", errors="ignore").strip()
    if response:
        print("Feather :", response)

    counter += 1
    time.sleep(2)
