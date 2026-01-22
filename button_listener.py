#!/usr/bin/python3
import os
import sys
import logging
import datetime
import threading
import signal
from signal import pause
from gpiozero import Button, LED
from threading import Timer

# Add current directory to path to import tracker
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from tracker import HabitTracker

# Configuration
BUTTON_PIN = 5
LED_PIN = 6
STATS_DURATION = 15.0

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        
        # Setup GPIO
        # Button default pull_up is True
        self.button = Button(BUTTON_PIN)
        self.led = LED(LED_PIN)
        
        self.led.on() # LED ON for WYAO
        
        self.button.when_pressed = self.handle_press
        
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
        self.button.close()
        self.led.close()
        
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
        self.led.on()
        self.tracker.initialize()
        self.schedule_reset()

    def show_done_screen(self):
        """Shows the 'You did it' screen."""
        self.led.off()
        self.tracker.draw_done_screen()
        
    def flash_led(self):
        """Flashes the LED 5 times significantly."""
        def _flash():
            for _ in range(5):
                self.led.on()
                threading.Event().wait(0.1)
                self.led.off()
                threading.Event().wait(0.1)
            # Ensure LED stays ON after flashing
            self.led.on()
            
        threading.Thread(target=_flash).start()

    def handle_press(self):
        """Log habit, show stats, then show done screen."""
        logger.info("Button Pressed: Logging Habit")
        self.flash_led()
        
        # 1. Log and Show Stats
        # Run update which talks to EPD
        self.tracker.update()
        
        # 2. Schedule transition to 'Done' screen
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(STATS_DURATION, self.show_done_screen)
        self.timer.start()

if __name__ == "__main__":
    controller = HabitController()
    logger.info("Button Listener Started...")
    try:
        pause()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting...")
