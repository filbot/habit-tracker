#!/usr/bin/python3
# -*- coding:utf-8 -*-
import sys
import os
import time
import logging
import json
import argparse
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import traceback

# Add current directory to path
libdir = os.path.dirname(os.path.realpath(__file__))
if os.path.exists(libdir):
    sys.path.append(libdir)

import epd2in13b_V4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATS_FILE = os.path.join(libdir, "stats.json")
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                data = json.load(f)
                # Migration from old format
                if 'count' in data and 'history' not in data:
                    return {
                        'history': [],
                        'offset': data['count']
                    }
                # Ensure defaults
                if 'history' not in data:
                    data['history'] = []
                if 'offset' not in data:
                    data['offset'] = 0
                return data
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
    return {"history": [], "offset": 0}

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f)
    except Exception as e:
        logger.error(f"Failed to save stats: {e}")

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

def draw_wyao(epd):
    logger.info("Drawing Init State (WYAO)")
    width = epd.height
    height = epd.width
    
    # Black background (0), White text (1)
    Himage_black = Image.new('1', (width, height), 0) 
    Himage_red = Image.new('1', (width, height), 255) # Transparent
    
    draw_black = ImageDraw.Draw(Himage_black)
    
    text = "WYAO"
    padding = 5
    available_width = width - (2 * padding)
    available_height = height - (2 * padding)
    
    font = fit_text(draw_black, text, available_width, available_height)
    
    # Center text using anchor
    x = width // 2
    y = height // 2
    draw_black.text((x, y), text, font=font, fill=1, anchor="mm")
    
    epd.display(epd.getbuffer(Himage_black), epd.getbuffer(Himage_red))

def draw_stats(epd, stats):
    logger.info("Drawing Update State")
    width = epd.height
    height = epd.width
    
    # White background (255)
    Himage_black = Image.new('1', (width, height), 255) 
    Himage_red = Image.new('1', (width, height), 255)
    
    draw_black = ImageDraw.Draw(Himage_black)
    draw_red = ImageDraw.Draw(Himage_red)
    
    # Calculate Metrics
    history = stats['history']
    offset = stats['offset']
    
    vol = get_weekly_volume(history)
    streak = get_weekly_streak(history)
    total = len(history) + offset
    
    # Layout
    # Line 1: Week: X (Red)
    # Line 2: Streak: Y (Black)
    # Line 3: Total: Z (Black)
    
    font_large = get_font(28)
    font_small = get_font(20)
    
    # Line 1: Volume (Red)
    text_vol = f"Week: {vol}"
    draw_red.text((10, 10), text_vol, font=font_large, fill=0)
    
    # Line 2: Streak (Black)
    text_streak = f"Streak: {streak} wks"
    draw_black.text((10, 50), text_streak, font=font_large, fill=0)
    
    # Line 3: Total (Black) - Smaller
    text_total = f"Total: {total}"
    draw_black.text((10, 90), text_total, font=font_small, fill=0)
    
    epd.display(epd.getbuffer(Himage_black), epd.getbuffer(Himage_red))

def main():
    parser = argparse.ArgumentParser(description='Habit Tracker Display')
    parser.add_argument('--init', action='store_true', help='Initialize display to WYAO state')
    args = parser.parse_args()

    try:
        epd = epd2in13b_V4.EPD()
        logger.info("Init and Clear")
        epd.init()
        epd.clear()
        
        if args.init:
            draw_wyao(epd)
        else:
            # Update stats
            stats = load_stats()
            stats['history'].append(datetime.now().isoformat())
            save_stats(stats)
            
            # Show stats
            draw_stats(epd, stats)
            
            # Wait 60 seconds
            logger.info("Waiting 60 seconds...")
            time.sleep(60)
            
            # Revert to WYAO
            draw_wyao(epd)

        logger.info("Goto Sleep...")
        epd.sleep()
        
    except IOError as e:
        logger.info(e)
    except KeyboardInterrupt:    
        logger.info("ctrl + c:")
        epd2in13b_V4.epdconfig.module_exit()
        exit()

if __name__ == "__main__":
    main()
