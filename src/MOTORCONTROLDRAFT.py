from __future__ import annotations

import os
from dataclasses import dataclass
from threading import Event, Lock, Thread
from time import sleep

from fastapi import FastAPI, HTTPException


app = FastAPI()

MM_PER_STEP = float(os.environ.get("MM_PER_STEP", "0.003048"))


class _NullOutputDevice:
    """Fallback used on non-Pi dev machines (no GPIO)."""

    def __init__(self, _pin: int, active_high: bool = True, initial_value: bool = False):
        self.active_high = active_high
        self.value = bool(initial_value)

    def on(self):
        self.value = True

    def off(self):
        self.value = False


def _get_output_device():
    try:
        from gpiozero import DigitalOutputDevice  # type: ignore

        return DigitalOutputDevice
    except Exception:
        return _NullOutputDevice


DigitalOutputDevice = _get_output_device()


@dataclass(frozen=True)
class MotorPins:
    step: int
    direction: int
    enable: int


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid int for {name}={raw!r}") from exc


def _load_pins() -> dict[str, MotorPins]:
    # Simple defaults; override on the Pi via env vars.
    return {
        "Motor 1": MotorPins(
            step=_env_int("MOTOR1_STEP_PIN", 17),
            direction=_env_int("MOTOR1_DIR_PIN", 27),
            enable=_env_int("MOTOR1_ENA_PIN", 22),
        ),
        "Motor 2": MotorPins(
            step=_env_int("MOTOR2_STEP_PIN", 5),
            direction=_env_int("MOTOR2_DIR_PIN", 6),
            enable=_env_int("MOTOR2_ENA_PIN", 13),
        ),
        "Motor 3": MotorPins(
            step=_env_int("MOTOR3_STEP_PIN", 19),
            direction=_env_int("MOTOR3_DIR_PIN", 26),
            enable=_env_int("MOTOR3_ENA_PIN", 21),
        ),
    }


class MotorController:
    def __init__(self, name: str, pins: MotorPins, mm_per_step: float):
        self.name = name
        self.mm_per_step = mm_per_step
        self.step = DigitalOutputDevice(pins.step)
        self.direction = DigitalOutputDevice(pins.direction)
        # Most stepper drivers use active-low enable.
        self.enable = DigitalOutputDevice(pins.enable, active_high=False, initial_value=True)

        self.stop_event = Event()
        self.lock = Lock()
        self.active_mode = "idle"
        self.position_mm = 0.0

    def current_position(self) -> float:
        return self.position_mm

    def set_position(self, pos: float) -> None:
        self.position_mm = float(pos)

    def rate_to_frequency(self, rate_mm_per_second: float) -> float:
        return max(1.0, abs(rate_mm_per_second) / self.mm_per_step)

    def reserve(self, mode: str) -> None:
        with self.lock:
            if self.active_mode != "idle":
                raise HTTPException(
                    status_code=409,
                    detail=f"{self.name} already has active hardware motion",
                )
            self.stop_event.clear()
            self.active_mode = mode

    def release(self) -> None:
        with self.lock:
            self.active_mode = "idle"

    def stop(self) -> None:
        self.stop_event.set()

    def _set_direction(self, direction_val: str) -> None:
        if direction_val == "up":
            self.direction.on()
        else:
            self.direction.off()

    def _pulse_loop(self, half_period: float, should_update_pos: bool, delta: float) -> int:
        completed = 0
        while not self.stop_event.is_set():
            self.step.on()
            sleep(half_period)
            self.step.off()
            sleep(half_period)
            completed += 1
            if should_update_pos:
                self.position_mm += delta
        return completed

    def move_steps(self, target_position: float, steps: int, freq_hz: float, direction_val: str) -> None:
        half_period = 1.0 / (2.0 * freq_hz)
        completed_steps = 0

        self._set_direction(direction_val)
        self.enable.off()

        try:
            for _ in range(steps):
                if self.stop_event.is_set():
                    break
                self.step.on()
                sleep(half_period)
                self.step.off()
                sleep(half_period)
                completed_steps += 1
        finally:
            self.enable.on()

            estimated_distance = completed_steps * self.mm_per_step
            if direction_val == "down":
                estimated_distance *= -1

            if completed_steps == steps:
                self.set_position(target_position)
            else:
                self.set_position(self.current_position() + estimated_distance)

            self.stop_event.clear()
            self.release()

    def jog(self, freq_hz: float, direction_val: str) -> None:
        half_period = 1.0 / (2.0 * freq_hz)
        delta = self.mm_per_step if direction_val == "up" else -self.mm_per_step

        self._set_direction(direction_val)
        self.enable.off()

        try:
            # Update position on every pulse so backend status shows movement.
            while not self.stop_event.is_set():
                self.step.on()
                sleep(half_period)
                self.step.off()
                sleep(half_period)
                self.set_position(self.current_position() + delta)
        finally:
            self.enable.on()
            self.stop_event.clear()
            self.release()


MOTOR_PINS = _load_pins()
MOTORS: dict[str, MotorController] = {
    name: MotorController(name, pins, MM_PER_STEP) for name, pins in MOTOR_PINS.items()
}


def normalize_motor(data):
    motor = str(data.get("motor", "")).strip()
    if not motor:
        raise HTTPException(status_code=400, detail="motor is required")
    if motor not in MOTORS:
        raise HTTPException(status_code=400, detail=f"Unknown motor: {motor}")
    return motor


def rate_to_frequency(rate_mm_per_second):
    return max(1.0, abs(rate_mm_per_second) / MM_PER_STEP)


def _controller(motor: str) -> MotorController:
    return MOTORS[motor]


@app.post("/api/motor/move-absolute")
def move_absolute(data: dict):
    motor = normalize_motor(data)
    ctrl = _controller(motor)
    target = float(data["target"])
    start = ctrl.current_position()
    distance = target - start
    direction_val = "up" if distance >= 0 else "down"
    steps = int(abs(distance) / MM_PER_STEP)

    ctrl.reserve("move_absolute")
    Thread(
        target=ctrl.move_steps,
        args=(target, steps, 20.0, direction_val),
        daemon=True,
    ).start()

    return {"status": "moving", "motor": motor, "target_mm": target}


@app.post("/api/motor/move-relative")
def move_relative(data: dict):
    motor = normalize_motor(data)
    ctrl = _controller(motor)
    distance = float(data["distance"])
    start = ctrl.current_position()
    target = start + distance
    direction_val = "up" if distance >= 0 else "down"
    steps = int(abs(distance) / MM_PER_STEP)

    ctrl.reserve("move_relative")
    Thread(
        target=ctrl.move_steps,
        args=(target, steps, 20.0, direction_val),
        daemon=True,
    ).start()

    return {"status": "moving", "motor": motor, "target_mm": target}


@app.post("/api/motor/jog-start")
def jog_start(data: dict):
    motor = normalize_motor(data)
    ctrl = _controller(motor)
    rate = abs(float(data.get("rate", data.get("frequency", 20.0))))
    direction_val = str(data.get("direction", "up")).lower()
    direction_val = "down" if direction_val in {"-1", "down", "reverse", "compression"} else "up"

    ctrl.reserve("jog")
    Thread(
        target=ctrl.jog,
        args=(ctrl.rate_to_frequency(rate), direction_val),
        daemon=True,
    ).start()

    return {"status": "jogging", "motor": motor, "direction": direction_val}


@app.post("/api/motor/jog-stop")
def jog_stop(data: dict):
    motor = normalize_motor(data)
    ctrl = _controller(motor)
    ctrl.stop()
    return {"status": "stopped", "motor": motor}


@app.post("/api/system/abort")
def stop_all():
    for ctrl in MOTORS.values():
        try:
            ctrl.step.off()
            ctrl.direction.off()
            ctrl.enable.on()
        except Exception:
            pass
        ctrl.stop()
    return {"status": "stopped"}
