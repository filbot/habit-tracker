
import time
import signal
import sys
from gpiozero import DigitalInputDevice

# BCM pins used by the e-paper display — skip these
DISPLAY_PINS = [17, 25, 8, 24, 10, 11, 18]
MONITOR_PINS = [p for p in range(2, 28) if p not in DISPLAY_PINS]

print("--- GPIO Pin Diagnostic Tool ---")
print("Using gpiozero (lgpio backend)")
print("Monitoring all non-display pins for activity...")
print("Note: Activity could be Signal going LOW or HIGH.")
print("Press Ctrl+C to exit.\n")

# Setup pins with internal pull-ups
pins = {}
for p in MONITOR_PINS:
    try:
        pins[p] = DigitalInputDevice(p, pull_up=True)
    except Exception as e:
        print(f"Skipping BCM Pin {p}: {e}")

if not pins:
    print("\nCRITICAL: No pins could be initialized. Are you sure the service isn't still running?")
    print("Run: sudo systemctl stop habit-tracker")
    sys.exit(1)

print(f"\nMonitoring {len(pins)} pins: {list(pins.keys())}")

# Keep track of last state
last_states = {p: dev.value for p, dev in pins.items()}

def cleanup_and_exit(sig=None, frame=None):
    print("\nExiting and cleaning up...")
    for dev in pins.values():
        dev.close()
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup_and_exit)

try:
    while True:
        for p, dev in pins.items():
            current = dev.value
            if current != last_states[p]:
                state_str = "HIGH" if current else "LOW (GND)"
                print(f"!! Activity on BCM Pin {p}: changed to {state_str}")
                last_states[p] = current
        time.sleep(0.05)
except Exception as e:
    print(f"Error: {e}")
    cleanup_and_exit()
