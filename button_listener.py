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
        GPIO.output(LED_PIN, GPIO.LOW)
        
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
        self.tracker.initialize()
        self.schedule_reset()

    def show_done_screen(self):
        """Shows the 'You did it' screen."""
        self.tracker.draw_done_screen()
        # LED is already off, ensuring it stays off

    def handle_short_press(self):
        """Log habit, show stats, then show done screen."""
        logger.info("Short Press: Logging Habit")
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
        logger.info("Long Press: Manual Reset")
        flash_led(5, 0.05) # Rapid flash
        
        if self.timer:
            self.timer.cancel()
            
        self.tracker.initialize()

    def run(self):
        logger.info("Button Listener Started (Polling Mode)...")
        try:
            while True:
                input_state = GPIO.input(BUTTON_PIN)
                
                if input_state == False: # Button Pressed (Active Low)
                    start_time = time.time()
                    
                    # Wait for release or long press threshold
                    while GPIO.input(BUTTON_PIN) == False:
                        time.sleep(0.1)
                        duration = time.time() - start_time
                        if duration >= LONG_PRESS_DURATION:
                            # Long press detected immediately
                            break
                    
                    duration = time.time() - start_time
                    
                    if duration >= LONG_PRESS_DURATION:
                        self.handle_long_press()
                        # Wait for button release to avoid double trigger
                        while GPIO.input(BUTTON_PIN) == False:
                            time.sleep(0.1)
                    else:
                        self.handle_short_press()
                        
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
