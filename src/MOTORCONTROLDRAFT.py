from gpiozero import PWMOutputDevice, DigitalOutputDevice
from fastapi import FastAPI
from time import sleep
STEP_PIN=17
DIR_PIN=27
ENA_PIN=22
FREQ_HZ=0

STEP = DigitalOutputDevice(STEP_PIN, active_high=True, initial_value=False)
# DIRECTION = DigitalOutputDevice(DIR_PIN, active_high=True, initial_value=False)
ENABLE = DigitalOutputDevice(ENA_PIN, active_high=False, initial_value=True) if ENA_PIN is not None else None

HALF_PERIOD = 1/(2*FREQ_HZ)

app = FastAPI()

@app.post("/move_absolute")
def move_motor_abs(freq_hz: float, direction: str):
    global FREQ_HZ
    FREQ_HZ = freq_hz
    print(HALF_PERIOD)

    direction.on()

    if ENABLE:
        ENABLE.off()
        
    STEP.on()
    sleep(HALF_PERIOD)
    STEP.off()


