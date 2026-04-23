from fastapi import FastAPI, HTTPException
from threading import Event, Lock, Thread
from time import sleep

from gpiozero import DigitalOutputDevice


app = FastAPI()

STEP_PIN = 17
DIR_PIN = 27
ENA_PIN = 22
MM_PER_STEP = 0.003048

step = DigitalOutputDevice(STEP_PIN)
direction = DigitalOutputDevice(DIR_PIN)
enable = DigitalOutputDevice(ENA_PIN, active_high=False, initial_value=True)

stop_event = Event()
motion_lock = Lock()
active_motor = None
active_mode = "idle"
motor_positions = {}


def normalize_motor(data):
    motor = str(data.get("motor", "")).strip()
    if not motor:
        raise HTTPException(status_code=400, detail="motor is required")
    return motor


def reserve_motor(motor, mode):
    global active_motor, active_mode

    with motion_lock:
        if active_motor is not None and active_motor != motor:
            raise HTTPException(
                status_code=409,
                detail=f"Hardware is currently reserved for {active_motor}",
            )

        if active_motor == motor and active_mode != "idle":
            raise HTTPException(
                status_code=409,
                detail=f"{motor} already has active hardware motion",
            )

        stop_event.clear()
        active_motor = motor
        active_mode = mode


def release_motor(motor):
    global active_motor, active_mode

    with motion_lock:
        if active_motor == motor:
            active_motor = None
            active_mode = "idle"


def current_position(motor):
    return motor_positions.get(motor, 0.0)


def set_position(motor, position):
    motor_positions[motor] = position


def rate_to_frequency(rate_mm_per_second):
    return max(1.0, abs(rate_mm_per_second) / MM_PER_STEP)


def move_steps(motor, target_position, steps, freq_hz, direction_val):
    half_period = 1.0 / (2.0 * freq_hz)
    completed_steps = 0

    if direction_val == "up":
        direction.on()
    else:
        direction.off()

    enable.off()

    try:
        for _ in range(steps):
            if stop_event.is_set():
                break

            step.on()
            sleep(half_period)
            step.off()
            sleep(half_period)
            completed_steps += 1
    finally:
        enable.on()

        estimated_distance = completed_steps * MM_PER_STEP
        if direction_val == "down":
            estimated_distance *= -1

        if completed_steps == steps:
            set_position(motor, target_position)
        else:
            set_position(motor, current_position(motor) + estimated_distance)

        stop_event.clear()
        release_motor(motor)


def jog(motor, freq_hz, direction_val):
    half_period = 1.0 / (2.0 * freq_hz)
    delta = MM_PER_STEP if direction_val == "up" else -MM_PER_STEP

    if direction_val == "up":
        direction.on()
    else:
        direction.off()

    enable.off()

    try:
        while not stop_event.is_set():
            step.on()
            sleep(half_period)
            step.off()
            sleep(half_period)
            set_position(motor, current_position(motor) + delta)
    finally:
        enable.on()
        stop_event.clear()
        release_motor(motor)


@app.post("/api/motor/move-absolute")
def move_absolute(data: dict):
    motor = normalize_motor(data)
    target = float(data["target"])
    start = current_position(motor)
    distance = target - start
    direction_val = "up" if distance >= 0 else "down"
    steps = int(abs(distance) / MM_PER_STEP)

    reserve_motor(motor, "move_absolute")
    Thread(
        target=move_steps,
        args=(motor, target, steps, 20.0, direction_val),
        daemon=True,
    ).start()

    return {"status": "moving", "motor": motor, "target_mm": target}


@app.post("/api/motor/move-relative")
def move_relative(data: dict):
    motor = normalize_motor(data)
    distance = float(data["distance"])
    start = current_position(motor)
    target = start + distance
    direction_val = "up" if distance >= 0 else "down"
    steps = int(abs(distance) / MM_PER_STEP)

    reserve_motor(motor, "move_relative")
    Thread(
        target=move_steps,
        args=(motor, target, steps, 20.0, direction_val),
        daemon=True,
    ).start()

    return {"status": "moving", "motor": motor, "target_mm": target}


@app.post("/api/motor/jog-start")
def jog_start(data: dict):
    motor = normalize_motor(data)
    rate = abs(float(data.get("rate", data.get("frequency", 20.0))))
    direction_val = str(data.get("direction", "up")).lower()
    direction_val = "down" if direction_val in {"-1", "down", "reverse", "compression"} else "up"

    reserve_motor(motor, "jog")
    Thread(
        target=jog,
        args=(motor, rate_to_frequency(rate), direction_val),
        daemon=True,
    ).start()

    return {"status": "jogging", "motor": motor, "direction": direction_val}


@app.post("/api/motor/jog-stop")
def jog_stop(data: dict):
    motor = normalize_motor(data)

    with motion_lock:
        if active_motor not in {None, motor}:
            raise HTTPException(
                status_code=409,
                detail=f"Hardware is currently reserved for {active_motor}",
            )

    stop_event.set()
    return {"status": "stopped", "motor": motor}


@app.post("/api/system/abort")
def stop_all():
    step.off()
    direction.off()
    enable.on()
    stop_event.set()
    return {"status": "stopped", "motor": active_motor}
