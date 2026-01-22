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
# Set up a single unified logger configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Reduce tracker log level to avoid noise if needed, but keep it DEBUG for now
# logging.getLogger('tracker').setLevel(logging.INFO)

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
        # Waveshare hats usually have 4 buttons: S1=5, S2=6, S3=13, S4=19
        # They pull to GND when pressed (Active LOW).
        self.pins = [5, 6, 13, 19]
        self.buttons = []
        
        logger.info(f"Initializing buttons on BCM pins: {self.pins}")
        for pin in self.pins:
            try:
                btn = Button(pin, pull_up=True, bounce_time=0.05)
                # Assign the same handler but pass the pin number for identification
                btn.when_pressed = lambda b=btn: self.handle_press(b.pin.number)
                btn.when_released = lambda b=btn: logger.debug(f"Button {b.pin.number} Released")
                self.buttons.append(btn)
                logger.debug(f"Monitoring pin {pin} (Current State: {'HIGH' if btn.is_pressed else 'LOW'})")
            except Exception as e:
                logger.error(f"Failed to setup pin {pin}: {e}")

        self.led = LED(LED_PIN)
        self.led.on() # LED ON for WYAO
        
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
        for btn in self.buttons:
            btn.close()
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

    def handle_press(self, pin_num):
        """Log habit, show stats, then show done screen."""
        logger.info(f"Button Pressed on Pin {pin_num}! Logging Habit...")
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
    logger.info("Button Listener Started. Monitoring for presses...")
    try:
        # Simple loop with periodic heartbeat to verify service is alive
        while True:
            threading.Event().wait(600) # Heartbeat every 10 mins
            logger.info("Heartbeat: Button Listener is still alive")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Exiting...")
        controller.cleanup()
