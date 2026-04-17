import RPi.GPIO as GPIO
import time

# Pin Setup
PUL = 17
DIR = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(PUL, GPIO.OUT)
GPIO.setup(DIR, GPIO.OUT)

# Set Direction
GPIO.output(DIR, GPIO.HIGH)

# Move 200 steps
for i in range(200):
    GPIO.output(PUL, GPIO.HIGH)
    time.sleep(0.001) # Controls speed
    GPIO.output(PUL, GPIO.LOW)
    time.sleep(0.001)

GPIO.cleanup()
 