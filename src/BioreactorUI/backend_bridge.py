#!/usr/bin/env python3
import copy
import os
import queue
import threading
import time

import requests


REQUEST_EXCEPTION = requests.RequestException

class HttpBackendBridge:
    def __init__(self, motors, base_url=None):
        print("init function hit")
        self.motors = list(motors)
        # Default to the Pi-friendly backend URL (Kestrel on 5000) but allow override via env.
        self.base_url = (
            base_url
            or os.environ.get("BIOREACTOR_BACKEND_URL")
            or "http://127.0.0.1:5000/api"
        )
        self._cached_status = {}
        # Used to reconcile UI state when event polling drops updates.
        self._last_status_snapshot = {}
        self.last_backend_ok_time = None
        self.backend_ok = False

    def _get(self, path, timeout):
        try:
            return requests.get(f"{self.base_url}{path}", timeout=timeout)
        except Exception as e:
            # print("exception: ", e)
            return None

    def _post(self, path, payload=None, timeout=1.0):
        try:
            return requests.post(f"{self.base_url}{path}", json=payload, timeout=timeout)
        except Exception as e:
            print("post exception:", e)
            print(f"url: {self.base_url} path: {path} ")
            return None

    def connect(self):
        resp = self._get("/status", timeout=2.0)
        ok = bool(resp and resp.status_code == 200)
        self.backend_ok = ok
        if ok:
            self.last_backend_ok_time = time.time()
        return ok

    def poll_events(self):
        events = []
        # Track which motors received which event types this cycle to avoid
        # duplicating updates when we synthesize from /status/all.
        seen_event_types = set()

        events_resp = self._get("/events", timeout=0.1)
        if events_resp and events_resp.status_code == 200:
            try:
                events = events_resp.json()
            except ValueError:
                events = []

        for ev in events:
            try:
                seen_event_types.add((ev.get("motor"), ev.get("type")))
            except Exception:
                pass

        status_resp = self._get("/status/all", timeout=0.1)
        if status_resp and status_resp.status_code == 200:
            try:
                data = status_resp.json()
                self.backend_ok = True
                self.last_backend_ok_time = time.time()
                self._cached_status = {item["motor"]: item for item in data}
                # Reconcile: synthesize motor_state/motor_position/motor_step updates
                # from authoritative status polling when event delivery is lossy.
                for motor, item in self._cached_status.items():
                    prev = self._last_status_snapshot.get(motor, {})
                    # Position
                    pos = item.get("position")
                    if pos is not None and prev.get("position") != pos and (motor, "motor_position") not in seen_event_types:
                        events.append({"type": "motor_position", "motor": motor, "position": pos})
                    # State
                    state = item.get("state")
                    if state and prev.get("state") != state and (motor, "motor_state") not in seen_event_types:
                        events.append({"type": "motor_state", "motor": motor, "state": state})
                    # Step
                    step = item.get("step")
                    if step and prev.get("step") != step and (motor, "motor_step") not in seen_event_types:
                        events.append({"type": "motor_step", "motor": motor, "step": step})

                    self._last_status_snapshot[motor] = {"position": pos, "state": state, "step": step}
            except ValueError:
                print("poll events exception: ", ValueError)
                pass
        else:
            # If we can't read status, consider the backend unhealthy until it recovers.
            self.backend_ok = False

        return events

    def has_active_run(self, motor):
        status = self._cached_status.get(motor, {})
        return status.get("isBusy", status.get("isRunning", False))

    def load_program(self, motor, steps):
        print("load program hit")
        payload = {"motor": motor, "steps": steps}
        try:
            resp = self._post("/program/load", payload=payload, timeout=2.0)
            return bool(resp and resp.status_code == 200)
        except Exception as e:
            print("load program exception: ", e)
            return None

    def start_program(self, motor):
        print("start program hit")
        resp = self._post("/program/start", payload={"motor": motor}, timeout=1.0)
        return bool(resp and resp.status_code == 200)

    def jog_start(self, motor, rate, direction):
        print("jog start hit")
        try:
            # Backend expects Direction as a string (C# model binding).
            payload = {"motor": motor, "rate": rate, "direction": str(direction)}
            self._post("/jog/start", payload=payload, timeout=1.0)
        except Exception as e:
            print("jog start exception: ", e)
            return None

    def jog_stop(self, motor):
        print("jog stop hit")
        try:
            self._post("/jog/stop", payload={"motor": motor}, timeout=1.0)
        except Exception as e:
            print("jog stop exception: ", e)
            return None

    def move_absolute(self, motor, target):
        print("move_absolute hit")
        try: 
            resp = self._post("/motor/move-absolute", payload={"motor": motor, "target": target}, timeout=1.0)
            return bool(resp and resp.status_code == 200)
        except Exception as e:
            print("move abs exception: ", e)
            return None

    def move_relative(self, motor, distance):
        print("move relative hit")
        try:
            resp = self._post("/motor/move-relative", payload={"motor": motor, "distance": distance}, timeout=1.0)
            return bool(resp and resp.status_code == 200)
        except Exception as e:
            print("move rel exception: ", e)
            return None

    def abort_all(self):
        self._post("/system/abort", timeout=1.0)

    # Placeholders for UI compatibility until the backend route set is finalized.
    def pause_all(self):
        self._post("/system/pause", timeout=1.0)

    def resume_all(self):
        self._post("/system/resume", timeout=1.0)

class UiMockBackend:
    """Temporary frontend-side stand-in for the real backend connection."""

    def __init__(self, motors):
        self.motors = list(motors)
        self.events = queue.Queue()
        self.lock = threading.Lock()
        self.positions = {motor: 0.0 for motor in self.motors}
        self.states = {motor: "idle" for motor in self.motors}
        self.steps = {motor: "Step: idle" for motor in self.motors}
        self.programs = {motor: [] for motor in self.motors}
        self.jog_contexts = {}
        self.run_contexts = {}
        self.paused = False

    def connect(self):
        self.emit("log", message="[BACKEND] Connected to frontend mock bridge.")
        for motor in self.motors:
            self.emit("motor_position", motor=motor, position=self.positions[motor])
            self.emit("motor_state", motor=motor, state=self.states[motor])
            self.emit("motor_step", motor=motor, step=self.steps[motor])

    def poll_events(self):
        drained = []
        while True:
            try:
                drained.append(self.events.get_nowait())
            except queue.Empty:
                return drained

    def emit(self, event_type, **payload):
        self.events.put({"type": event_type, **payload})

    def set_motor_state(self, motor, state):
        with self.lock:
            self.states[motor] = state
        self.emit("motor_state", motor=motor, state=state)

    def set_motor_position(self, motor, position):
        with self.lock:
            self.positions[motor] = position
        self.emit("motor_position", motor=motor, position=position)

    def set_motor_step(self, motor, step):
        with self.lock:
            self.steps[motor] = step
        self.emit("motor_step", motor=motor, step=step)

    def has_active_run(self, motor):
        with self.lock:
            return motor in self.run_contexts

    def jog_start(self, motor, rate_mm_per_sec, direction):
        with self.lock:
            if self.paused:
                self.emit("log", message="[WARN] Cannot jog while paused")
                return False
            if motor in self.run_contexts:
                self.emit("log", message=f"[WARN] {motor} is executing a program")
                return False
            if motor in self.jog_contexts:
                return False

            stop_event = threading.Event()
            self.jog_contexts[motor] = {"stop_event": stop_event}

        self.emit(
            "log",
            message=f"[JOG START] {motor} dir={'up' if direction > 0 else 'down'} rate={rate_mm_per_sec}",
        )
        self.set_motor_state(motor, "jogging")

        def worker():
            last = time.time()
            while not stop_event.wait(0.1):
                now = time.time()
                dt = now - last
                last = now
                with self.lock:
                    position = self.positions[motor] + rate_mm_per_sec * dt * direction
                self.set_motor_position(motor, position)

        threading.Thread(target=worker, daemon=True).start()
        return True

    def jog_stop(self, motor):
        with self.lock:
            context = self.jog_contexts.pop(motor, None)
        if not context:
            return False
        context["stop_event"].set()
        self.set_motor_state(motor, "idle")
        self.emit("log", message=f"[JOG STOP] {motor}")
        return True

    def move_relative(self, motor, delta_mm):
        with self.lock:
            if self.paused:
                self.emit("log", message="[WARN] Cannot move while paused")
                return False
            if motor in self.run_contexts:
                self.emit("log", message=f"[WARN] {motor} is executing a program")
                return False
            if motor in self.jog_contexts:
                self.emit("log", message=f"[WARN] {motor} is already jogging")
                return False

            current = self.positions[motor]
            target = current + delta_mm

        self.set_motor_state(motor, "moving")
        self.emit("log", message=f"[MOVE START] {motor} relative {delta_mm}")
        self.set_motor_position(motor, target)
        self.set_motor_state(motor, "idle")
        self.emit("log", message=f"[MOVE END] {motor} pos={target:.3f}")
        return True

    def move_absolute(self, motor, target_mm):
        with self.lock:
            current = self.positions[motor]
        return self.move_relative(motor, target_mm - current)

    def load_program(self, motor, steps):
        with self.lock:
            if motor in self.run_contexts:
                self.emit("log", message=f"[WARN] {motor} is already executing a program")
                return False
            self.programs[motor] = copy.deepcopy(steps)
        self.emit("log", message=f"[PROGRAM LOAD] {motor} loaded {len(steps)} step(s)")
        return True

    def start_program(self, motor):
        with self.lock:
            if self.paused:
                self.emit("log", message="[WARN] Cannot start while paused")
                return False
            if motor in self.run_contexts:
                self.emit("log", message=f"[WARN] {motor} is already executing a program")
                return False

            sequence = copy.deepcopy(self.programs[motor])
            if not sequence:
                self.emit("log", message=f"[WARN] {motor} has no program to submit")
                return False

            context = {
                "pause_event": threading.Event(),
                "stop_event": threading.Event(),
                "sequence": sequence,
            }
            self.run_contexts[motor] = context

        self.set_motor_state(motor, "queued")
        self.emit("log", message=f"[PROGRAM SUBMIT] {motor}")

        def worker():
            self.emit("log", message=f"[RUN START] {motor} loaded {len(sequence)} action steps")
            try:
                for index, step in enumerate(sequence, start=1):
                    if context["stop_event"].is_set():
                        break

                    while context["pause_event"].is_set():
                        if context["stop_event"].wait(0.1):
                            break
                    if context["stop_event"].is_set():
                        break

                    self.set_motor_state(motor, "running")
                    self.set_motor_step(motor, f"Step: {index}/{len(sequence)}")
                    self.emit("log", message=f"[RUN] {motor} step {index}: {step['label']}")

                    started = time.time()
                    while time.time() - started < step["estimated_seconds"]:
                        if context["stop_event"].is_set():
                            break
                        while context["pause_event"].is_set():
                            self.set_motor_state(motor, "paused")
                            if context["stop_event"].wait(0.1):
                                break
                        if context["stop_event"].is_set():
                            break
                        time.sleep(0.05)

                    if context["stop_event"].is_set():
                        break

                    self.set_motor_position(motor, step["target_position_mm"])
                    self.emit("log", message=f"[STEP COMPLETE] {motor} step {index}")

                if context["stop_event"].is_set():
                    self.set_motor_step(motor, "Step: discarded")
                    self.emit("log", message=f"[RUN DISCARDED] {motor} loaded sequence cleared")
                else:
                    self.set_motor_step(motor, "Step: complete")
                    self.emit("log", message=f"[RUN COMPLETE] {motor}")
            finally:
                with self.lock:
                    self.run_contexts.pop(motor, None)
                self.set_motor_state(motor, "idle")
                if self.steps[motor] in ("Step: complete", "Step: discarded"):
                    time.sleep(1.5)
                    self.set_motor_step(motor, "Step: idle")

        threading.Thread(target=worker, daemon=True).start()
        return True

    def pause_all(self):
        with self.lock:
            if self.paused:
                return False
            self.paused = True
            jogged = list(self.jog_contexts.keys())
            active = list(self.run_contexts.items())

        for motor in jogged:
            self.jog_stop(motor)
            self.set_motor_state(motor, "paused")

        for motor, context in active:
            context["pause_event"].set()
            self.set_motor_state(motor, "paused")

        self.emit("log", message="[EMERGENCY STOP] Motion paused. Choose Continue or Stop Experiment.")
        return True

    def resume_all(self):
        with self.lock:
            if not self.paused:
                return False
            self.paused = False
            active = list(self.run_contexts.items())

        for motor, context in active:
            context["pause_event"].clear()
            self.set_motor_state(motor, "running")

        for motor in self.motors:
            with self.lock:
                is_active = motor in self.run_contexts
                current_state = self.states[motor]
            if not is_active and current_state == "paused":
                self.set_motor_state(motor, "idle")

        self.emit("log", message="[EXPERIMENT CONTINUE] Pause cleared.")
        return True

    def abort_all(self):
        with self.lock:
            self.paused = False
            jogged = list(self.jog_contexts.keys())
            active = list(self.run_contexts.items())

        for motor in jogged:
            self.jog_stop(motor)

        for motor, context in active:
            context["pause_event"].clear()
            context["stop_event"].set()
            self.set_motor_state(motor, "stopping")
            self.set_motor_step(motor, "Step: stopping")

        if jogged or active:
            self.emit("log", message="[EXPERIMENT STOPPED] Active motion discarded.")
        else:
            self.emit("log", message="[EXPERIMENT STOPPED] No active motion to discard.")
        return True
