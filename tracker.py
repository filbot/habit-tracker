#!/usr/bin/python3
# -*- coding:utf-8 -*-
import sys
import os
import time
import logging
import json
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

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

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

_font_cache = {}

def get_font(size):
    font_file = get_font_file()
    if font_file:
        cache_key = (font_file, size)
        if cache_key in _font_cache:
            return _font_cache[cache_key]
        try:
            font = ImageFont.truetype(font_file, size)
            _font_cache[cache_key] = font
            return font
        except Exception as e:
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

def draw_stats(epd):
    logger.info("Drawing Update State")
    width = epd.height
    height = epd.width
    
    # White background (255)
    image_black = Image.new('1', (width, height), 255) 
    
    draw_black = ImageDraw.Draw(image_black)
    
    # Calculate Metrics from Database
    # Only fetch last ~53 weeks for streak/volume calculation
    since = (datetime.now() - timedelta(weeks=53)).isoformat()
    recent_history = database.get_logs_since(since)
    offset = database.get_offset()

    vol = get_weekly_volume(recent_history)
    streak = get_weekly_streak(recent_history)
    total = database.get_log_count() + offset
    
    # Layout Constants
    padding = 10
    
    # Fonts
    font_label = get_font(12)
    font_value = get_font(24)
    
    # Calculate Box Height needed
    # Label (12) + Gap (5) + Value (24) + Inner Padding (5 top + 5 bottom)
    label_h = 14 # slightly more than font size to be safe
    value_h = 28
    inner_gap = 5
    inner_padding = 5
    
    box_height = inner_padding + label_h + inner_gap + value_h + inner_padding
    
    # Bottom area
    box_y_end = height - padding
    box_y_start = box_y_end - box_height
    
    # Calculate box width (3 boxes, 4 gaps of padding)
    total_gap = 4 * padding
    available_width = width - total_gap
    box_width = available_width // 3
    
    # --- Top Half: Message (White) ---
    # Available height for message
    # From 0 to box_y_start - padding
    msg_area_height = box_y_start - padding
    msg_area_center_y = msg_area_height // 2
    
    messages = [
        "Keep it up!",
        "Great job!",
        "You got this!",
        "Don't stop!",
        "Crushing it!",
        "Let's go!",
        "Nice work!",
        "Way to go!"
    ]
    msg = random.choice(messages)
    font_msg = get_font(28)
    
    # Center message
    bbox = font_msg.getbbox(msg)
    msg_w = bbox[2] - bbox[0]
    msg_h = bbox[3] - bbox[1]
    msg_x = (width - msg_w) // 2
    msg_y = msg_area_center_y - (msg_h // 2)
    
    draw_black.text((msg_x, msg_y), msg, font=font_msg, fill=0)
    
    # --- Bottom Half: Stats Boxes (White on Black) ---
    stats_data = [
        ("This Week", str(vol)),
        ("Streak", str(streak)),
        ("Total", str(total))
    ]
    
    for i, (label, value) in enumerate(stats_data):
        # Calculate box coordinates
        x_start = padding + (i * (box_width + padding))
        x_end = x_start + box_width
        
        # Draw Box Outline (White=0)
        draw_black.rectangle([x_start, box_y_start, x_end, box_y_end], outline=0, width=1)
        
        # Center of box
        box_center_x = x_start + (box_width // 2)
        
        # Draw Label (Top of box)
        bbox_l = font_label.getbbox(label)
        l_w = bbox_l[2] - bbox_l[0]
        l_x = box_center_x - (l_w // 2)
        label_y = box_y_start + inner_padding
        draw_black.text((l_x, label_y), label, font=font_label, fill=0)
        
        # Draw Value (Bottom of box)
        bbox_v = font_value.getbbox(value)
        v_w = bbox_v[2] - bbox_v[0]
        v_x = box_center_x - (v_w // 2)
        # Position value below label + gap
        value_y = label_y + label_h + inner_gap
        draw_black.text((v_x, value_y), value, font=font_value, fill=0)
    
    epd.display(epd.getbuffer(image_black))

def draw_wyao(epd):
    logger.info("Drawing Init State (WYAO)")
    width = epd.height
    height = epd.width
    
    # White background (255)
    image_black = Image.new('1', (width, height), 255) 
    
    draw_black = ImageDraw.Draw(image_black)
    
    text = "WYAO"
    padding = 5
    available_width = width - (2 * padding)
    available_height = height - (2 * padding)
    
    # 1. Find the right font size
    font = fit_text(draw_black, text, available_width, available_height)
    
    # 2. Draw centered using anchor "mm"
    # This is much more reliable than summing character widths manually
    x = width // 2
    y = height // 2
    
    draw_black.text((x, y), text, font=font, fill=0, anchor="mm")

    epd.display(epd.getbuffer(image_black))

def draw_done_screen(epd):
    logger.info("Drawing Done Screen")
    width = epd.height
    height = epd.width
    
    # Black Background (0)
    image_black = Image.new('1', (width, height), 0)
    
    draw_black = ImageDraw.Draw(image_black)
    
    font = get_font(40)
    text = "DONE"
    
    # Draw White text (1) on Black background
    # Center text using anchor="mm" (Middle-Middle)
    x = width // 2
    y = height // 2
    
    # Nudge y up slightly because 'mm' centers based on full line height/bbox
    # and for all-caps, visual center is slightly higher than mathematical center
    # if the font has descender space.
    # But let's try pure 'mm' first as it's standard.
    draw_black.text((x, y), text, font=font, fill=1, anchor="mm")

    epd.display(epd.getbuffer(image_black))


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
            except TimeoutError as e:
                logger.error(f"Display timeout: {e}")
                return None
            finally:
                self.sleep()

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

            # Wait 15 seconds
            logger.info("Waiting 15 seconds...")
            time.sleep(15)

            tracker.reset()

    except KeyboardInterrupt:
        logger.info("ctrl + c:")
    except Exception as e:
        logger.error(f"Unhandled Exception: {e}", exc_info=True)
    finally:
        tracker.cleanup()

if __name__ == "__main__":
    main()
