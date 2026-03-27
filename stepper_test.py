from gpiozero import PWMOutputDevice, DigitalOutputDevice
from time import sleep
STEP_PIN=17
DIR_PIN=27
ENA_PIN=22
FREQ_HZ=20
STEPS=200

def main():

    step = DigitalOutputDevice(STEP_PIN, active_high=True, initial_value=False)
    direction = DigitalOutputDevice(DIR_PIN, active_high=True, initial_value=False)
    enable = DigitalOutputDevice(ENA_PIN, active_high=False, initial_value=True) if ENA_PIN is not None else None

    half_period = 1/(2*FREQ_HZ)
    
    try:
        direction.on()
        if enable:
            enable.off()
        print("Spinning...")
        for _ in range(STEPS):
            step.on()
            sleep(half_period)
            step.off()
            sleep(half_period)
    
    finally:
        print("Complete")
        step.off()
        direction.off()
        if enable:
            enable.on()
        
        step.close()
        direction.close()
        if enable:
            enable.close()
            
if __name__ == "__main__":
    main()