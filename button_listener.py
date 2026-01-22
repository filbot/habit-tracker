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
        self._running = True
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(LED_PIN, GPIO.OUT)
        
        # Initial state check
        logger.info(f"Hardware Setup: Button Pin {BUTTON_PIN}, LED Pin {LED_PIN}")
        logger.info(f"Initial Button Reading: {'HIGH' if GPIO.input(BUTTON_PIN) else 'LOW (PRESSED)'}")
        
        # Initial LED State
        GPIO.output(LED_PIN, GPIO.HIGH)
        
        # Start background tasks
        self.schedule_reset()
        
        # Spawn polling thread
        self.poll_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.poll_thread.start()
        
        # Initial Display State
        logger.info("Performing initial display refresh...")
        self.tracker.initialize()
        
        # Signal handling
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

    def _polling_loop(self):
        """Dedicated thread for button polling."""
        logger.info("Button Polling Thread Started.")
        last_state = GPIO.input(BUTTON_PIN)
        
        while self._running:
            current_state = GPIO.input(BUTTON_PIN)
            if current_state == GPIO.LOW and last_state == GPIO.HIGH:
                # Button Transition: Released -> Pressed
                logger.info(f"!! Button Press Detected on Pin {BUTTON_PIN} !!")
                # Handle press in a separate thread so polling doesn't stop
                threading.Thread(target=self.handle_press).start()
            
            last_state = current_state
            time.sleep(0.05) # 50ms polling

    def handle_press(self):
        """Main habit tracking action."""
        # Use a simple lockout to prevent multiple triggers during one update
        logger.info("Logging habit completion...")
        self.flash_led()
        self.tracker.update()
        
        # Schedule back to done screen
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(STATS_DURATION, self.show_done_screen)
        self.timer.start()

    def show_done_screen(self):
        """Shows the 'You did it' screen."""
        logger.info("Transitioning to Done screen.")
        GPIO.output(LED_PIN, GPIO.LOW)
        self.tracker.draw_done_screen()

    def flash_led(self):
        """Flashes the LED 5 times."""
        for _ in range(5):
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(0.1)
        # Stay ON after flash
        GPIO.output(LED_PIN, GPIO.HIGH)

    def schedule_reset(self):
        """Daily 3am reset."""
        seconds = get_seconds_until_3am()
        logger.info(f"Scheduled 3AM reset in {seconds:.2f} seconds")
        self.reset_timer = Timer(seconds, self.daily_reset)
        self.reset_timer.start()

    def daily_reset(self):
        logger.info("Running daily reset...")
        GPIO.output(LED_PIN, GPIO.HIGH)
        self.tracker.initialize()
        self.schedule_reset()

    def cleanup(self, signum=None, frame=None):
        logger.info("Shutting down...")
        self._running = False
        if self.timer: self.timer.cancel()
        if self.reset_timer: self.reset_timer.cancel()
        GPIO.cleanup()
        self.tracker.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    controller = HabitController()
    logger.info("Application is running. Heartbeat every 10 mins.")
    try:
        while True:
            time.sleep(600)
            logger.info("Heartbeat: Service Active")
    except (KeyboardInterrupt, SystemExit):
        controller.cleanup()
