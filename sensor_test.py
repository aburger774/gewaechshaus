import spidev
import RPi.GPIO as GPIO
import time

# Pin-Belegung
PIN_CS = 5
PIN_DRDY = 4

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_CS, GPIO.OUT)
GPIO.setup(PIN_DRDY, GPIO.IN)

# SPI Setup
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000
spi.mode = 0b01

def cs_low(): GPIO.output(PIN_CS, GPIO.LOW)
def cs_high(): GPIO.output(PIN_CS, GPIO.HIGH)
def wait_drdy(): 
    for _ in range(1000):
        if GPIO.input(PIN_DRDY) == 0:
            return True
        time.sleep(0.001)
    return False

def send_cmd(cmd):
    cs_low()
    spi.xfer2([cmd])
    cs_high()
    time.sleep(0.01)

def write_register(reg, value):
    cs_low()
    spi.xfer2([0x50 | reg, 0x00, value])
    cs_high()
    time.sleep(0.01)

def read_data():
    cs_low()
    spi.xfer2([0x01])  # RDATA
    time.sleep(0.01)
    raw = spi.readbytes(3)
    cs_high()
    result = (raw[0] << 16) | (raw[1] << 8) | raw[2]
    if result & 0x800000:
        result -= 0x1000000
    return result

def init_ads1256():
    send_cmd(0xFE)  # RESET
    time.sleep(0.1)
    write_register(0x00, 0x01)  # STATUS: Auto-Calibration on
    write_register(0x01, 0x08)  # MUX: AIN0 - AINCOM
    write_register(0x02, 0x00)  # ADCON: Gain 1
    write_register(0x03, 0xF0)  # DRATE: 30k SPS
    send_cmd(0xF0)              # SELFCAL
    time.sleep(0.1)

def read_voltage():
    send_cmd(0xFC)  # SYNC
    send_cmd(0x00)  # WAKEUP
    if not wait_drdy():
        print("DRDY Timeout!")
        return None
    raw = read_data()
    voltage = (raw * 2.5) / 0x7FFFFF
    return voltage

# ========== Hauptprogramm ==========
init_ads1256()
print("Spannung vom Bodenfeuchtesensor (AIN0 gegen AINCOM):")

try:
    while True:
        volt = read_voltage()
        if volt is not None:
            print(f"{volt:.4f} V")
        else:
            print("Fehler bei der Messung.")
        time.sleep(1)
except KeyboardInterrupt:
    print("Messung beendet.")
finally:
    spi.close()
    GPIO.cleanup()
