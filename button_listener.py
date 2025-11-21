#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
import os
import sys
import logging
import threading
from threading import Timer

# Add current directory to path to import tracker
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from tracker import HabitTracker

# Configuration
# Using BCM numbering (GPIO XX)
BUTTON_PIN = 5  # Physical Pin 29
LED_PIN = 6     # Physical Pin 31

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class App:
    def __init__(self):
        self.setup_gpio()
        self.tracker = HabitTracker()
        self.reset_timer = None
        self.lock = threading.Lock()

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.HIGH) # Initial State: LED ON

    def flash_led(self, times=5, interval=0.1):
        def _flash():
            for _ in range(times):
                GPIO.output(LED_PIN, GPIO.LOW) # Off
                time.sleep(interval)
                GPIO.output(LED_PIN, GPIO.HIGH) # On
                time.sleep(interval)
        
        # Run in separate thread to not block display update
        threading.Thread(target=_flash, daemon=True).start()

    def on_reset(self):
        logger.info("Timer expired. Resetting display.")
        with self.lock:
            self.tracker.reset()
            self.tracker.sleep()

    def run(self):
        logger.info("Button listener started. Press Ctrl+C to exit.")
        try:
            while True:
                # Wait for button press
                GPIO.wait_for_edge(BUTTON_PIN, GPIO.FALLING)
                
                # Debounce
                time.sleep(0.05)
                if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    logger.info("Button pressed!")
                    
                    # 1. Flash LED (Non-blocking)
                    self.flash_led()
                    
                    # 2. Cancel existing timer if any
                    if self.reset_timer:
                        self.reset_timer.cancel()
                    
                    # 3. Update Display (Blocking, but LED is already flashing)
                    with self.lock:
                        self.tracker.update()
                    
                    # 4. Start new Reset Timer (30s)
                    self.reset_timer = Timer(30.0, self.on_reset)
                    self.reset_timer.start()
                    
                    # Simple debounce delay
                    time.sleep(0.5)
                    
        except KeyboardInterrupt:
            logger.info("Exiting...")
            if self.reset_timer:
                self.reset_timer.cancel()
        finally:
            GPIO.cleanup()

if __name__ == "__main__":
    app = App()
    app.run()
