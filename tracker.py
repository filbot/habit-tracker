#!/usr/bin/python3
# -*- coding:utf-8 -*-
import sys
import os
import time
import logging
import functools
import argparse
import random
import threading
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

import database

# Add lib to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in13_V4

logger = logging.getLogger(__name__)

FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

MOTIVATIONAL_MESSAGES = (
    "Keep it up!", "Great job!", "You got this!", "Don't stop!",
    "Crushing it!", "Let's go!", "Nice work!", "Way to go!",
)

# Bound history queries to ~1 year; matches api.RECENT_HISTORY_WEEKS.
RECENT_HISTORY_WEEKS = 53

# Display layout
LAYOUT_PADDING = 10
LAYOUT_INNER_GAP = 5
LAYOUT_INNER_PADDING = 5
LAYOUT_LABEL_HEIGHT = 14   # slightly larger than font size for safety
LAYOUT_VALUE_HEIGHT = 28
STATS_BOX_COUNT = 3

# Font sizes
FONT_SIZE_LABEL = 12
FONT_SIZE_VALUE = 24
FONT_SIZE_MESSAGE = 28
FONT_SIZE_DONE = 40

# Display state durations
STATS_DISPLAY_SECONDS = 15

# Pillow fill values for 1-bit images
COLOR_BLACK = 0
COLOR_WHITE = 255
COLOR_BLACK_FILL = 0
COLOR_WHITE_FILL = 1

def get_font_file():
    """Finds a valid TrueType font file on the system."""
    # 1. Check for a bundled project font (Most reliable)
    bundled_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets', 'font.ttf')
    if os.path.exists(bundled_path):
        return bundled_path

    # 2. Check standard system paths (Fallback)
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        FONT_PATH
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

@functools.lru_cache(maxsize=32)
def _load_truetype(font_file, size):
    return ImageFont.truetype(font_file, size)

def get_font(size):
    font_file = get_font_file()
    if font_file:
        try:
            return _load_truetype(font_file, size)
        except OSError as e:
            logger.warning(f"Failed to load font '{font_file}' at size {size}: {e}")
    return ImageFont.load_default()

def fit_text(draw, text, max_width, max_height):
    font_file = get_font_file()
    if not font_file:
        logger.warning("No TTF font found, falling back to default tiny font.")
        return ImageFont.load_default()

    # Binary search for the largest font size that fits
    lo, hi = 10, 250
    best_size = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        test_font = get_font(mid)
        bbox = draw.textbbox((0, 0), text, font=test_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        if w <= max_width and h <= max_height:
            best_size = mid
            lo = mid + 1
        else:
            hi = mid - 1

    logger.debug(f"Selected font size: {best_size} for text '{text}'")
    return get_font(best_size)

def get_weekly_volume(history):
    now = datetime.now()
    current_year, current_week, _ = now.isocalendar()
    
    count = 0
    for ts in history:
        dt = datetime.fromisoformat(ts)
        year, week, _ = dt.isocalendar()
        if year == current_year and week == current_week:
            count += 1
    return count

def get_weekly_streak(history):
    if not history:
        return 0
        
    # Get set of (year, week) for all entries
    weeks = set()
    for ts in history:
        dt = datetime.fromisoformat(ts)
        weeks.add(dt.isocalendar()[:2])
    
    if not weeks:
        return 0

    now = datetime.now()
    current_year, current_week, _ = now.isocalendar()
    
    streak = 0
    # Check backwards from current week
    # If current week has activity, streak starts at 1. 
    # If not, check previous week (maybe they haven't done it yet this week, but streak is still alive? 
    # Usually streak implies contiguous blocks. Let's be strict: if you miss a week, streak resets.
    # But for "current streak", if I did it last week and today is Monday, my streak is still alive.
    
    # Let's check if current week is present
    check_year, check_week = current_year, current_week
    
    # If current week is empty, check if last week was active to decide if streak is 0 or just pending
    if (check_year, check_week) not in weeks:
        # Move back one week
        d = datetime.now() - timedelta(days=7)
        check_year, check_week = d.isocalendar()[:2]
        if (check_year, check_week) not in weeks:
            return 0 # No activity this week or last week
            
    # Now count backwards
    while (check_year, check_week) in weeks:
        streak += 1
        # Move back one week
        # Simple way: create a date in that week and subtract 7 days
        # ISO weeks are tricky to iterate mathematically without date objects
        # Let's find a date in the current check_week
        d = datetime.fromisocalendar(check_year, check_week, 1) # Monday of that week
        d = d - timedelta(days=7)
        check_year, check_week = d.isocalendar()[:2]
        
    return streak

def _fetch_stats() -> tuple[int, int, int]:
    """Returns (weekly_volume, weekly_streak, total)."""
    since = (datetime.now() - timedelta(weeks=RECENT_HISTORY_WEEKS)).isoformat()
    recent_history = database.get_logs_since(since)
    offset = database.get_offset()
    return (
        get_weekly_volume(recent_history),
        get_weekly_streak(recent_history),
        database.get_log_count() + offset,
    )


def _draw_centered_message(draw, width: int, max_y: int, message: str) -> None:
    """Draw a motivational message horizontally and vertically centered above max_y."""
    font = get_font(FONT_SIZE_MESSAGE)
    bbox = font.getbbox(message)
    msg_w = bbox[2] - bbox[0]
    msg_h = bbox[3] - bbox[1]
    msg_x = (width - msg_w) // 2
    msg_y = (max_y // 2) - (msg_h // 2)
    draw.text((msg_x, msg_y), message, font=font, fill=COLOR_BLACK_FILL)


def _draw_stats_box(draw, x_start: int, y_start: int, box_width: int, box_height: int,
                    label: str, value: str, font_label, font_value) -> None:
    """Draw one labelled stats box."""
    draw.rectangle(
        [x_start, y_start, x_start + box_width, y_start + box_height],
        outline=COLOR_BLACK_FILL,
        width=1,
    )
    box_center_x = x_start + (box_width // 2)

    label_y = y_start + LAYOUT_INNER_PADDING
    bbox_l = font_label.getbbox(label)
    l_x = box_center_x - ((bbox_l[2] - bbox_l[0]) // 2)
    draw.text((l_x, label_y), label, font=font_label, fill=COLOR_BLACK_FILL)

    value_y = label_y + LAYOUT_LABEL_HEIGHT + LAYOUT_INNER_GAP
    bbox_v = font_value.getbbox(value)
    v_x = box_center_x - ((bbox_v[2] - bbox_v[0]) // 2)
    draw.text((v_x, value_y), value, font=font_value, fill=COLOR_BLACK_FILL)


def draw_stats(epd):
    logger.info("Drawing Update State")
    width = epd.height
    height = epd.width

    image = Image.new('1', (width, height), COLOR_WHITE)
    draw = ImageDraw.Draw(image)

    vol, streak, total = _fetch_stats()

    font_label = get_font(FONT_SIZE_LABEL)
    font_value = get_font(FONT_SIZE_VALUE)

    box_height = (LAYOUT_INNER_PADDING + LAYOUT_LABEL_HEIGHT
                  + LAYOUT_INNER_GAP + LAYOUT_VALUE_HEIGHT + LAYOUT_INNER_PADDING)
    box_y_end = height - LAYOUT_PADDING
    box_y_start = box_y_end - box_height

    total_gap = (STATS_BOX_COUNT + 1) * LAYOUT_PADDING
    box_width = (width - total_gap) // STATS_BOX_COUNT

    msg_area_height = box_y_start - LAYOUT_PADDING
    _draw_centered_message(draw, width, msg_area_height, random.choice(MOTIVATIONAL_MESSAGES))

    stats_data = (
        ("This Week", str(vol)),
        ("Streak", str(streak)),
        ("Total", str(total)),
    )
    for i, (label, value) in enumerate(stats_data):
        x_start = LAYOUT_PADDING + (i * (box_width + LAYOUT_PADDING))
        _draw_stats_box(draw, x_start, box_y_start, box_width, box_height,
                        label, value, font_label, font_value)

    epd.display(epd.getbuffer(image))

WYAO_PADDING = 5


def draw_wyao(epd):
    logger.info("Drawing Init State (WYAO)")
    width = epd.height
    height = epd.width

    image = Image.new('1', (width, height), COLOR_WHITE)
    draw = ImageDraw.Draw(image)

    text = "WYAO"
    available_width = width - (2 * WYAO_PADDING)
    available_height = height - (2 * WYAO_PADDING)

    font = fit_text(draw, text, available_width, available_height)
    draw.text((width // 2, height // 2), text, font=font, fill=COLOR_BLACK_FILL, anchor="mm")

    epd.display(epd.getbuffer(image))


def draw_done_screen(epd):
    logger.info("Drawing Done Screen")
    width = epd.height
    height = epd.width

    image = Image.new('1', (width, height), COLOR_BLACK)
    draw = ImageDraw.Draw(image)

    font = get_font(FONT_SIZE_DONE)
    draw.text((width // 2, height // 2), "DONE", font=font, fill=COLOR_WHITE_FILL, anchor="mm")

    epd.display(epd.getbuffer(image))


class HabitTracker:
    def __init__(self):
        self.epd = epd2in13_V4.EPD()
        self.lock = threading.RLock()
        logger.info("HabitTracker Initialized")
        # Ensure DB is initialized
        database.init_db()
        
    def _with_display(self, func, *args, **kwargs):
        """Ensures display is initialized before and sleeps after."""
        with self.lock:
            try:
                ret = self.epd.init()
                if ret != 0:
                    logger.error("Display init failed (SPI/GPIO unavailable)")
                    return None
                result = func(self.epd, *args, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Display operation failed: {e}", exc_info=True)
                return None
            finally:
                try:
                    self.sleep()
                except Exception as e:
                    logger.error(f"Display sleep failed: {e}", exc_info=True)

    def initialize(self):
        self._with_display(draw_wyao)

    def update(self):
        # Update stats in DB
        database.add_log()
        # Show stats on display
        self._with_display(draw_stats)
        
    def draw_done_screen(self):
        self._with_display(draw_done_screen)
        
    def reset(self):
        # Revert to WYAO
        self._with_display(draw_wyao)
        
    def sleep(self):
        logger.info("Display Sleeping...")
        self.epd.sleep()
        
    def cleanup(self):
        """Final cleanup of GPIO."""
        with self.lock:
            logger.info("Cleaning up GPIO...")
            epd2in13_V4.epdconfig.module_exit()

def main():
    parser = argparse.ArgumentParser(description='Habit Tracker Display')
    parser.add_argument('--init', action='store_true', help='Initialize display to WYAO state')
    args = parser.parse_args()

    tracker = HabitTracker()
    try:
        if args.init:
            tracker.reset()
        else:
            tracker.update()

            logger.info("Waiting %d seconds...", STATS_DISPLAY_SECONDS)
            time.sleep(STATS_DISPLAY_SECONDS)

            tracker.reset()

    except KeyboardInterrupt:
        logger.info("ctrl + c:")
    except Exception as e:
        logger.error(f"Unhandled Exception: {e}", exc_info=True)
    finally:
        tracker.cleanup()

if __name__ == "__main__":
    main()
