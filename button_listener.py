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
# GPIO Setup
BUTTON_PIN = 5  # BCM
LED_PIN = 6     # BCM

# Constants
LONG_PRESS_DURATION = 3.0  # Seconds
STATS_DURATION = 15.0      # Seconds

def flash_led(times=3, interval=0.1):
    """Flashes the LED in a separate thread."""
    def _flash():
        for _ in range(times):
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(interval)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(interval)
    threading.Thread(target=_flash).start()

def get_seconds_until_3am():
    """Calculates seconds until the next 3:00 AM."""
    now = datetime.datetime.now()
    next_3am = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if now >= next_3am:
        next_3am += datetime.timedelta(days=1)
    return (next_3am - now).total_seconds()

class HabitController:
    def __init__(self):
        self.tracker = HabitTracker()
        self.timer = None
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.LOW)
        
        # Start 3AM Scheduler
        self.schedule_reset()
        
        # Initial State
        self.tracker.initialize()

    def schedule_reset(self):
        """Schedules the daily reset at 3am."""
        seconds = get_seconds_until_3am()
        print(f"Scheduling reset in {seconds} seconds")
        self.reset_timer = threading.Timer(seconds, self.daily_reset)
        self.reset_timer.start()

    def daily_reset(self):
        """Resets the display to WYAO and reschedules."""
        print("Executing Daily Reset...")
        self.tracker.initialize()
        self.schedule_reset()

    def show_done_screen(self):
        """Shows the 'You did it' screen."""
        self.tracker.draw_done_screen()
        # LED is already off, ensuring it stays off

    def handle_short_press(self):
        """Log habit, show stats, then show done screen."""
        print("Short Press: Logging Habit")
        flash_led(1) # Quick flash confirmation
        
        # 1. Log and Show Stats
        self.tracker.update()
        
        # 2. Schedule transition to 'Done' screen
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(STATS_DURATION, self.show_done_screen)
        self.timer.start()

    def handle_long_press(self):
        """Manual Reset."""
        print("Long Press: Manual Reset")
        flash_led(5, 0.05) # Rapid flash
        
        if self.timer:
            self.timer.cancel()
            
        self.tracker.initialize()

    def run(self):
        print("Button Listener Started (Polling Mode)...")
        try:
            while True:
                    with self.lock:
                        self.tracker.update()
                    
                    # 4. Start new Reset Timer (15s)
                    self.reset_timer = Timer(15.0, self.on_reset)
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
