import spidev
import RPi.GPIO as GPIO
import time
import sys
import os

# Pin definition
RST_PIN  = 17
DC_PIN   = 25
CS_PIN   = 8
BUSY_PIN = 24
PWR_PIN  = 18

def log(msg):
    print(f"[DIAGNOSTIC] {msg}")

def check_spi():
    log("Checking SPI device...")
    if not os.path.exists('/dev/spidev0.0'):
        log("ERROR: /dev/spidev0.0 not found. Is SPI enabled in raspi-config?")
        return False
    
    try:
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 2000000
        spi.mode = 0b00
        log("SPI device opened successfully.")
        spi.close()
        return True
    except Exception as e:
        log(f"ERROR: Failed to open SPI device: {e}")
        return False

def check_gpio():
    log("Checking GPIO setup...")
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins
        GPIO.setup(RST_PIN, GPIO.OUT)
        GPIO.setup(DC_PIN, GPIO.OUT)
        GPIO.setup(PWR_PIN, GPIO.OUT)
        GPIO.setup(BUSY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Try PUD_DOWN first as per code
        
        log("GPIO setup successful.")
        return True
    except Exception as e:
        log(f"ERROR: Failed to setup GPIO: {e}")
        return False

def test_reset_busy():
    log("Testing Reset and Busy signal...")
    
    # Power on
    GPIO.output(PWR_PIN, 1)
    time.sleep(0.1)
    
    # Initial state of BUSY
    initial_busy = GPIO.input(BUSY_PIN)
    log(f"Initial BUSY pin state: {initial_busy}")
    
    # Reset sequence
    log("Sending Reset signal...")
    GPIO.output(RST_PIN, 1)
    time.sleep(0.2)
    GPIO.output(RST_PIN, 0)
    time.sleep(0.01)
    GPIO.output(RST_PIN, 1)
    time.sleep(0.2)
    
    # Check BUSY after reset
    post_reset_busy = GPIO.input(BUSY_PIN)
    log(f"Post-Reset BUSY pin state: {post_reset_busy}")
    
    if initial_busy == post_reset_busy:
        log("WARNING: BUSY pin did not change state during reset (or was already idle).")
    else:
        log("BUSY pin state changed, display is reacting to Reset.")

    # Cleanup
    GPIO.output(RST_PIN, 0)
    GPIO.output(PWR_PIN, 0)
    GPIO.cleanup()

if __name__ == "__main__":
    log("Starting diagnostic...")
    if check_spi() and check_gpio():
        test_reset_busy()
    log("Diagnostic finished.")
