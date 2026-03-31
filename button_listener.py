#!/usr/bin/python3
import os
import sys
import logging
import datetime
import threading
import signal
import time
from logging.handlers import RotatingFileHandler
from gpiozero import Button, LED
from threading import Timer

# Add current directory to path to import tracker
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from tracker import HabitTracker

# Configuration
BUTTON_PIN = 5
LED_PIN = 6
STATS_DURATION = 15.0
POLL_INTERVAL_S = 0.05
HEARTBEAT_INTERVAL_S = 600
FLASH_COUNT = 5
FLASH_PERIOD_S = 0.1

# Logging setup — INFO level with rotation to prevent disk fill
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
LOG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'habit-tracker.log')

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

def get_seconds_until_3am():
    """Calculates seconds until the next 3:00 AM, clamped for DST safety."""
    now = datetime.datetime.now()
    next_3am = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if now >= next_3am:
        next_3am += datetime.timedelta(days=1)
    seconds = (next_3am - now).total_seconds()
    # Clamp to [1 hour, 25 hours] to handle DST edge cases
    return max(3600, min(seconds, 90000))

class HabitController:
    def __init__(self):
        self.tracker = HabitTracker()
        self.timer = None
        self.reset_timer = None
        self._shutdown_event = threading.Event()
        self._timer_lock = threading.Lock()
        self._press_lock = threading.Lock()
        self._cleaned_up = False

        # Setup GPIO with gpiozero
        logger.info(f"Hardware Setup: Button Pin {BUTTON_PIN}, LED Pin {LED_PIN}")
        self.button = Button(BUTTON_PIN, pull_up=True)
        self.led = LED(LED_PIN)

        # Initial state check
        logger.info(f"Initial Button Reading: {'HIGH' if not self.button.is_pressed else 'LOW (PRESSED)'}")

        # Initial LED State
        self.led.on()

        # Start background tasks
        self.schedule_reset()

        # Spawn polling thread
        self.poll_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.poll_thread.start()

        # Initial Display State
        logger.info("Performing initial display refresh...")
        self.tracker.initialize()

        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Signal handler — just sets shutdown event, cleanup happens in main loop."""
        logger.info(f"Received signal {signum}, requesting shutdown...")
        self._shutdown_event.set()

    def _polling_loop(self):
        """Dedicated thread for button polling."""
        logger.info("Button Polling Thread Started.")
        last_state = self.button.is_pressed

        while not self._shutdown_event.is_set():
            try:
                current_state = self.button.is_pressed
                if current_state and not last_state:
                    # Button Transition: Released -> Pressed
                    logger.info(f"Button Press Detected on Pin {BUTTON_PIN}")
                    if self._press_lock.acquire(blocking=False):
                        threading.Thread(target=self._guarded_press, daemon=True).start()
                    else:
                        logger.debug("Press already in progress, ignoring")
                last_state = current_state
            except Exception as e:
                logger.error(f"Polling error: {e}", exc_info=True)
                time.sleep(1)  # backoff before retry
            time.sleep(POLL_INTERVAL_S)

    def _guarded_press(self):
        """Wrapper ensuring press lock is always released."""
        try:
            self.handle_press()
        finally:
            self._press_lock.release()

    def handle_press(self):
        """Main habit tracking action."""
        try:
            logger.info("Logging habit completion...")
            self.flash_led()
            self.tracker.update()

            # Schedule transition to done screen
            with self._timer_lock:
                if self.timer:
                    self.timer.cancel()
                self.timer = Timer(STATS_DURATION, self.show_done_screen)
                self.timer.start()
        except Exception as e:
            logger.error(f"handle_press failed: {e}", exc_info=True)

    def show_done_screen(self):
        """Shows the 'You did it' screen."""
        logger.info("Transitioning to Done screen.")
        self.led.off()
        self.tracker.draw_done_screen()

    def flash_led(self):
        """Flashes the LED."""
        for _ in range(FLASH_COUNT):
            self.led.on()
            time.sleep(FLASH_PERIOD_S)
            self.led.off()
            time.sleep(FLASH_PERIOD_S)
        # Stay ON after flash
        self.led.on()

    def schedule_reset(self):
        """Daily 3am reset."""
        seconds = get_seconds_until_3am()
        logger.info(f"Scheduled 3AM reset in {seconds:.0f} seconds")
        with self._timer_lock:
            self.reset_timer = Timer(seconds, self.daily_reset)
            self.reset_timer.start()

    def daily_reset(self):
        logger.info("Running daily reset...")
        try:
            self.led.on()
            self.tracker.initialize()
        except Exception as e:
            logger.error(f"Daily reset failed: {e}", exc_info=True)
        finally:
            self.schedule_reset()

    def cleanup(self, signum=None, frame=None):
        if self._cleaned_up:
            return
        self._cleaned_up = True
        logger.info("Shutting down...")
        self._shutdown_event.set()

        with self._timer_lock:
            if self.timer:
                self.timer.cancel()
                self.timer.join(timeout=2)
            if self.reset_timer:
                self.reset_timer.cancel()
                self.reset_timer.join(timeout=2)

        self.button.close()
        self.led.close()
        self.tracker.cleanup()

if __name__ == "__main__":
    controller = HabitController()
    logger.info("Application is running. Heartbeat every 10 mins.")
    try:
        while not controller._shutdown_event.wait(timeout=HEARTBEAT_INTERVAL_S):
            logger.info("Heartbeat: Service Active")
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        controller.cleanup()
