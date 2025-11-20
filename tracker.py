#!/usr/bin/python3
# -*- coding:utf-8 -*-
import sys
import os
import time
import logging
import json
import argparse
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
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
    return {"count": 0}

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

def main():
    parser = argparse.ArgumentParser(description='Habit Tracker Display')
    parser.add_argument('--init', action='store_true', help='Initialize display to WYAO state')
    args = parser.parse_args()

    try:
        epd = epd2in13b_V4.EPD()
        logger.info("Init and Clear")
        epd.init()
        epd.clear()

        # Display dimensions (Landscape: 250x122)
        width = epd.height # 250
        height = epd.width # 122
        
        if args.init:
            logger.info("Drawing Init State (WYAO)")
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
            
        else:
            logger.info("Drawing Update State")
            stats = load_stats()
            stats['count'] += 1
            save_stats(stats)
            
            # White background (255)
            Himage_black = Image.new('1', (width, height), 255) 
            Himage_red = Image.new('1', (width, height), 255)
            
            draw_black = ImageDraw.Draw(Himage_black)
            draw_red = ImageDraw.Draw(Himage_red)
            
            msg = "Keep it up!"
            count_str = str(stats['count'])
            
            # Fonts
            font_msg = get_font(30)
            font_count = get_font(60)
            
            # Draw Message (Red)
            bbox_msg = draw_red.textbbox((0, 0), msg, font=font_msg)
            w_msg = bbox_msg[2] - bbox_msg[0]
            x_msg = (width - w_msg) // 2
            y_msg = 10
            draw_red.text((x_msg, y_msg), msg, font=font_msg, fill=0)
            
            # Draw Count (Black)
            bbox_count = draw_black.textbbox((0, 0), count_str, font=font_count)
            w_count = bbox_count[2] - bbox_count[0]
            x_count = (width - w_count) // 2
            y_count = y_msg + 40 # Offset
            draw_black.text((x_count, y_count), count_str, font=font_count, fill=0)
            
            epd.display(epd.getbuffer(Himage_black), epd.getbuffer(Himage_red))

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
