#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, scrolledtext
import time

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

        ttk.Label(master, text="Gauge Length").grid(row=4, column=0, sticky="e", padx=(0, 8), pady=3)
        self.length_entry = ttk.Entry(master, textvariable=self.length)
        self.length_entry.grid(row=4, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Strain (%)").grid(row=5, column=0, sticky="e", padx=(0, 8), pady=3)
        self.strain_entry = ttk.Entry(master, textvariable=self.strain)
        self.strain_entry.grid(row=5, column=1, sticky="ew", pady=3)

        ttk.Label(master, text="Displacement").grid(row=6, column=0, sticky="e", padx=(0, 8), pady=3)
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
            self.strain_label.set(f"Derived displacement from strain: {d:.3f}")
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
            float(self.rate.get())
            float(self.freq.get())
            if self.motion.get() == "strain":
                float(self.length.get())
                float(self.strain.get())
            else:
                float(self.displacement.get())
            if self.timing.get() == "duration":
                float(self.duration.get())
            else:
                int(self.cycles.get())
        except Exception:
            messagebox.showerror("Invalid Action Step", "Please enter valid numbers.", parent=self)
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

        self.motors = ["Motor 1", "Motor 2", "Motor 3"]
        self.pos = {m: 0.0 for m in self.motors}
        self.state = {m: "idle" for m in self.motors}
        self.programs = {m: [] for m in self.motors}
        self.jog_jobs = {}
        self.paused = False

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

    def show(self, name):
        for p in self.pages.values():
            p.grid_forget()
        self.pages[name].grid(row=0, column=0, sticky="nsew")

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

    def make_control_page(self, parent):
        frame = ttk.Frame(parent)
        frame.columnconfigure(1, weight=1)

        left = ttk.Frame(frame)
        left.grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=4)

        ttk.Label(left, text="Select Motor").pack(anchor="w")
        self.sel_motor = tk.StringVar(value=self.motors[0])
        ttk.Combobox(left, textvariable=self.sel_motor, values=self.motors, state="readonly", width=18).pack(fill="x", pady=6)

        ttk.Label(left, text="Jog rate (units/sec)").pack(anchor="w")
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

        ttk.Label(left, text="Relative move").pack(anchor="w")
        self.rel = tk.DoubleVar(value=10.0)
        ttk.Spinbox(left, from_=-1000000000, to=1000000000, increment=0.1, textvariable=self.rel, width=14).pack(pady=4)
        ttk.Button(left, text="Move Relative", command=self.move_relative).pack(fill="x", pady=4)

        ttk.Label(left, text="Absolute move").pack(anchor="w", pady=(8, 0))
        self.abs = tk.DoubleVar(value=0.0)
        ttk.Spinbox(left, from_=-1000000000000, to=1000000000000, increment=0.1, textvariable=self.abs, width=14).pack(pady=4)
        ttk.Button(left, text="Move Absolute", command=self.move_absolute).pack(fill="x", pady=4)

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=8)

        self.pause_text = tk.StringVar(value="Experiment Status: Ready")
        ttk.Label(left, textvariable=self.pause_text, foreground="#8B0000").pack(anchor="w", pady=(0, 4))
        self.pause_btn = ttk.Button(left, text="Emergency Stop", command=self.emergency_stop)
        self.pause_btn.pack(fill="x", pady=4)
        self.continue_btn = ttk.Button(left, text="Continue", command=self.continue_experiment, state="disabled")
        self.continue_btn.pack(fill="x", pady=4)
        self.stop_btn = ttk.Button(left, text="Stop Experiment", command=self.stop_experiment, state="disabled")
        self.stop_btn.pack(fill="x", pady=4)

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="Motor Positions", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        pos_frame = ttk.Frame(right)
        pos_frame.pack(fill="x", pady=(6, 8))
        self.pos_labels = {}
        for motor in self.motors:
            lbl = ttk.Label(pos_frame, text=f"{motor}: 0.000 (idle)")
            lbl.pack(anchor="w", pady=2)
            self.pos_labels[motor] = lbl

        ttk.Label(right, text="Log", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(8, 0))
        self.control_log = scrolledtext.ScrolledText(right, height=18, state="disabled", wrap="none")
        self.control_log.pack(fill="both", expand=True, pady=(4, 0))

        return frame

    def make_project_page(self, parent):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text="Project Settings - Program Builder", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))

        top = ttk.Frame(frame)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Program motor:").pack(side="left")
        self.proj_motor = tk.StringVar(value=self.motors[0])
        combo = ttk.Combobox(top, textvariable=self.proj_motor, values=self.motors, state="readonly", width=18)
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_steps())
        self.program_text = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.program_text).pack(side="left", padx=(10, 0))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)
        self.step_box = tk.Listbox(list_frame, height=18)
        self.step_box.pack(side="left", fill="both", expand=True, padx=(0, 6))
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.step_box.yview)
        scroll.pack(side="right", fill="y")
        self.step_box.configure(yscrollcommand=scroll.set)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Add Action", command=self.add_action).pack(side="left", padx=4)
        ttk.Button(buttons, text="Add Loop", command=self.add_loop).pack(side="left", padx=4)
        ttk.Button(buttons, text="Remove Selected", command=self.remove_step).pack(side="left", padx=4)
        ttk.Button(buttons, text="Submit Program", command=self.submit_program).pack(side="right", padx=4)

        self.refresh_steps()
        return frame

    def make_history_page(self, parent):
        frame = ttk.Frame(parent)
        ttk.Label(frame, text="History", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 6))
        self.history_log = scrolledtext.ScrolledText(frame, state="disabled", wrap="none")
        self.history_log.pack(fill="both", expand=True)
        return frame

    def start_jog(self, direction):
        if self.paused:
            self.add_log("[WARN] Cannot jog while paused")
            return
        motor = self.sel_motor.get()
        if motor in self.jog_jobs:
            return
        try:
            rate = float(self.jog_rate.get())
        except Exception:
            rate = 1.0
        self.state[motor] = "jogging"
        self.update_motor_label(motor)
        self.add_log(f"[JOG START] {motor} dir={'up' if direction > 0 else 'down'} rate={rate}")
        last = time.time()

        def tick():
            nonlocal last
            now = time.time()
            dt = now - last
            last = now
            self.pos[motor] += rate * dt * direction
            self.update_motor_label(motor)
            self.jog_jobs[motor] = self.after(100, tick)

        self.jog_jobs[motor] = self.after(100, tick)

    def stop_jog(self):
        motor = self.sel_motor.get()
        job = self.jog_jobs.pop(motor, None)
        if not job:
            return
        try:
            self.after_cancel(job)
        except Exception:
            pass
        self.state[motor] = "idle"
        self.update_motor_label(motor)
        self.add_log(f"[JOG STOP] {motor}")

    def move_relative(self):
        if self.paused:
            self.add_log("[WARN] Cannot move while paused")
            return
        motor = self.sel_motor.get()
        if motor in self.jog_jobs:
            self.add_log(f"[WARN] {motor} is already jogging")
            return
        try:
            value = float(self.rel.get())
        except Exception:
            self.add_log("[WARN] invalid relative value")
            return
        if value == 0:
            self.add_log(f"[MOVE] {motor} relative zero ignored")
            return
        self.state[motor] = "moving"
        self.update_motor_label(motor)
        self.add_log(f"[MOVE START] {motor} relative {value}")
        self.pos[motor] += value
        self.state[motor] = "idle"
        self.update_motor_label(motor)
        self.add_log(f"[MOVE END] {motor} pos={self.pos[motor]:.3f}")

    def move_absolute(self):
        try:
            target = float(self.abs.get())
        except Exception:
            self.add_log("[WARN] invalid absolute value")
            return
        self.rel.set(target - self.pos[self.sel_motor.get()])
        self.move_relative()

    def emergency_stop(self):
        if self.paused:
            return
        for motor in self.motors:
            job = self.jog_jobs.pop(motor, None)
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
                self.state[motor] = "paused"
                self.update_motor_label(motor)
        self.paused = True
        self.pause_text.set("Experiment Status: Emergency-paused")
        self.pause_btn.configure(state="disabled")
        self.continue_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        self.add_log("[EMERGENCY STOP] Motion paused. Choose Continue or Stop Experiment.")

    def continue_experiment(self):
        if not self.paused:
            return
        self.paused = False
        for motor in self.motors:
            if self.state[motor] == "paused":
                self.state[motor] = "idle"
                self.update_motor_label(motor)
        self.pause_text.set("Experiment Status: Ready")
        self.pause_btn.configure(state="normal")
        self.continue_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.add_log("[EXPERIMENT CONTINUE] Pause cleared.")

    def stop_experiment(self):
        for motor in self.motors:
            job = self.jog_jobs.pop(motor, None)
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    pass
            self.state[motor] = "idle"
            self.update_motor_label(motor)
        self.paused = False
        self.pause_text.set("Experiment Status: Ready")
        self.pause_btn.configure(state="normal")
        self.continue_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        self.add_log("[EXPERIMENT STOPPED] Motion stopped.")

    def step_text(self, step, i):
        if step["type"] == "loop":
            return f"Step {i}: LOOP x{step['count']}"
        if step["motion_mode"] == "strain":
            disp = step["gauge_length"] * (step["strain_pct"] / 100.0)
            motion = f"strain={step['strain_pct']:.3f}% length={step['gauge_length']:.3f} disp={disp:.3f}"
        else:
            motion = f"displacement={step['displacement']:.3f}"
        if step["timing_mode"] == "cycles":
            timing = f"cycles={step['cycles']} freq={step['freq']:.3f}"
        else:
            timing = f"duration={step['duration']:.3f} {step['unit']}"
        return f"Step {i}: {step['direction']} {motion}; {timing}; rate={step['rate']:.3f}"

    def refresh_steps(self):
        motor = self.proj_motor.get()
        steps = self.programs[motor]
        self.step_box.delete(0, "end")
        actions = 0
        loops = 0
        for i, step in enumerate(steps, start=1):
            if step["type"] == "loop":
                loops += 1
            else:
                actions += 1
            self.step_box.insert("end", self.step_text(step, i))
        self.program_text.set(f"{motor}: {len(steps)} steps, {actions} actions, {loops} loops")

    def add_action(self):
        d = ActionDialog(self, title="Add Action Step")
        if d.result:
            self.programs[self.proj_motor.get()].append(d.result)
            self.refresh_steps()

    def add_loop(self):
        motor = self.proj_motor.get()
        if not self.programs[motor]:
            messagebox.showinfo("Add Loop", "No prior steps to repeat. Add actions first.")
            return
        d = LoopDialog(self, title="Add Loop")
        if d.result:
            self.programs[motor].append(d.result)
            self.refresh_steps()

    def remove_step(self):
        sel = self.step_box.curselection()
        if not sel:
            return
        del self.programs[self.proj_motor.get()][sel[0]]
        self.refresh_steps()

    def submit_program(self):
        motor = self.proj_motor.get()
        steps = self.programs[motor]
        actions = 0
        loops = 0
        total_cycles = 0
        for step in steps:
            if step["type"] == "loop":
                loops += 1
            else:
                actions += 1
                if step["timing_mode"] == "cycles":
                    total_cycles += step["cycles"]
        self.add_log(f"[PROGRAM SUBMIT] {motor} | steps={len(steps)} actions={actions} loops={loops} total_cycles={total_cycles}")
        if not steps:
            self.add_log(f"[PROGRAM DETAIL] {motor} has no steps.")
            return
        for i, step in enumerate(steps, start=1):
            if step["type"] == "loop":
                self.add_log(f"[PROGRAM DETAIL] {motor} step {i}: loop x{step['count']}")
            else:
                self.add_log(f"[PROGRAM DETAIL] {motor} step {i}: {self.step_text(step, i)[8:]}")

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()