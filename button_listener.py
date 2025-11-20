#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
import subprocess
import os
import sys
import logging

# Configuration
BUTTON_PIN = 5
LED_PIN = 6
TRACKER_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tracker.py")

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(LED_PIN, GPIO.OUT)

def flash_led(times=5, interval=0.1):
    for _ in range(times):
        GPIO.output(LED_PIN, GPIO.LOW) # Off
        time.sleep(interval)
        GPIO.output(LED_PIN, GPIO.HIGH) # On
        time.sleep(interval)

def run_tracker():
    logger.info("Running tracker script...")
    try:
        # Run tracker.py using the same python interpreter
        subprocess.run([sys.executable, TRACKER_SCRIPT], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Tracker script failed: {e}")
    except Exception as e:
        logger.error(f"Error running tracker: {e}")

def main():
    setup_gpio()
    logger.info("Button listener started. Press Ctrl+C to exit.")
    
    try:
        # Initial State: LED ON
        GPIO.output(LED_PIN, GPIO.HIGH)
        
        while True:
            # Wait for button press (Falling edge because of Pull Up)
            # Using wait_for_edge is more efficient than polling
            GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
            
            # Debounce / Check if it's a real press
            time.sleep(0.05)
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                logger.info("Button pressed!")
                
                # Flash LED
                flash_led()
                
                # Run Tracker
                run_tracker()
                
                # Return to Idle State (LED ON)
                GPIO.output(LED_PIN, GPIO.HIGH)
                
                # Simple debounce delay to prevent double triggers
                time.sleep(0.5)
                
    except KeyboardInterrupt:
        logger.info("Exiting...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
