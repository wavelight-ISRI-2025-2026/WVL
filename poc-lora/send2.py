import serial
import time

ser = serial.Serial("/dev/ttyUSB0", 9600, timeout=1)
time.sleep(2)

counter = 0

while True:
    msg = f"Ping {counter}"
    ser.write((msg + "\n").encode())

    print("TX:", msg)

    rx = ser.readline().decode(errors="ignore").strip()
    if rx:
        print("RX:", rx)

    counter += 1
    time.sleep(2)