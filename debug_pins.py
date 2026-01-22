
import RPi.GPIO as GPIO
import time
import signal
import sys

# Set mode to BCM (standard for most scripts)
GPIO.setmode(GPIO.BCM)

# List of BCM pins to monitor
DISPLAY_PINS = [17, 25, 8, 24, 10, 11, 18]
MONITOR_PINS = [p for p in range(2, 28) if p not in DISPLAY_PINS]

print("--- GPIO Pin Diagnostic Tool (Low Level) ---")
print("Using RPi.GPIO library")
print("Monitoring all non-display pins for activity...")
print("Note: Activity could be Signal going LOW or HIGH.")
print("Press Ctrl+C to exit.\n")

# Setup pins with internal pull-ups
for p in MONITOR_PINS:
    try:
        GPIO.setup(p, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    except Exception as e:
        print(f"Error setting up BCM Pin {p}: {e}")

# Keep track of last state
last_states = {p: GPIO.input(p) for p in MONITOR_PINS}

def signal_handler(sig, frame):
    print("\nExiting and cleaning up...")
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

try:
    while True:
        for p in MONITOR_PINS:
            current = GPIO.input(p)
            if current != last_states[p]:
                state_str = "HIGH" if current else "LOW (GND)"
                print(f"!! Activity on BCM Pin {p}: changed to {state_str}")
                last_states[p] = current
        time.sleep(0.05)
except Exception as e:
    print(f"Error: {e}")
    GPIO.cleanup()
