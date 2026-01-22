import spidev
import lgpio
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
        self.gpio_handle = None
        self.RST_PIN = RST_PIN
        self.DC_PIN = DC_PIN
        self.CS_PIN = CS_PIN
        self.BUSY_PIN = BUSY_PIN
        self.PWR_PIN = PWR_PIN

    def digital_write(self, pin, value):
        if self.gpio_handle is None:
            return
        if pin == CS_PIN:
            return
        lgpio.gpio_write(self.gpio_handle, pin, value)

    def digital_read(self, pin):
        if self.gpio_handle is None:
            return 0
        return lgpio.gpio_read(self.gpio_handle, pin)

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.SPI.writebytes(data)

    def spi_writebyte2(self, data):
        self.SPI.writebytes2(data)

    def module_init(self):
        if self.gpio_handle is not None:
            return 0
            
        logger.debug("Initializing module with lgpio")
        
        try:
            # 1. Open GPIO Chip (usually 0 on Pi)
            self.gpio_handle = lgpio.gpiochip_open(0)
            
            # 2. Claim Output Pins
            # RST, DC, PWR
            try:
                lgpio.gpio_claim_output(self.gpio_handle, RST_PIN)
            except Exception:
                logger.error(f"Failed to claim RST_PIN ({RST_PIN})")
                raise

            try:
                lgpio.gpio_claim_output(self.gpio_handle, DC_PIN)
            except Exception:
                logger.error(f"Failed to claim DC_PIN ({DC_PIN})")
                raise
                
            try:
                lgpio.gpio_claim_output(self.gpio_handle, PWR_PIN)
            except Exception:
                logger.error(f"Failed to claim PWR_PIN ({PWR_PIN})")
                raise
            
            # 3. Claim Input Pins
            # BUSY (Active High usually, usage depends on driver)
            try:
                lgpio.gpio_claim_input(self.gpio_handle, BUSY_PIN)
            except Exception:
                logger.error(f"Failed to claim BUSY_PIN ({BUSY_PIN})")
                raise
            
            # 4. Initialize States
            lgpio.gpio_write(self.gpio_handle, PWR_PIN, 1)
            time.sleep(0.1)
            
            # 5. Initialize SPI
            # SPI device, bus = 0, device = 0
            self.SPI.open(0, 0)
            self.SPI.max_speed_hz = 2000000
            self.SPI.mode = 0b00
            
        except Exception as e:
            logger.error(f"Module Init Failed: {e}")
            # Try to close if partially opened
            if self.gpio_handle is not None:
                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None
            return -1
            
        return 0

    def module_exit(self):
        logger.debug("spi end")
        try:
            if self.SPI:
                self.SPI.close()
        except Exception as e:
            logger.error(f"SPI Close Error: {e}")
            
        logger.debug("gpio close")
        try:
            if self.gpio_handle is not None:
                # Reset pins to safe state before closing?
                # Usually setting PWR low is good practice for EPD
                lgpio.gpio_write(self.gpio_handle, RST_PIN, 0)
                lgpio.gpio_write(self.gpio_handle, DC_PIN, 0)
                lgpio.gpio_write(self.gpio_handle, PWR_PIN, 0)
                
                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None
        except Exception as e:
            logger.error(f"GPIO Close Error: {e}")

# Expose methods to module level
implementation = RaspberryPi()
for func in [x for x in dir(implementation) if not x.startswith('_')]:
    setattr(sys.modules[__name__], func, getattr(implementation, func))

### END OF FILE ###
