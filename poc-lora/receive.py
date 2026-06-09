import serial
import time

PORT = "/dev/ttyUSB1"
BAUDRATE = 9600

ser = serial.Serial(PORT, BAUDRATE, timeout=1)
time.sleep(2)

print("En attente de messages LoRa...")

while True:
    line = ser.readline().decode("utf-8", errors="ignore").strip()

    if line.startswith("RECV:"):
        print("Message reçu :", line)
