import serial
import time

PORT = "/dev/ttyACM0"
BAUDRATE = 115200

ser = serial.Serial(PORT, BAUDRATE, timeout=1)
time.sleep(2)

print("En attente de messages LoRa...")

while True:
    line = ser.readline().decode("utf-8", errors="ignore").strip()

    if line.startswith("RECV:"):
        print("Message reçu :", line)
