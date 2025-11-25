#!/usr/bin/python3
# -*- coding:utf-8 -*-
import sys
import os
import time
import logging
import json
import argparse
import random
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

import database

# Add current directory to path
libdir = os.path.dirname(os.path.realpath(__file__))
if os.path.exists(libdir):
    sys.path.append(libdir)

import epd2in13b_V4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        return ImageFont.load_default()

def fit_text(draw, text, max_width, max_height):
    size = 10
    font = get_font(size)
    while True:
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width >= max_width or height >= max_height:
            return get_font(size - 1)
        size += 1
        font = get_font(size)

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
    image_red = Image.new('1', (width, height), 255)
    
    draw_black = ImageDraw.Draw(image_black)
    draw_red = ImageDraw.Draw(image_red)
    
    # Calculate Metrics from Database
    history = database.get_all_logs()
    offset = database.get_offset()
    
    vol = get_weekly_volume(history)
    streak = get_weekly_streak(history)
    total = len(history) + offset
    
    # Layout Constants
    top_height = height // 2
    padding = 10
    box_y_start = top_height + padding
    box_y_end = height - padding
    box_height = box_y_end - box_y_start
    
    # Calculate box width (3 boxes, 4 gaps of padding)
    total_gap = 4 * padding
    available_width = width - total_gap
    box_width = available_width // 3
    
    # --- Top Half: Message (White) ---
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
    
    # Center message in top half manually
    bbox = font_msg.getbbox(msg)
    msg_w = bbox[2] - bbox[0]
    msg_h = bbox[3] - bbox[1]
    msg_x = (width - msg_w) // 2
    msg_y = (top_height - msg_h) // 2
    
    draw_black.text((msg_x, msg_y), msg, font=font_msg, fill=0)
    
    # --- Bottom Half: Stats Boxes (White on Black) ---
    stats_data = [
        ("This Week", str(vol)),
        ("Streak", str(streak)),
        ("Total", str(total))
    ]
    
    font_label = get_font(12)
    font_value = get_font(24)
    
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
        label_y = box_y_start + 5
        draw_black.text((l_x, label_y), label, font=font_label, fill=0)
        
        # Draw Value (Center/Bottom of box)
        bbox_v = font_value.getbbox(value)
        v_w = bbox_v[2] - bbox_v[0]
        v_x = box_center_x - (v_w // 2)
        value_y = box_y_start + 25
        draw_black.text((v_x, value_y), value, font=font_value, fill=0)
    
    epd.display(epd.getbuffer(image_black), epd.getbuffer(image_red))

def draw_wyao(epd):
    logger.info("Drawing Init State (WYAO)")
    width = epd.height
    height = epd.width
    
    # White background (255)
    image_black = Image.new('1', (width, height), 255) 
    image_red = Image.new('1', (width, height), 255) # Transparent
    
    draw_black = ImageDraw.Draw(image_black)
    draw_red = ImageDraw.Draw(image_red)
    
    text = "WYAO"
    padding = 10
    available_width = width - (2 * padding)
    available_height = height - (2 * padding)
    
    # 1. Find the right font size
    font = fit_text(draw_black, text, available_width, available_height)
    
    # 2. Calculate total width to center
    total_width = 0
    char_widths = []
    for char in text:
        l = draw_black.textlength(char, font=font)
        char_widths.append(l)
        total_width += l
        
    start_x = (width - total_width) // 2
    y = height // 2
    
    # 3. Draw characters
    current_x = start_x
    for i, char in enumerate(text):
        if char == 'A':
            # Red 'A' on Red Layer (0 = Red)
            draw_red.text((current_x, y), char, font=font, fill=0, anchor="lm")
        else:
            # Black 'W', 'Y', 'O' on Black Layer (0 = Black)
            draw_black.text((current_x, y), char, font=font, fill=0, anchor="lm")
        
        current_x += char_widths[i]
        
    epd.display(epd.getbuffer(image_black), epd.getbuffer(image_red))

def draw_done_screen(epd):
    logger.info("Drawing Done Screen")
    width = epd.height
    height = epd.width
    
    # Black Background (0)
    image_black = Image.new('1', (width, height), 0)
    image_red = Image.new('1', (width, height), 255)
    
    draw_black = ImageDraw.Draw(image_black)
    
    font = get_font(40)
    text = "YOU DID IT"
    
    # Draw White text (1) on Black background
    # Center text using anchor="mm" (Middle-Middle)
    x = width // 2
    y = height // 2
    
    # Nudge y up slightly because 'mm' centers based on full line height/bbox
    # and for all-caps, visual center is slightly higher than mathematical center
    # if the font has descender space.
    # But let's try pure 'mm' first as it's standard.
    draw_black.text((x, y), text, font=font, fill=1, anchor="mm")
    
    epd.display(epd.getbuffer(image_black), epd.getbuffer(image_red))

class HabitTracker:
    def __init__(self):
        self.epd = epd2in13b_V4.EPD()
        logger.info("Init")
        self.epd.init()
        # Ensure DB is initialized
        database.init_db()
        
    def initialize(self):
        self.epd.init()
        draw_wyao(self.epd)
        self.sleep()

    def update(self):
        self.epd.init() # Ensure awake and SPI open
        # Update stats in DB
        database.add_log()
        
        # Show stats
        draw_stats(self.epd)
        
    def draw_done_screen(self):
        self.epd.init()
        draw_done_screen(self.epd)
        self.sleep()
        
    def reset(self):
        self.epd.init() # Ensure awake and SPI open
        # Revert to WYAO
        draw_wyao(self.epd)
        self.sleep()
        
    def sleep(self):
        logger.info("Goto Sleep...")
        self.epd.sleep()

def main():
    parser = argparse.ArgumentParser(description='Habit Tracker Display')
    parser.add_argument('--init', action='store_true', help='Initialize display to WYAO state')
    args = parser.parse_args()

    try:
        tracker = HabitTracker()
        
        if args.init:
            tracker.reset()
            tracker.sleep()
        else:
            tracker.update()
            
            # Wait 15 seconds
            logger.info("Waiting 15 seconds...")
            time.sleep(15)
            
            tracker.reset()
            tracker.sleep()
        
    except Exception as e:
        logger.error(f"Unhandled Exception: {e}", exc_info=True)
    except KeyboardInterrupt:    
        logger.info("ctrl + c:")
        epd2in13b_V4.epdconfig.module_exit()
        exit()

if __name__ == "__main__":
    main()
