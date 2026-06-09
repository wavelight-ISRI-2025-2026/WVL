import serial

ser = serial.Serial("/dev/ttyUSB1", 9600, timeout=1)

print("Listening...")

while True:
    line = ser.readline().decode(errors="ignore").strip()
    if line:
        print("LoRa RX:", line)