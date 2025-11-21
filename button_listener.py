#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
import os
import sys
import logging
import threading
import datetime
from threading import Timer

# Add current directory to path to import tracker
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from tracker import HabitTracker

# Configuration
BUTTON_PIN = 5  # BCM
LED_PIN = 6     # BCM

# Constants
LONG_PRESS_DURATION = 3.0  # Seconds
STATS_DURATION = 15.0      # Seconds

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def flash_led(times=3, interval=0.1):
    """Flashes the LED in a separate thread."""
    def _flash():
        for _ in range(times):
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(interval)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(interval)
        # Leave LED ON after flashing
        GPIO.output(LED_PIN, GPIO.HIGH)
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
        self.reset_timer = None
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.HIGH) # LED ON for WYAO
        
        # Start 3AM Scheduler
        self.schedule_reset()
        
        # Initial State
        self.tracker.initialize()

    def schedule_reset(self):
        """Schedules the daily reset at 3am."""
        seconds = get_seconds_until_3am()
        logger.info(f"Scheduling reset in {seconds} seconds")
        self.reset_timer = threading.Timer(seconds, self.daily_reset)
        self.reset_timer.start()

    def daily_reset(self):
        """Resets the display to WYAO and reschedules."""
        logger.info("Executing Daily Reset...")
        GPIO.output(LED_PIN, GPIO.HIGH) # Turn LED ON
        self.tracker.initialize()
        self.schedule_reset()

    def show_done_screen(self):
        """Shows the 'You did it' screen."""
        GPIO.output(LED_PIN, GPIO.LOW) # Turn LED OFF immediately
        self.tracker.draw_done_screen()

    def handle_press(self):
        """Log habit, show stats, then show done screen."""
        logger.info("Button Pressed: Logging Habit")
        flash_led(5) # Flash 5 times as requested
        
        # 1. Log and Show Stats
        self.tracker.update()
        
        # 2. Schedule transition to 'Done' screen
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(STATS_DURATION, self.show_done_screen)
        self.timer.start()

    def run(self):
        logger.info("Button Listener Started...")
        try:
            while True:
                # Wait for button press (Active Low)
                if GPIO.input(BUTTON_PIN) == False:
                    # Debounce
                    time.sleep(0.05)
                    if GPIO.input(BUTTON_PIN) == False:
                        self.handle_press()
                        
                        # Wait for release to avoid multiple triggers
                        while GPIO.input(BUTTON_PIN) == False:
                            time.sleep(0.1)
                            
                time.sleep(0.1) # Polling rate
                
        except KeyboardInterrupt:
            logger.info("Exiting...")
        finally:
            if self.timer:
                self.timer.cancel()
            if self.reset_timer:
                self.reset_timer.cancel()
            GPIO.cleanup()

if __name__ == "__main__":
    controller = HabitController()
    controller.run()
