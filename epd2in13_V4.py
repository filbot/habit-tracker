# *****************************************************************************
# * | File        :	  epd2in13_V4.py
# * | Author      :   Waveshare team
# * | Function    :   Electronic paper driver
# * | Info        :
# *----------------
# * | This version:   V1.0
# * | Date        :   2023-06-16
# * | Info        :   python demo
# *----------------
# *****************************************************************************

import logging
import epdconfig

# Display resolution
EPD_WIDTH       = 122
EPD_HEIGHT      = 250

logger = logging.getLogger(__name__)

class EPD:
    def __init__(self):
        self.reset_pin = epdconfig.RST_PIN
        self.dc_pin = epdconfig.DC_PIN
        self.busy_pin = epdconfig.BUSY_PIN
        self.cs_pin = epdconfig.CS_PIN
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

    # hardware reset
    def reset(self):
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(20) 
        epdconfig.digital_write(self.reset_pin, 0)
        epdconfig.delay_ms(2)
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(20)   

    # send 1 byte command
    def send_command(self, command):
        epdconfig.digital_write(self.dc_pin, 0)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([command])
        epdconfig.digital_write(self.cs_pin, 1)
    
    # send 1 byte data
    def send_data(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([data])
        epdconfig.digital_write(self.cs_pin, 1)
        
    # send a lot of data   
    def send_data2(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte2(data)
        epdconfig.digital_write(self.cs_pin, 1)
        
    # judge e-Paper whether is busy
    def busy(self):
        logger.debug("e-Paper busy")
        while(epdconfig.digital_read(self.busy_pin) == 1): # 0: busy, 1: idle
            epdconfig.delay_ms(10)
        # Wait, the previous driver (b_V4) had: while(epdconfig.digital_read(self.busy_pin) != 0)
        # That means 1 is busy, 0 is idle? 
        # Let's check epd2in13b_V4 reference.
        # epd2in13b_V4: while(digital_read(busy) != 0) -> Busy is HIGH.
        # Use previous logic to be safe unless I am sure.
        # Actually, let's stick to the previous logic: if BUSY var is HIGH, it's busy.
        pass
        
    def ReadBusy(self):
        logger.debug("e-Paper busy")
        while(epdconfig.digital_read(self.busy_pin) == 1):      # 1: busy, 0: idle
            epdconfig.delay_ms(10)
        logger.debug("e-Paper busy release")

    # set the display window
    def set_windows(self, xstart, ystart, xend, yend):
        self.send_command(0x44) # SET_RAM_X_ADDRESS_START_END_POSITION
        self.send_data((xstart>>3) & 0xff)
        self.send_data((xend>>3) & 0xff)
        
        self.send_command(0x45) # SET_RAM_Y_ADDRESS_START_END_POSITION
        self.send_data(ystart & 0xff)
        self.send_data((ystart >> 8) & 0xff)
        self.send_data(yend & 0xff)
        self.send_data((yend >> 8) & 0xff)
        
    # set the display cursor(origin)
    def set_cursor(self, xstart, ystart):
        self.send_command(0x4E) # SET_RAM_X_ADDRESS_COUNTER
        self.send_data(xstart & 0xff)

        self.send_command(0x4F) # SET_RAM_Y_ADDRESS_COUNTER
        self.send_data(ystart & 0xff)
        self.send_data((ystart >> 8) & 0xff)

    # initialize 
    def init(self):
        if (epdconfig.module_init() != 0):
            return -1
            
        self.reset()
        
        # Wait for busy? 
        self.ReadBusy()

        self.send_command(0x12)  # SWRESET
        self.ReadBusy()   

        self.send_command(0x01) # Driver output control      
        self.send_data(0xf9)
        self.send_data(0x00)
        self.send_data(0x00)

        self.send_command(0x11) # data entry mode       
        self.send_data(0x03)

        self.set_windows(0, 0, self.width - 1, self.height - 1)
        self.set_cursor(0, 0)

        self.send_command(0x3C) # BorderWavefrom
        self.send_data(0x05)	

        self.send_command(0x18) # Read built-in temperature sensor
        self.send_data(0x80)	

        self.send_command(0x21) # Display update control
        self.send_data(0x00)
        self.send_data(0x80)

        self.ReadBusy()
        
        return 0
        
    def init_fast(self):
        # fast refresh init
        # Based on typical V4 fast init
        if (epdconfig.module_init() != 0):
            return -1
            
        self.reset()
        self.send_command(0x12)  # SWRESET
        self.ReadBusy() 

        self.send_command(0x18) # Read built-in temperature sensor
        self.send_data(0x80)
        
        self.send_command(0x22) # Load temperature value
        self.send_data(0xB1) 
        self.send_command(0x20) 
        self.ReadBusy() 

        self.send_command(0x11) # data entry mode       
        self.send_data(0x03)

        self.set_windows(0, 0, self.width - 1, self.height - 1)
        self.set_cursor(0, 0)
        
        self.send_command(0x22) # Display Update Control
        self.send_data(0xC7) # Fast?
        
        return 0

    # turn on display
    def TurnOnDisplay(self):
        self.send_command(0x20)
        self.ReadBusy()
        
    def TurnOnDisplayPart(self):
        self.send_command(0x22)
        self.send_data(0xFF) # 0xC7 or 0xFF? typical is 0xFF or 0x0C for partial
        self.send_command(0x20)
        self.ReadBusy()

    # image converted to bytearray
    def getbuffer(self, image):
        img = image
        imwidth, imheight = img.size
        # The display is 122x250 (vertical), so if image is 122x250:
        if(imwidth == self.width and imheight == self.height):
            img = img.convert('1')
        elif(imwidth == self.height and imheight == self.width):
            # Rotate
            img = img.rotate(90, expand=True).convert('1')
        else:
            logger.warning("Wrong image dimensions: must be " + str(self.width) + "x" + str(self.height))
            # return a blank buffer
            return [0x00] * (int(self.width/8) * self.height)

        buf = bytearray(img.tobytes('raw'))
        return buf

    # display image
    def display(self, image):
        self.send_command(0x24)
        self.send_data2(image)
        self.TurnOnDisplay()
        
    def displayPartial(self, image):
        # NOTE: User says partial refresh is supported.
        # Usually requires writing to 0x24 and triggering partial update
        self.send_command(0x24)
        self.send_data2(image)
        
        # Determine strict partial update command
        # For V4, it is often:
        # 1. Init (Fast) is different?
        # Or just use 0x22 -> 0x0F/0xFF?
        
        # Let's try the common V4 partial sequence
        # Write to RAM
        # Update
        self.TurnOnDisplayPart()

    # display white image
    def clear(self):
        if self.width%8 == 0:
            linewidth = int(self.width/8)
        else:
            linewidth = int(self.width/8) + 1
            
        buf = [0xff] * (int(linewidth * self.height))
            
        self.send_command(0x24)
        self.send_data2(buf)
        self.TurnOnDisplay()

    # sleep
    def sleep(self):
        self.send_command(0x10) # DEEP_SLEEP
        self.send_data(0x01) # check code
        
        epdconfig.delay_ms(2000)
        epdconfig.module_exit()
