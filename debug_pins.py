
import time
from gpiozero import Button
import signal
import sys

# List of pins to monitor (excluding display pins)
DISPLAY_PINS = [17, 25, 8, 24, 10, 11]
MONITOR_PINS = [2, 3, 4, 5, 6, 7, 9, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 26, 27]

print("--- GPIO Pin Diagnostic Tool ---")
print("Monitoring all non-display pins...")
print("Press a button on your Pi to see which pin responds.")
print("Press Ctrl+C to exit.\n")

buttons = []
for p in MONITOR_PINS:
    try:
        # Try both active-low (pull-up) and potentially active-high
        # Actually just monitoring the raw value is easier
        btn = Button(p, pull_up=True) 
        btn.when_pressed = lambda b=p: print(f"!! Activity detected on BCM Pin {b} (Signal went LOW - Pulled to GND)")
        btn.when_released = lambda b=p: print(f"   Activity detected on BCM Pin {b} (Signal went HIGH)")
        buttons.append(btn)
    except Exception as e:
        pass

def signal_handler(sig, frame):
    print("\nExiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

while True:
    time.sleep(1)
