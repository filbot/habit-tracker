import spidev
import RPi.GPIO as GPIO
import time
import logging
import sys

logger = logging.getLogger(__name__)

# Pin definition
RST_PIN  = 17
DC_PIN   = 25
CS_PIN   = 8
BUSY_PIN = 24
PWR_PIN  = 18

class RaspberryPi:
    def __init__(self):
        self.SPI = spidev.SpiDev()
        self.RST_PIN = RST_PIN
        self.DC_PIN = DC_PIN
        self.CS_PIN = CS_PIN
        self.BUSY_PIN = BUSY_PIN
        self.PWR_PIN = PWR_PIN

    def digital_write(self, pin, value):
        GPIO.output(pin, value)

    def digital_read(self, pin):
        val = GPIO.input(pin)
        # logger.debug(f"Read pin {pin}: {val}")
        return val

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.SPI.writebytes(data)

    def spi_writebyte2(self, data):
        self.SPI.writebytes2(data)

    def module_init(self):
        logger.debug("Initializing module with RPi.GPIO")
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins
        GPIO.setup(RST_PIN, GPIO.OUT)
        GPIO.setup(DC_PIN, GPIO.OUT)
        GPIO.setup(PWR_PIN, GPIO.OUT)
        GPIO.setup(BUSY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Manual CS Control Trick:
        # We want to control CS (GPIO 8) manually because spidev's timing might not match
        # what the display driver expects (or we want to be sure).
        # However, spidev(0,0) claims GPIO 8.
        # So we open spidev(0,1) which claims GPIO 7, leaving GPIO 8 free for us to use as generic GPIO.
        # Note: This assumes nothing is connected to CE1 (GPIO 7).
        
        try:
            GPIO.setup(CS_PIN, GPIO.OUT)
            GPIO.output(CS_PIN, 1)
            logger.debug("CS Pin setup as GPIO Output")
            
            # Open SPI Bus 0, Device 1 (CE1) to avoid conflict on CE0
            self.SPI.open(0, 1)
            self.SPI.max_speed_hz = 2000000
            self.SPI.mode = 0b00
            self.SPI.no_cs = True # Tell spidev not to touch CS (though it would touch CE1)
        except Exception as e:
            logger.error(f"Failed to setup SPI/CS: {e}")
            return -1

        GPIO.output(PWR_PIN, 1)
        time.sleep(0.1)
        
        return 0

    def module_exit(self):
        logger.debug("spi end")
        self.SPI.close()
        
        GPIO.output(RST_PIN, 0)
        GPIO.output(DC_PIN, 0)
        GPIO.output(PWR_PIN, 0)
        GPIO.cleanup()

# Expose methods to module level
implementation = RaspberryPi()
for func in [x for x in dir(implementation) if not x.startswith('_')]:
    setattr(sys.modules[__name__], func, getattr(implementation, func))

### END OF FILE ###
