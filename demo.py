#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import time
import logging
from PIL import Image, ImageDraw, ImageFont
import traceback

# Add current directory to path so we can import the driver
libdir = os.path.dirname(os.path.realpath(__file__))
if os.path.exists(libdir):
    sys.path.append(libdir)

import epd2in13b_V4

logging.basicConfig(level=logging.DEBUG)

try:
    logging.info("epd2in13b_V4 Demo")

    epd = epd2in13b_V4.EPD()
    logging.info("init and Clear")
    epd.init()
    epd.clear()
    time.sleep(1)

    # Drawing on the image
    logging.info("Drawing")
    
    # The display is 122x250 (Portrait)
    # We will create an image in Landscape (250x122) and the driver will rotate it.
    # For black image: 0 is black, 1 is white (255)
    # For red image: 0 is red, 1 is white (255)
    
    Himage_black = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame
    Himage_red = Image.new('1', (epd.height, epd.width), 255)  # 255: clear the frame
    
    draw_black = ImageDraw.Draw(Himage_black)
    draw_red = ImageDraw.Draw(Himage_red)

    # Draw some shapes
    # Rectangle on black layer
    draw_black.rectangle((10, 10, 110, 60), outline=0)
    # Filled rectangle on red layer
    draw_red.rectangle((15, 15, 105, 55), fill=0)
    
    # Draw text
    # Load a font. 
    # Usually /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf exists on Pi.
    try:
        font15 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 15)
        font20 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
    except IOError:
        # Fallback to default font if specific font not found
        logging.warning("DejaVuSans-Bold.ttf not found, using default font")
        font15 = ImageFont.load_default()
        font20 = ImageFont.load_default()

    draw_black.text((10, 70), 'Hello World', font=font15, fill=0)
    draw_red.text((10, 90), 'e-Paper Demo', font=font15, fill=0)
    draw_black.text((10, 120), 'Raspberry Pi', font=font20, fill=0)
    draw_red.text((10, 150), 'Zero 2 W', font=font20, fill=0)
    
    # Draw current time
    current_time = time.strftime("%H:%M:%S")
    draw_red.text((120, 10), current_time, font=font15, fill=0)

    logging.info("Displaying...")
    epd.display(epd.getbuffer(Himage_black), epd.getbuffer(Himage_red))
    time.sleep(2)
    
    logging.info("Goto Sleep...")
    epd.sleep()
    
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    epd2in13b_V4.epdconfig.module_exit()
    exit()
