import RPi.GPIO as GPIO
import time

RELAIS_PIN = 16

GPIO.setmode(GPIO.BCM)

try:
    while True:
        # Relais aus: Pin als Input konfigurieren
        print("Relais aus (Pin als INPUT)")
        GPIO.setup(RELAIS_PIN, GPIO.IN)
        time.sleep(2)

        # Relais an: Pin als Output konfigurieren
        print("Relais an (Pin als OUTPUT)")
        GPIO.setup(RELAIS_PIN, GPIO.OUT)
        GPIO.output(RELAIS_PIN, GPIO.HIGH)  # Falls nötig, HIGH setzen
        time.sleep(2)

except KeyboardInterrupt:
    print("Programm beendet")

finally:
    GPIO.cleanup()
