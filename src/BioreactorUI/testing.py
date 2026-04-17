from backend_bridge import HttpBackendBridge

def motor_output(events, status):
    print("events: ", events)
    print("status: ", status)

bridge = HttpBackendBridge(["Motor 1"])
if bridge.connect():
    bridge.jog_start("Motor 1", rate=5.0, direction=1, callback=motor_output)
else:
    print("backend not running")