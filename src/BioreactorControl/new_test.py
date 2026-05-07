from gpiozero import DigitalOutputDevice
from time import sleep
import sys

# --- Hardware Configuration ---
STEP_PIN = 17  # Connected to PUL- [cite: 1124]
DIR_PIN = 27   # Connected to DIR- [cite: 1124]
ENA_PIN = 22   # Connected to EN-  [cite: 1124]

# --- Physical Constants ---
MM_PER_REV = 2      # From Motor Parameter Equations 
STEPS_PER_REV = 200      # Standard 1.8 degree motor 
MICROSTEPS = 8           # Based on Phase 3 DIP settings [cite: 674]
PULSES_PER_REV = STEPS_PER_REV * MICROSTEPS
PULSES_PER_MM = PULSES_PER_REV / MM_PER_REV  # ~2624.67 pulses/mm

def move_stepper(target_mm, speed_mm_s):
    """
    Moves the stepper motor to a target position.
    target_mm: Distance to move (positive or negative)
    speed_mm_s: Speed in mm/second
    """
    # Initialize Pins
    # active_high=False because of Common-Anode wiring 
    # In common-anode, pulling the pin LOW (GND) activates the signal.
    step_signal = DigitalOutputDevice(STEP_PIN, active_high=False)
    direction_signal = DigitalOutputDevice(DIR_PIN, active_high=False)
    
    # Motor Enable Logic: In common-anode, pulling EN- LOW (on) 
    # enters "Free State". Pulling it HIGH (off) enables "Auto Control"[cite: 920, 922].
    enable_signal = DigitalOutputDevice(ENA_PIN, active_high=False, initial_value=False)

    # Calculate required pulses and frequency
    total_pulses = int(abs(target_mm) * PULSES_PER_MM)
    frequency_hz = speed_mm_s * PULSES_PER_MM
    
    if frequency_hz <= 0:
        print("Speed must be greater than 0.")
        return

    # Set Direction
    if target_mm > 0:
        direction_signal.off() # Adjust based on actual actuator orientation
    else:
        direction_signal.on()

    # Calculate timing (Half-period for 50% duty cycle pulse)
    delay = 1.0 / (2.0 * frequency_hz)

    print(f"Moving {target_mm} mm at {speed_mm_s} mm/s...")
    print(f"Executing {total_pulses} pulses at {frequency_hz:.2f} Hz.")

    try:
        for _ in range(total_pulses):
            step_signal.on()
            sleep(delay)
            step_signal.off()
            sleep(delay)
    except KeyboardInterrupt:
        print("\nMovement interrupted by user.")
    finally:
        print("Movement complete.")
        # Clean up
        step_signal.close()
        direction_signal.close()
        enable_signal.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python move_stepper.py [distance_mm] [speed_mm_s]")
        print("Example: python move_stepper.py 10 2")
    else:
        dist = float(sys.argv[1])
        spd = float(sys.argv[2])
        move_stepper(dist, spd)