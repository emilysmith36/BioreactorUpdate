#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, scrolledtext
import copy
import time

from backend_bridge import UiMockBackend
from backend_bridge import HttpBackendBridge

class ActionDialog(simpledialog.Dialog):
    def body(self, master):
        master.columnconfigure(1, weight=1)

        self.direction = tk.StringVar(value="tension")
        self.rate = tk.DoubleVar(value=1.0)
        self.freq = tk.DoubleVar(value=1.0)
        self.motion = tk.StringVar(value="strain")
        self.length = tk.DoubleVar(value=10.0)
        self.strain = tk.DoubleVar(value=5.0)
        self.displacement = tk.DoubleVar(value=0.5)
        self.timing = tk.StringVar(value="duration")
        self.duration = tk.DoubleVar(value=1.0)
        self.unit = tk.StringVar(value="Minutes")
        self.cycles = tk.IntVar(value=10)
        self.strain_label = tk.StringVar()
        self.cycles_label = tk.StringVar()

        ttk.Label(master, text="Direction").grid(row=0, column=0, sticky="e", padx=(0, 8), pady=3)
        ttk.Combobox(master, textvariable=self.direction, values=("tension", "compression"), state="readonly").grid(row=0, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Rate").grid(row=1, column=0, sticky="e", padx=(0, 8), pady=3)
        ttk.Entry(master, textvariable=self.rate).grid(row=1, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Frequency (Hz)").grid(row=2, column=0, sticky="e", padx=(0, 8), pady=3)
        ttk.Entry(master, textvariable=self.freq).grid(row=2, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Motion Type").grid(row=3, column=0, sticky="e", padx=(0, 8), pady=3)
        motion_frame = ttk.Frame(master)
        motion_frame.grid(row=3, column=1, sticky="w", pady=3)
        ttk.Radiobutton(motion_frame, text="Strain (%)", variable=self.motion, value="strain").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(motion_frame, text="Displacement", variable=self.motion, value="displacement").pack(side="left")

        ttk.Label(master, text="Gauge Length (mm)").grid(row=4, column=0, sticky="e", padx=(0, 8), pady=3)
        self.length_entry = ttk.Entry(master, textvariable=self.length)
        self.length_entry.grid(row=4, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Strain (%)").grid(row=5, column=0, sticky="e", padx=(0, 8), pady=3)
        self.strain_entry = ttk.Entry(master, textvariable=self.strain)
        self.strain_entry.grid(row=5, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Displacement (mm)").grid(row=6, column=0, sticky="e", padx=(0, 8), pady=3)
        self.disp_entry = ttk.Entry(master, textvariable=self.displacement)
        self.disp_entry.grid(row=6, column=1, sticky="ew", pady=3)

        ttk.Label(master, textvariable=self.strain_label).grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 6))

        ttk.Label(master, text="Timing").grid(row=8, column=0, sticky="e", padx=(0, 8), pady=3)
        timing_frame = ttk.Frame(master)
        timing_frame.grid(row=8, column=1, sticky="w", pady=3)
        ttk.Radiobutton(timing_frame, text="Duration", variable=self.timing, value="duration").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(timing_frame, text="Cycles", variable=self.timing, value="cycles").pack(side="left")

        ttk.Label(master, text="Duration").grid(row=9, column=0, sticky="e", padx=(0, 8), pady=3)
        self.duration_entry = ttk.Entry(master, textvariable=self.duration)
        self.duration_entry.grid(row=9, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Unit").grid(row=10, column=0, sticky="e", padx=(0, 8), pady=3)
        self.unit_box = ttk.Combobox(master, textvariable=self.unit, values=("Minutes", "Hours"), state="readonly")
        self.unit_box.grid(row=10, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Cycles").grid(row=11, column=0, sticky="e", padx=(0, 8), pady=3)
        self.cycles_entry = ttk.Entry(master, textvariable=self.cycles)
        self.cycles_entry.grid(row=11, column=1, sticky="ew", pady=3)

        ttk.Label(master, textvariable=self.cycles_label).grid(row=12, column=0, columnspan=2, sticky="w", pady=(0, 4))

        for var in (self.motion, self.timing, self.length, self.strain, self.freq, self.cycles):
            var.trace_add("write", self.update_text)

        self.update_text()
        return None

    def update_text(self, *_args):
        use_strain = self.motion.get() == "strain"
        use_cycles = self.timing.get() == "cycles"

        self.length_entry.configure(state="normal" if use_strain else "disabled")
        self.strain_entry.configure(state="normal" if use_strain else "disabled")
        self.disp_entry.configure(state="disabled" if use_strain else "normal")
        self.duration_entry.configure(state="disabled" if use_cycles else "normal")
        self.unit_box.configure(state="disabled" if use_cycles else "readonly")
        self.cycles_entry.configure(state="normal" if use_cycles else "disabled")

        try:
            d = float(self.length.get()) * float(self.strain.get()) / 100.0
            self.strain_label.set(f"Derived displacement from strain: {d:.3f} mm")
        except Exception:
            self.strain_label.set("Derived displacement from strain: invalid input")

        if not use_cycles:
            self.cycles_label.set("Estimated completion time is shown for cycle-based steps.")
            return

        try:
            est = float(self.cycles.get()) / float(self.freq.get()) / 60.0
            self.cycles_label.set(f"Estimated completion time: {est:.2f} minutes")
        except Exception:
            self.cycles_label.set("Estimated completion time: invalid input")

    def validate(self):
        try:
            rate = float(self.rate.get())
            freq = float(self.freq.get())
            if rate <= 0 or freq <= 0:
                raise ValueError
            if self.motion.get() == "strain":
                length = float(self.length.get())
                strain = float(self.strain.get())
                if length <= 0 or strain < 0:
                    raise ValueError
            else:
                displacement = float(self.displacement.get())
                if displacement < 0:
                    raise ValueError
            if self.timing.get() == "duration":
                duration = float(self.duration.get())
                if duration <= 0:
                    raise ValueError
            else:
                cycles = int(self.cycles.get())
                if cycles <= 0:
                    raise ValueError
        except Exception:
            messagebox.showerror(
                "Invalid Action Step",
                "Enter positive values for rate, frequency, timing, and gauge length. "
                "Use non-negative values for strain and displacement.",
                parent=self,
            )
            return False
        return True

    def apply(self):
        self.result = {
            "type": "action",
            "direction": self.direction.get(),
            "rate": float(self.rate.get()),
            "freq": float(self.freq.get()),
            "motion_mode": self.motion.get(),
            "gauge_length": float(self.length.get()) if self.motion.get() == "strain" else 0.0,
            "strain_pct": float(self.strain.get()) if self.motion.get() == "strain" else 0.0,
            "displacement": float(self.displacement.get()) if self.motion.get() == "displacement" else 0.0,
            "timing_mode": self.timing.get(),
            "duration": float(self.duration.get()) if self.timing.get() == "duration" else 0.0,
            "unit": self.unit.get() if self.timing.get() == "duration" else "",
            "cycles": int(self.cycles.get()) if self.timing.get() == "cycles" else 0,
        }

class LoopDialog(simpledialog.Dialog):
    def body(self, master):
        ttk.Label(master, text="Repeat count").grid(row=0, column=0, sticky="e")
        self.count = tk.IntVar(value=2)
        ttk.Spinbox(master, from_=2, to=1000, textvariable=self.count, width=8).grid(row=0, column=1)
        ttk.Label(master, text="(repeats everything above it)").grid(row=1, column=0, columnspan=2, pady=(6, 0))
        return None

    def apply(self):
        self.result = {"type": "loop", "count": int(self.count.get())}

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bioreactor Program Builder")
        self.geometry("1100x700")
        self.minsize(900, 600)

        # Used by the History page; must exist before pages are constructed.
        self.connection_text = tk.StringVar(value="Backend: connecting…")

        self.motors = ["Motor 1", "Motor 2", "Motor 3"]
        self.pos = {m: 0.0 for m in self.motors}
        self.state = {m: "idle" for m in self.motors}
        self.current_step = {m: "Step: idle" for m in self.motors}
        self.programs = {m: [] for m in self.motors}
        self.status_indicators = {m: [] for m in self.motors}
        self.paused = False
        #self.bridge = UiMockBackend(self.motors)
        self.bridge = HttpBackendBridge(self.motors)

        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        side = ttk.Frame(root, width=220)
        side.pack(side="left", fill="y", padx=6, pady=6)
        side.pack_propagate(False)
        ttk.Button(side, text="Bioreactor Settings", command=lambda: self.show("control")).pack(fill="x", pady=6)
        ttk.Button(side, text="Project Settings", command=lambda: self.show("project")).pack(fill="x", pady=6)
        ttk.Button(side, text="History", command=lambda: self.show("history")).pack(fill="x", pady=6)

        self.area = ttk.Frame(root)
        self.area.pack(side="right", fill="both", expand=True, padx=8, pady=8)

        self.pages = {
            "control": self.make_control_page(self.area),
            "project": self.make_project_page(self.area),
            "history": self.make_history_page(self.area),
        }

        self.show("control")
        self.bridge.connect()
        self.after(50, self.process_bridge_events)
        self.after(250, self.refresh_connection_status)

    def show(self, name):
        for p in self.pages.values():
            p.grid_forget()
        self.pages[name].grid(row=0, column=0, sticky="nsew")

    def process_bridge_events(self):
        for event in self.bridge.poll_events():
            self.apply_bridge_event(event)
        self.refresh_experiment_status_from_state()
        self.after(50, self.process_bridge_events)

    def refresh_connection_status(self):
        ok = bool(getattr(self.bridge, "backend_ok", False))
        last_ok = getattr(self.bridge, "last_backend_ok_time", None)
        if not ok:
            if last_ok is None:
                self.connection_text.set("Backend: disconnected (no successful update yet)")
            else:
                age = max(0.0, time.time() - float(last_ok))
                self.connection_text.set(f"Backend: disconnected (last ok {age:.1f}s ago)")
        else:
            if last_ok is None:
                self.connection_text.set("Backend: connected")
            else:
                age = max(0.0, time.time() - float(last_ok))
                self.connection_text.set(f"Backend: connected (updated {age:.1f}s ago)")
        self.after(250, self.refresh_connection_status)

    def apply_bridge_event(self, event):
        event_type = event["type"]
        
        if event_type == "log":
            self.add_log(event["message"])
            
        elif event_type == "motor_state":
            # This updates the text in the "Motor Positions" section
            self.set_motor_state(event["motor"], event["state"])
            # This adds a note to the history log
            self.add_log(f"[STATUS] {event['motor']} is now {event['state']}")
            
        elif event_type == "motor_position":
            self.pos[event["motor"]] = event["position"]
            self.update_motor_label(event["motor"])
            
        elif event_type == "motor_step":
            self.set_motor_step(event["motor"], event["step"])

    def refresh_experiment_status_from_state(self):
        if self.paused:
            self.set_experiment_status(
                "Experiment Status: Emergency-paused",
                pause_state="disabled",
                continue_state="normal",
                stop_state="normal",
            )
            return

        if any(self.bridge.has_active_run(motor) for motor in self.motors):
            self.set_experiment_status(
                "Experiment Status: Running",
                pause_state="normal",
                continue_state="disabled",
                stop_state="disabled",
            )
            return

        self.set_experiment_status(
            "Experiment Status: Ready",
            pause_state="normal",
            continue_state="disabled",
            stop_state="disabled",
        )

    def add_log(self, text):
        line = f"{time.strftime('%H:%M:%S')}  {text}"
        for box in (self.control_log, self.history_log):
            try:
                box.configure(state="normal")
                box.insert("end", line + "\n")
                box.see("end")
                box.configure(state="disabled")
            except Exception:
                pass

    def update_motor_label(self, motor):
        self.pos_labels[motor].config(text=f"{motor}: {self.pos[motor]:.3f} ({self.state[motor]})")
        self.step_labels[motor].config(text=self.current_step[motor])
        for widget in self.status_indicators.get(motor, []):
            widget.config(text=f"{motor}: {self.state[motor]} | {self.current_step[motor][6:]}")

    def sync_emergency_controls(self):
        pause_state = str(self.pause_btn["state"])
        continue_state = str(self.continue_btn["state"])
        stop_state = str(self.stop_btn["state"])

        for widget in getattr(self, "pause_buttons", []):
            widget.configure(state=pause_state)
        for widget in getattr(self, "continue_buttons", []):
            widget.configure(state=continue_state)
        for widget in getattr(self, "stop_buttons", []):
            widget.configure(state=stop_state)

    def set_experiment_status(self, text, pause_state=None, continue_state=None, stop_state=None):
        self.pause_text.set(text)
        if pause_state is not None:
            self.pause_btn.configure(state=pause_state)
        if continue_state is not None:
            self.continue_btn.configure(state=continue_state)
        if stop_state is not None:
            self.stop_btn.configure(state=stop_state)
        self.sync_emergency_controls()

    def selected_program_motors(self):
        return [motor for motor, var in self.proj_motor_vars.items() if var.get()]

    def current_preview_motor(self):
        selected = self.selected_program_motors()
        return selected[0] if selected else self.motors[0]

    def programs_match(self, motors):
        if not motors:
            return True
        baseline = self.programs[motors[0]]
        return all(self.programs[motor] == baseline for motor in motors[1:])

    def update_program_summary(self):
        motors = self.selected_program_motors()
        if not motors:
            self.program_text.set("Select at least one motor to edit or run.")
            return

        preview_motor = motors[0]
        steps = self.programs[preview_motor]
        actions = sum(1 for step in steps if step["type"] == "action")
        loops = sum(1 for step in steps if step["type"] == "loop")

        if len(motors) == 1:
            self.program_text.set(f"{preview_motor}: {len(steps)} steps, {actions} actions, {loops} loops")
            return

        if self.programs_match(motors):
            names = ", ".join(motors)
            self.program_text.set(f"{names}: shared program with {len(steps)} steps")
        else:
            self.program_text.set("Selected motors have different programs. Preview shows the first selected motor.")

    def set_motor_state(self, motor, state):
        self.state[motor] = state
        self.update_motor_label(motor)

    def set_motor_step(self, motor, text):
        self.current_step[motor] = text
        self.update_motor_label(motor)

    def has_active_run(self, motor):
        return self.bridge.has_active_run(motor)

    def active_run_motors(self):
        return [motor for motor in self.motors if self.bridge.has_active_run(motor)]

    def can_manual_control(self, motor):
        if self.paused:
            self.add_log("[WARN] Cannot move while paused")
            return False
        if self.bridge.has_active_run(motor):
            self.add_log(f"[WARN] {motor} is busy with another motion")
            return False
        if self.state[motor] == "jogging":
            self.add_log(f"[WARN] {motor} is already jogging")
            return False
        return True

    def action_displacement_mm(self, step):
        if step["motion_mode"] == "strain":
            return step["gauge_length"] * (step["strain_pct"] / 100.0)
        return step["displacement"]

    def action_duration_seconds(self, step):
        if step["timing_mode"] == "cycles":
            return step["cycles"] / step["freq"]
        unit_scale = 3600.0 if step["unit"] == "Hours" else 60.0
        return step["duration"] * unit_scale

    def expand_program(self, steps):
        expanded = []
        executed = []

        for step in steps:
            if step["type"] == "action":
                clone = copy.deepcopy(step)
                expanded.append(clone)
                executed.append(clone)
                continue

            block = [copy.deepcopy(s) for s in executed]
            for _ in range(step["count"] - 1):
                for substep in copy.deepcopy(block):
                    expanded.append(substep)
                    executed.append(substep)

        return expanded

    def serialize_backend_step(self, step, i):
        displacement_mm = self.action_displacement_mm(step)
        estimated_seconds = self.action_duration_seconds(step)
        return {
            "type": "action",
            "direction": step["direction"],
            "rate": step["rate"],
            "frequency_hz": step["freq"],
            "displacement_mm": displacement_mm,
            "timing_mode": step["timing_mode"],
            "duration_seconds": estimated_seconds,
            "estimated_seconds": estimated_seconds,
            "cycles": step["cycles"],
            "target_position_mm": displacement_mm if step["direction"] == "tension" else -displacement_mm,
            "label": self.step_text(step, i)[8:],
        }

    def build_backend_sequence(self, motor):
        expanded = self.expand_program(self.programs[motor])
        return [self.serialize_backend_step(step, i) for i, step in enumerate(expanded, start=1)]

    def make_control_page(self, parent):
        frame = ttk.Frame(parent)
        frame.columnconfigure(1, weight=1)

        left = ttk.Frame(frame)
        left.grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=4)

        ttk.Label(left, text="Select Motor").pack(anchor="w")
        self.sel_motor = tk.StringVar(value=self.motors[0])
        ttk.Combobox(left, textvariable=self.sel_motor, values=self.motors, state="readonly", width=18).pack(fill="x", pady=6)

        ttk.Label(left, text="Jog rate (mm/sec)").pack(anchor="w")
        self.jog_rate = tk.DoubleVar(value=1.0)
        ttk.Spinbox(left, from_=0.01, to=1000000, increment=0.1, textvariable=self.jog_rate, width=12).pack(pady=6)

        jog = ttk.Frame(left)
        jog.pack(fill="x", pady=6)
        up = ttk.Button(jog, text="Up", width=8)
        down = ttk.Button(jog, text="Down", width=8)
        up.pack(side="left", padx=6)
        down.pack(side="left", padx=6)
        up.bind("<ButtonPress-1>", lambda _e: self.start_jog(1))
        up.bind("<ButtonRelease-1>", lambda _e: self.stop_jog())
        down.bind("<ButtonPress-1>", lambda _e: self.start_jog(-1))
        down.bind("<ButtonRelease-1>", lambda _e: self.stop_jog())

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(left, text="Relative move (mm)").pack(anchor="w")
        self.rel = tk.DoubleVar(value=10.0)
        ttk.Spinbox(left, from_=-1000000000, to=1000000000, increment=0.1, textvariable=self.rel, width=14).pack(pady=4)
        ttk.Button(left, text="Move Relative", command=self.move_relative).pack(fill="x", pady=4)

        ttk.Label(left, text="Absolute move (mm)").pack(anchor="w", pady=(8, 0))
        self.abs = tk.DoubleVar(value=0.0)
        ttk.Spinbox(left, from_=-1000000000000, to=1000000000000, increment=0.1, textvariable=self.abs, width=14).pack(pady=4)
        ttk.Button(left, text="Move Absolute", command=self.move_absolute).pack(fill="x", pady=4)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)

        self.pause_text = tk.StringVar(value="Experiment Status: Ready")
        self.pause_buttons = []
        self.continue_buttons = []
        self.stop_buttons = []
        ttk.Label(left, textvariable=self.pause_text, foreground="#8B0000").pack(anchor="w", pady=(0, 4))
        self.pause_btn = ttk.Button(left, text="Emergency Stop", command=self.emergency_stop)
        self.pause_btn.pack(fill="x", pady=4)
        self.continue_btn = ttk.Button(left, text="Continue", command=self.continue_experiment, state="disabled")
        self.continue_btn.pack(fill="x", pady=4)
        self.stop_btn = ttk.Button(left, text="Stop Experiment", command=self.stop_experiment, state="disabled")
        self.stop_btn.pack(fill="x", pady=4)
        self.pause_buttons.append(self.pause_btn)
        self.continue_buttons.append(self.continue_btn)
        self.stop_buttons.append(self.stop_btn)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="Motor Positions", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        pos_frame = ttk.Frame(right)
        pos_frame.pack(fill="x", pady=(6, 8))
        self.pos_labels = {}
        self.step_labels = {}
        for motor in self.motors:
            lbl = ttk.Label(pos_frame, text=f"{motor}: 0.000 (idle)")
            lbl.pack(anchor="w", pady=2)
            self.pos_labels[motor] = lbl
            step_lbl = ttk.Label(pos_frame, text=self.current_step[motor], foreground="#555555")
            step_lbl.pack(anchor="w", padx=(20, 0), pady=(0, 2))
            self.step_labels[motor] = step_lbl

        ttk.Label(right, text="Log", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(8, 0))
        self.control_log = scrolledtext.ScrolledText(right, height=18, state="disabled", wrap="word")
        self.control_log.pack(fill="both", expand=True, pady=(4, 0))

        return frame

    def build_motor_status_strip(self, parent):
        status_frame = ttk.LabelFrame(parent, text="Motor Status")
        status_frame.pack(fill="x", pady=(0, 8))

        for motor in self.motors:
            label = ttk.Label(status_frame, text=f"{motor}: {self.state[motor]} | {self.current_step[motor][6:]}")
            label.pack(anchor="w", padx=8, pady=2)
            self.status_indicators[motor].append(label)

        return status_frame

    def make_project_page(self, parent):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text="Project Settings - Program Builder", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))
        self.build_motor_status_strip(frame)

        top = ttk.Frame(frame)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Program motors:").pack(side="left")
        self.proj_motor_vars = {}
        check_frame = ttk.Frame(top)
        check_frame.pack(side="left", padx=8)
        for motor in self.motors:
            var = tk.BooleanVar(value=(motor == self.motors[0]))
            self.proj_motor_vars[motor] = var
            ttk.Checkbutton(check_frame, text=motor, variable=var, command=self.refresh_steps).pack(side="left", padx=(0, 8))
        self.program_text = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.program_text).pack(side="left", padx=(10, 0))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)
        self.step_box = tk.Listbox(list_frame, height=18)
        self.step_box.pack(side="left", fill="both", expand=True)
        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.step_box.yview)
        scroll_y.pack(side="right", fill="y")
        scroll_x = ttk.Scrollbar(frame, orient="horizontal", command=self.step_box.xview)
        scroll_x.pack(fill="x", pady=(0, 6))
        self.step_box.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Add Action", command=self.add_action).pack(side="left", padx=4)
        ttk.Button(buttons, text="Add Loop", command=self.add_loop).pack(side="left", padx=4)
        ttk.Button(buttons, text="Move Up", command=lambda: self.move_step(-1)).pack(side="left", padx=4)
        ttk.Button(buttons, text="Move Down", command=lambda: self.move_step(1)).pack(side="left", padx=4)
        ttk.Button(buttons, text="Remove Selected", command=self.remove_step).pack(side="left", padx=4)
        ttk.Button(buttons, text="Submit Program", command=self.submit_program).pack(side="right", padx=4)

        emergency = ttk.LabelFrame(frame, text="Emergency Controls")
        emergency.pack(fill="x", pady=(6, 0))
        ttk.Label(emergency, textvariable=self.pause_text, foreground="#8B0000").pack(anchor="w", padx=8, pady=(8, 4))
        controls = ttk.Frame(emergency)
        controls.pack(fill="x", padx=8, pady=(0, 8))
        pause_btn = ttk.Button(controls, text="Emergency Stop", command=self.emergency_stop)
        pause_btn.pack(side="left", padx=(0, 6))
        continue_btn = ttk.Button(controls, text="Continue", command=self.continue_experiment, state="disabled")
        continue_btn.pack(side="left", padx=6)
        stop_btn = ttk.Button(controls, text="Stop Experiment", command=self.stop_experiment, state="disabled")
        stop_btn.pack(side="left", padx=6)
        self.pause_buttons.append(pause_btn)
        self.continue_buttons.append(continue_btn)
        self.stop_buttons.append(stop_btn)

        self.refresh_steps()
        return frame

    def make_history_page(self, parent):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text="History", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 6))
        self.build_motor_status_strip(frame)
        ttk.Label(frame, textvariable=self.connection_text, foreground="#555555").pack(anchor="w", pady=(0, 6))
        self.history_log = scrolledtext.ScrolledText(frame, state="disabled", wrap="word")
        self.history_log.pack(fill="both", expand=True)

        emergency = ttk.LabelFrame(frame, text="Emergency Controls")
        emergency.pack(fill="x", pady=(8, 0))
        ttk.Label(emergency, textvariable=self.pause_text, foreground="#8B0000").pack(anchor="w", padx=8, pady=(8, 4))
        controls = ttk.Frame(emergency)
        controls.pack(fill="x", padx=8, pady=(0, 8))
        pause_btn = ttk.Button(controls, text="Emergency Stop", command=self.emergency_stop)
        pause_btn.pack(side="left", padx=(0, 6))
        continue_btn = ttk.Button(controls, text="Continue", command=self.continue_experiment, state="disabled")
        continue_btn.pack(side="left", padx=6)
        stop_btn = ttk.Button(controls, text="Stop Experiment", command=self.stop_experiment, state="disabled")
        stop_btn.pack(side="left", padx=6)
        self.pause_buttons.append(pause_btn)
        self.continue_buttons.append(continue_btn)
        self.stop_buttons.append(stop_btn)
        return frame

    def start_jog(self, direction):
        motor = self.sel_motor.get()
        if not self.can_manual_control(motor):
            return
        try:
            rate = float(self.jog_rate.get())
        except Exception:
            rate = 1.0
        self.bridge.jog_start(motor, rate, direction)

    def stop_jog(self):
        motor = self.sel_motor.get()
        self.bridge.jog_stop(motor)

    def move_relative(self):
        motor = self.sel_motor.get()
        if not self.can_manual_control(motor):
            return
        try:
            value = float(self.rel.get())
        except Exception:
            self.add_log("[WARN] invalid relative value")
            return
        if value == 0:
            self.add_log(f"[MOVE] {motor} relative zero ignored")
            return
        self.bridge.move_relative(motor, value)

    def move_absolute(self):
        try:
            target = float(self.abs.get())
        except Exception:
            self.add_log("[WARN] invalid absolute value")
            return
        self.bridge.move_absolute(self.sel_motor.get(), target)

    def emergency_stop(self):
        if self.paused:
            return
        self.paused = True
        self.bridge.pause_all()
        self.refresh_experiment_status_from_state()

    def continue_experiment(self):
        if not self.paused:
            return
        self.paused = False
        self.bridge.resume_all()
        self.refresh_experiment_status_from_state()

    def stop_experiment(self):
        active_runs = self.active_run_motors()
        if active_runs:
            confirmed = messagebox.askyesno(
                "Stop Experiment",
                "This will discard the active loaded sequence for the running motor(s). Continue?",
                parent=self,
            )
            if not confirmed:
                self.add_log("[STOP CANCELLED] Active sequence kept.")
                return

        self.paused = False
        self.bridge.abort_all()
        self.refresh_experiment_status_from_state()

    def step_text(self, step, i):
        if step["type"] == "loop":
            return f"Step {i}: LOOP repeat all previous steps x{step['count']}"
        if step["motion_mode"] == "strain":
            disp = step["gauge_length"] * (step["strain_pct"] / 100.0)
            motion = f"strain={step['strain_pct']:.3f}% length={step['gauge_length']:.3f} mm disp={disp:.3f} mm"
        else:
            motion = f"displacement={step['displacement']:.3f} mm"
        if step["timing_mode"] == "cycles":
            timing = f"cycles={step['cycles']} freq={step['freq']:.3f}"
        else:
            timing = f"duration={step['duration']:.3f} {step['unit']}"
        return f"Step {i}: {step['direction']} {motion}; {timing}; rate={step['rate']:.3f}"

    def refresh_steps(self):
        self.step_box.delete(0, "end")
        motors = self.selected_program_motors()
        if not motors:
            self.update_program_summary()
            return

        preview_motor = self.current_preview_motor()
        steps = self.programs[preview_motor]
        for i, step in enumerate(steps, start=1):
            self.step_box.insert("end", self.step_text(step, i))
        self.update_program_summary()

    def add_action(self):
        motors = self.selected_program_motors()
        if not motors:
            messagebox.showinfo("Add Action", "Select at least one motor to program.")
            return
        d = ActionDialog(self, title="Add Action Step")
        if d.result:
            for motor in motors:
                self.programs[motor].append(copy.deepcopy(d.result))
            self.refresh_steps()

    def add_loop(self):
        motors = self.selected_program_motors()
        if not motors:
            messagebox.showinfo("Add Loop", "Select at least one motor to program.")
            return
        if any(not self.programs[motor] for motor in motors):
            messagebox.showinfo("Add Loop", "Every selected motor must already have prior steps before adding a loop.")
            return
        d = LoopDialog(self, title="Add Loop")
        if d.result:
            for motor in motors:
                self.programs[motor].append(copy.deepcopy(d.result))
            self.refresh_steps()

    def remove_step(self):
        motors = self.selected_program_motors()
        if not motors:
            return
        sel = self.step_box.curselection()
        if not sel:
            return
        index = sel[0]
        if any(index >= len(self.programs[motor]) for motor in motors):
            messagebox.showinfo("Remove Step", "The selected motors do not all have a step at that index.")
            return
        for motor in motors:
            del self.programs[motor][index]
        self.refresh_steps()

    def move_step(self, direction):
        motors = self.selected_program_motors()
        if not motors:
            return

        sel = self.step_box.curselection()
        if not sel:
            return

        index = sel[0]
        new_index = index + direction

        if new_index < 0:
            self.add_log("[WARN] Selected step is already at the top.")
            return

        if any(index >= len(self.programs[motor]) for motor in motors):
            messagebox.showinfo("Move Step", "The selected motors do not all have a step at that index.")
            return

        if any(new_index >= len(self.programs[motor]) for motor in motors):
            self.add_log("[WARN] Selected step is already at the bottom for one or more selected motors.")
            return

        for motor in motors:
            steps = self.programs[motor]
            steps[index], steps[new_index] = steps[new_index], steps[index]

        self.refresh_steps()
        self.step_box.selection_set(new_index)
        self.step_box.activate(new_index)

    def submit_program(self):
        motors = self.selected_program_motors()
        if not motors:
            messagebox.showinfo("Submit Program", "Select at least one motor to run.")
            return

        started = 0
        for motor in motors:
            if self.has_active_run(motor):
                self.add_log(f"[WARN] {motor} already has active motion")
                continue

            steps = self.programs[motor]
            if not steps:
                self.add_log(f"[WARN] {motor} has no program to submit")
                continue

            sequence = self.build_backend_sequence(motor)
            if self.bridge.load_program(motor, sequence) and self.bridge.start_program(motor):
                started += 1

        if started:
            self.refresh_experiment_status_from_state()

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
