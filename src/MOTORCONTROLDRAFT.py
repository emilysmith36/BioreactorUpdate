from fastapi import FastAPI
from threading import Thread, Event
from gpiozero import DigitalOutputDevice
from time import sleep

app = FastAPI()

STEP_PIN = 17
DIR_PIN = 27
ENA_PIN = 22

step = DigitalOutputDevice(STEP_PIN)
direction = DigitalOutputDevice(DIR_PIN)
enable = DigitalOutputDevice(ENA_PIN, active_high=False, initial_value=True)

stop_event = Event()

def move_steps(steps, freq_hz, direction_val):
    print("getting into move_steps")
    half_period = 1 / (2 * freq_hz)

    if (direction_val == "up"):
        direction.on()
    else:
        direction.off()

    enable.off()

    for _ in range(abs(steps)):
        if stop_event.is_set():
            break
            
        step.on()
        sleep(half_period)
        step.off()
        sleep(half_period)

    enable.on()
    stop_event.clear()

def jog(freq_hz, direction_val):
    print("getting into jog")
    half_period = 1 / (2 * freq_hz)
    
    if direction_val == "up":
        direction.on()
    else:
        direction.off()

    enable.off()

    while not stop_event.is_set():
        step.on()
        sleep(half_period)
        step.off()
        sleep(half_period)

    enable.on()
    stop_event.clear()

#api routes

@app.post("/api/motor/move-absolute")
def move_absolute(data:dict):
    print("inside move_absolute in control")
    target = float(data["target"])
    steps = int(target / 0.003048) #needs calibration, how many mm is each step

    Thread(target=move_steps, args=(steps, 20, 1)).start()
    return {"status": "moving"}

@app.post("/api/motor/move-relative")
def move_relative(data:dict):
    print("inside move relative in control")
    distance = float(data["distance"])
    steps = int(distance / 0.003048) #needs calibration
    direction_val = "up" if steps >= 0 else "down"

    Thread(target=move_steps, args=(steps, 20, direction_val)).start()
    return {"status": "moving"}

@app.post("/api/motor/jog-start")
def jog_start(data: dict):
    print("inside jog start in control")
    freq_hz = float(data["frequency"])
    direction_val = "up" if freq_hz >= 0 else "down"

    stop_event.clear()
    Thread(target=jog, args=(freq_hz, direction_val)).start()
    return {"status": "jogging"}

@app.post("/api/motor/jog-stop")
def jog_stop(data: dict):
    print("inside jog stop in control")
    stop_event.set()
    return {"status": "stopped"}

@app.post("/api/motor/stop")
def stop_all():
    print("inside stop all in control")
    stop_event.set()
    return {"status": "stopped"}