import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
import os
from pathlib import Path
from collections import deque


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "BioreactorControl"
UI_DIR = ROOT / "BioreactorUI"

DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:5000"
RAW_BACKEND_BASE_URL = os.environ.get("BIOREACTOR_BACKEND_BASE_URL", DEFAULT_BACKEND_BASE_URL).rstrip("/")


def _normalize_client_base_url(url: str) -> str:
    # 0.0.0.0 is a bind-all address, not something clients can connect to.
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname == "0.0.0.0":
        parsed = parsed._replace(netloc=parsed.netloc.replace("0.0.0.0", "127.0.0.1"))
        return parsed.geturl().rstrip("/")
    return url.rstrip("/")


BACKEND_CLIENT_BASE_URL = _normalize_client_base_url(RAW_BACKEND_BASE_URL)
BACKEND_HEALTH_URL = f"{BACKEND_CLIENT_BASE_URL}/api/status"
BACKEND_API_BASE_URL = f"{BACKEND_CLIENT_BASE_URL}/api"
MOTORCONTROL_HOST = "127.0.0.1"
MOTORCONTROL_PORT = 8000

LOG_TAILS = {
    "backend": deque(maxlen=200),
    "motorcontrol": deque(maxlen=200),
    "ui": deque(maxlen=200),
}


def stream_output(name, process):
    if process.stdout is None:
        return

    for line in process.stdout:
        try:
            LOG_TAILS.setdefault(name, deque(maxlen=200)).append(line.rstrip("\n"))
        except Exception:
            pass
        print(f"[{name}] {line}", end="")


def start_process(name, command, cwd):
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=dict(
            **os.environ,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    thread = threading.Thread(target=stream_output, args=(name, process), daemon=True)
    thread.start()
    return process


def wait_for_http(url, timeout_s):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.25)
    return False


def wait_for_http_or_exit(url, timeout_s, process, name):
    """Wait for an HTTP endpoint, but fail fast if the process exits."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited early (exit code {process.returncode})")
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.25)
    return False


def _format_tail(name: str) -> str:
    tail = list(LOG_TAILS.get(name, []))
    if not tail:
        return f"(no {name} output captured)"
    joined = "\n".join(tail[-60:])
    return f"--- last {min(60, len(tail))} lines from {name} ---\n{joined}\n--- end {name} ---"


def wait_for_tcp(host, port, timeout_s):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def terminate_process(process):
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main():
    backend = None
    motorcontrol = None
    ui = None

    try:
        print("Starting backend...")
        # Force a known backend URL so the UI/diagnostics behave the same on Windows and the Pi.
        #
        # Override defaults with:
        # - BIOREACTOR_BACKEND_BASE_URL=http://127.0.0.1:5000   (used by this script + UI)
        # - ASPNETCORE_URLS=http://0.0.0.0:5000                (Kestrel bind address; useful on the Pi)
        backend_env = dict(os.environ)
        backend_env.setdefault("ASPNETCORE_URLS", BACKEND_CLIENT_BASE_URL)
        # Allow running a net8 app on machines that only have a newer runtime installed (e.g. net10).
        backend_env.setdefault("DOTNET_ROLL_FORWARD", "LatestMajor")

        backend = subprocess.Popen(
            ["dotnet", "run", "--project", str(BACKEND_DIR / "BioreactorControl.csproj")],
            cwd=str(BACKEND_DIR),
            env=backend_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=stream_output, args=("backend", backend), daemon=True).start()

        if not wait_for_http_or_exit(BACKEND_HEALTH_URL, timeout_s=60, process=backend, name="Backend"):
            raise RuntimeError(
                "Backend did not become ready at /api/status.\n"
                f"Health URL: {BACKEND_HEALTH_URL}\n\n"
                f"{_format_tail('backend')}"
            )
        print("Backend is ready.")

        print("Starting motor control service...")
        try:
            import uvicorn  # noqa: F401
        except Exception as exc:
            raise RuntimeError(
                "Python dependency missing: uvicorn. Install deps (e.g. `pip install -r requirements.txt`)."
            ) from exc

        motorcontrol = start_process(
            "motorcontrol",
            [sys.executable, "-m", "uvicorn", "MOTORCONTROLDRAFT:app", "--host", "0.0.0.0", "--port", "8000"],
            ROOT,
        )

        if not wait_for_tcp(MOTORCONTROL_HOST, MOTORCONTROL_PORT, timeout_s=15):
            raise RuntimeError("Motor control service did not open port 8000")
        print("Motor control service is ready.")

        print("Starting UI...")
        ui_env = dict(os.environ)
        ui_env.setdefault("BIOREACTOR_BACKEND_URL", BACKEND_API_BASE_URL)
        ui = subprocess.Popen(
            [sys.executable, "bioreactorUI.py"],
            cwd=str(UI_DIR),
            env=ui_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        threading.Thread(target=stream_output, args=("ui", ui), daemon=True).start()
        print("System is running. Press Ctrl+C to stop everything.")

        while True:
            if backend.poll() is not None:
                raise RuntimeError("Backend process exited unexpectedly")
            if motorcontrol.poll() is not None:
                raise RuntimeError("Motor control service exited unexpectedly")
            if ui.poll() is not None:
                raise RuntimeError("UI process exited unexpectedly")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        for process in (ui, motorcontrol, backend):
            if process is not None:
                terminate_process(process)


if __name__ == "__main__":
    main()
