#!/usr/bin/env python3
"""
Diagnostic test for the current backend-driven motor path.

Important note:
This test only verifies the new backend/API control path. A successful run does not
guarantee physical motor movement unless `MotorControl.cs` has been wired to real
hardware control, since the current move path may still be simulated in software.

What it checks:
1. Backend can start and answer HTTP health/status requests.
2. A selected motor exists and can accept a move command.
3. Status/events change after the command.
4. A simple one-step program can be loaded and started.

This script is meant to diagnose where the new system breaks, not just
whether it "works" or "doesn't work".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
BACKEND_PROJECT = ROOT / "BioreactorControl" / "BioreactorControl.csproj"
BASE_URL = "http://localhost:5000/api"


class TestFailure(RuntimeError):
    pass


def print_step(title: str) -> None:
    print(f"\n=== {title} ===")


def print_ok(message: str) -> None:
    print(f"[PASS] {message}")


def print_warn(message: str) -> None:
    print(f"[WARN] {message}")


def print_fail(message: str) -> None:
    print(f"[FAIL] {message}")


def safe_json(response: requests.Response):
    try:
        return response.json()
    except ValueError:
        return None


def wait_for_backend(base_url: str, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = requests.get(f"{base_url}/status", timeout=1.0)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.25)
    return False


def fetch_all_status(base_url: str):
    resp = requests.get(f"{base_url}/status/all", timeout=2.0)
    if resp.status_code != 200:
        raise TestFailure(f"/status/all returned HTTP {resp.status_code}")
    data = safe_json(resp)
    if not isinstance(data, list):
        raise TestFailure("/status/all did not return a JSON list")
    return data


def fetch_events(base_url: str):
    resp = requests.get(f"{base_url}/events", timeout=2.0)
    if resp.status_code != 200:
        raise TestFailure(f"/events returned HTTP {resp.status_code}")
    data = safe_json(resp)
    if not isinstance(data, list):
        raise TestFailure("/events did not return a JSON list")
    return data


def find_motor_status(statuses, motor_name: str):
    for item in statuses:
        if item.get("motor") == motor_name:
            return item
    return None


def wait_for_position_change(base_url: str, motor_name: str, start_position: float, timeout_s: float):
    deadline = time.time() + timeout_s
    last_status = None
    seen_events = []

    while time.time() < deadline:
        statuses = fetch_all_status(base_url)
        last_status = find_motor_status(statuses, motor_name)
        if last_status and abs(last_status.get("position", start_position) - start_position) > 1e-6:
            return last_status, seen_events

        events = fetch_events(base_url)
        seen_events.extend(events)
        time.sleep(0.2)

    return last_status, seen_events


def wait_for_state(base_url: str, motor_name: str, expected_states: set[str], timeout_s: float):
    deadline = time.time() + timeout_s
    seen_events = []

    while time.time() < deadline:
        statuses = fetch_all_status(base_url)
        status = find_motor_status(statuses, motor_name)
        if status and str(status.get("state", "")).lower() in expected_states:
            return status, seen_events

        events = fetch_events(base_url)
        seen_events.extend(events)
        time.sleep(0.2)

    return None, seen_events


def start_backend_process():
    return subprocess.Popen(
        ["dotnet", "run", "--project", str(BACKEND_PROJECT)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def terminate_process(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def run_move_test(base_url: str, motor_name: str, distance_mm: float) -> None:
    print_step("Manual Move Test")

    statuses = fetch_all_status(base_url)
    status = find_motor_status(statuses, motor_name)
    if status is None:
        raise TestFailure(f"{motor_name} was not found in /status/all")

    start_position = float(status.get("position", 0.0))
    print_ok(f"{motor_name} found at position {start_position:.3f}")

    resp = requests.post(
        f"{base_url}/motor/move-relative",
        json={"motor": motor_name, "distance": distance_mm},
        timeout=2.0,
    )
    if resp.status_code != 200:
        body = resp.text.strip() or "<empty body>"
        raise TestFailure(f"move-relative failed with HTTP {resp.status_code}: {body}")
    print_ok(f"move-relative command accepted for {motor_name}")

    updated_status, events = wait_for_position_change(base_url, motor_name, start_position, timeout_s=4.0)
    if updated_status is None:
        raise TestFailure("Could not read updated motor status after move command")

    end_position = float(updated_status.get("position", start_position))
    if abs(end_position - start_position) <= 1e-6:
        print_fail(f"{motor_name} position did not change after move command")
        print_warn("Possible causes:")
        print_warn("- backend route accepted the command but did not execute movement")
        print_warn("- motor state blocked the move")
        print_warn("- hardware path is still simulated or not yet wired")
        print_warn(f"- events seen during wait: {json.dumps(events[-5:], indent=2) if events else 'none'}")
        raise TestFailure("Manual move path did not produce a position change")

    print_ok(f"{motor_name} position changed from {start_position:.3f} to {end_position:.3f}")


def run_program_test(base_url: str, motor_name: str) -> None:
    print_step("Program Load/Start Test")

    steps = [
        {
            "type": "action",
            "direction": "tension",
            "rate": 1.0,
            "frequency_hz": 1.0,
            "displacement_mm": 1.0,
            "timing_mode": "duration",
            "duration_seconds": 1.0,
            "estimated_seconds": 1.0,
            "cycles": 0,
            "target_position_mm": 1.0,
            "label": "smoketest step",
        }
    ]

    load_resp = requests.post(
        f"{base_url}/program/load",
        json={"motor": motor_name, "steps": steps},
        timeout=2.0,
    )
    if load_resp.status_code != 200:
        body = load_resp.text.strip() or "<empty body>"
        raise TestFailure(f"program/load failed with HTTP {load_resp.status_code}: {body}")
    print_ok("Program load route accepted test step")

    start_resp = requests.post(
        f"{base_url}/program/start",
        json={"motor": motor_name},
        timeout=2.0,
    )
    if start_resp.status_code != 200:
        body = start_resp.text.strip() or "<empty body>"
        raise TestFailure(f"program/start failed with HTTP {start_resp.status_code}: {body}")
    print_ok("Program start route accepted test run")

    running_status, running_events = wait_for_state(base_url, motor_name, {"running", "stopped", "idle"}, timeout_s=4.0)
    if running_status is None:
        print_fail("Did not observe a useful state change after starting the program")
        print_warn(f"Recent events: {json.dumps(running_events[-5:], indent=2) if running_events else 'none'}")
        raise TestFailure("Program run state did not update")

    print_ok(f"Observed program-related state: {running_status.get('state')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the current backend motor control path.")
    parser.add_argument("--motor", default="Motor 1", help='Motor name, for example "Motor 1"')
    parser.add_argument("--distance", type=float, default=5.0, help="Relative move distance in mm for manual move test")
    parser.add_argument("--base-url", default=BASE_URL, help="Backend API base URL")
    parser.add_argument(
        "--start-backend",
        action="store_true",
        help="Start the .NET backend automatically before testing",
    )
    args = parser.parse_args()

    backend_process = None

    try:
        if args.start_backend:
            print_step("Starting Backend")
            backend_process = start_backend_process()
            print_ok("Backend process launched")

        print_step("Backend Health Check")
        if not wait_for_backend(args.base_url, timeout_s=10.0):
            raise TestFailure(
                "Backend did not become healthy at /api/status.\n"
                "Likely failure points:\n"
                "- dotnet backend did not start\n"
                "- backend bound to a different port\n"
                "- firewall or host issue\n"
                "- startup exception in Program.cs"
            )
        print_ok("Backend responded at /api/status")

        statuses = fetch_all_status(args.base_url)
        if not statuses:
            raise TestFailure("/status/all returned no motors")
        print_ok(f"Backend reports {len(statuses)} motor(s)")

        run_move_test(args.base_url, args.motor, args.distance)
        run_program_test(args.base_url, args.motor)

        print_step("Result")
        print_ok("Smoke test finished successfully")
        return 0

    except TestFailure as exc:
        print_step("Result")
        print_fail(str(exc))
        return 1

    except requests.RequestException as exc:
        print_step("Result")
        print_fail(f"HTTP request failed: {exc}")
        print_warn("Likely failure is between the test script and the backend API.")
        return 1

    finally:
        terminate_process(backend_process)


if __name__ == "__main__":
    raise SystemExit(main())
