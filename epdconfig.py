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
        if pin == CS_PIN:
            return
        GPIO.output(pin, value)

    def digital_read(self, pin):
        return GPIO.input(pin)

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
        # CS_PIN is handled by spidev, do not setup as GPIO
        GPIO.setup(PWR_PIN, GPIO.OUT)
        # Use Pull Down for BUSY pin to ensure it's not floating High
        GPIO.setup(BUSY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        GPIO.output(PWR_PIN, 1)
        time.sleep(0.1) # Wait for power to stabilize
        
        # SPI device, bus = 0, device = 0
        self.SPI.open(0, 0)
        self.SPI.max_speed_hz = 1000000 # 1MHz
        self.SPI.mode = 0b00
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
