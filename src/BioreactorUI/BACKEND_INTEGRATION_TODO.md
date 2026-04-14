# Backend-Frontend-TODO

The UI now goes through `backend_bridge.py` instead of running motors directly inside `bioreactorUI.py`.

## What the UI needs

These are the methods the frontend is expecting:

`connect()`
`poll_events()`
`jog_start(motor, rate_mm_per_sec, direction)`
`jog_stop(motor)`
`move_relative(motor, delta_mm)`
`move_absolute(motor, target_mm)`
`load_program(motor, steps)`
`start_program(motor)`
`pause_all()`
`resume_all()`
`abort_all()`
`has_active_run(motor)`

## UI listens for displaying the following

Right now the frontend handles these event shapes:

`{"type": "log", "message": "..."}`
`{"type": "motor_state", "motor": "Motor 1", "state": "running"}`
`{"type": "motor_position", "motor": "Motor 1", "position": 12.34}`
`{"type": "motor_step", "motor": "Motor 1", "step": "Step: 2/8"}`

## Step payload the UI sends

The frontend expands loops itself before handing steps off. Each step currently looks like this:

{
    "type": "action",
    "direction": "tension",
    "rate": 1.0,
    "frequency_hz": 1.0,
    "displacement_mm": 0.5,
    "timing_mode": "duration",
    "duration_seconds": 60.0,
    "estimated_seconds": 60.0,
    "cycles": 0,
    "target_position_mm": 0.5,
    "label": "tension displacement=0.500 mm; duration=1.000 Minutes; rate=1.000",
}

## Notes

Loop expansion stays on the frontend for now so current UI behavior does not change if I need to make any revisions.

If the user enters strain, the frontend converts it to displacement in mm before sending it. You just need to interpret displacement.

`label` is mainly there so logs/status messages can echo something readable.

## Backend-side to-do list

Remove the placeholder project creation during backend startup.
Implement a real version of the adapter above.
Send structured events back instead of only writing to the console.
Decide what transport we want to use: stdin/stdout JSON, local HTTP, or some other local IPC.
Keep pause, resume, and abort behavior on the backend side so the UI does not have to fake it.
Confirm the exact meaning of rate, frequency, duration, and cycles for the motion actions.
