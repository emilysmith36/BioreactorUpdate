import subprocess
import sys
import time

# Start backend (.NET)
backend = subprocess.Popen(
    ["dotnet", "run", "--project", "BioreactorControl/BioreactorControl.csproj"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Give backend a moment to boot
time.sleep(2)

# Start Python UI
ui = subprocess.Popen(
    [sys.executable, "BioreactorUI/BioreactorUI.py"],
)

try:
    backend.wait()
    ui.wait()
except KeyboardInterrupt:
    print("Shutting down...")
    backend.terminate()
    ui.terminate()