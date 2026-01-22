#!/usr/bin/python3
import os
import sys
import logging
import datetime
import threading
import signal
import time
import RPi.GPIO as GPIO
from threading import Timer

# Add current directory to path to import tracker
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from tracker import HabitTracker

# Configuration
BUTTON_PIN = 5
LED_PIN = 6
STATS_DURATION = 15.0

# Logging setup
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

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
        
        # Setup GPIO with RPi.GPIO (BCM mode)
        GPIO.setmode(GPIO.BCM)
        logger.info(f"Setting up Button on BCM Pin {BUTTON_PIN} and LED on Pin {LED_PIN} (using RPi.GPIO)")
        
        # Button: In with Pull-up
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # LED: Out
        GPIO.setup(LED_PIN, GPIO.OUT)
        
        # Check initial state
        initial_state = "HIGH" if GPIO.input(BUTTON_PIN) else "LOW (GND)"
        logger.info(f"Initial Button State: {initial_state}")
        
        # LED ON for WYAO
        GPIO.output(LED_PIN, GPIO.HIGH)
        
        # Add event detection (Falling edge for pressed)
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=self.handle_event, bouncetime=200)
        
        # Start 3AM Scheduler
        self.schedule_reset()
        
        # Initial State
        self.tracker.initialize()
        
        # Signal handling for clean exit
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

    def cleanup(self, signum=None, frame=None):
        """Performs clean exit."""
        logger.info("Cleaning up...")
        if self.timer:
            self.timer.cancel()
        if self.reset_timer:
            self.reset_timer.cancel()
        
        # Close GPIO pins
        GPIO.cleanup()
        
        # Final display cleanup
        self.tracker.cleanup()
        sys.exit(0)

    def schedule_reset(self):
        """Schedules the daily reset at 3am."""
        seconds = get_seconds_until_3am()
        logger.info(f"Scheduling reset in {seconds} seconds")
        self.reset_timer = Timer(seconds, self.daily_reset)
        self.reset_timer.start()

    def daily_reset(self):
        """Resets the display to WYAO and reschedules."""
        logger.info("Executing Daily Reset...")
        GPIO.output(LED_PIN, GPIO.HIGH)
        self.tracker.initialize()
        self.schedule_reset()

    def show_done_screen(self):
        """Shows the 'You did it' screen."""
        GPIO.output(LED_PIN, GPIO.LOW)
        self.tracker.draw_done_screen()
        
    def flash_led(self):
        """Flashes the LED 5 times significantly."""
        def _flash():
            for _ in range(5):
                GPIO.output(LED_PIN, GPIO.HIGH)
                time.sleep(0.1)
                GPIO.output(LED_PIN, GPIO.LOW)
                time.sleep(0.1)
            # Ensure LED stays ON after flashing
            GPIO.output(LED_PIN, GPIO.HIGH)
            
        threading.Thread(target=_flash).start()

    def handle_event(self, channel):
        """Callback for GPIO event."""
        # Check current state again to be sure (simple debounce check)
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            self.handle_press(channel)

    def handle_press(self, pin_num):
        """Log habit, show stats, then show done screen."""
        logger.info(f"Button Pressed on Pin {pin_num}! Logging Habit...")
        self.flash_led()
        
        # 1. Log and Show Stats
        self.tracker.update()
        
        # 2. Schedule transition to 'Done' screen
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(STATS_DURATION, self.show_done_screen)
        self.timer.start()

if __name__ == "__main__":
    controller = HabitController()
    logger.info("Button Listener Started. Monitoring for presses...")
    try:
        # Simple loop with periodic heartbeat
        while True:
            time.sleep(600) # Sleep 10 mins
            logger.info("Heartbeat: Button Listener is still alive")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting...")
        controller.cleanup()
