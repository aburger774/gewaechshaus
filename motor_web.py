# === Datei: motor_web.py ===

from flask import Flask, render_template, request, jsonify, redirect, url_for
import RPi.GPIO as GPIO
import threading
import time
import spidev
import json
import os

app = Flask(__name__)

# === GPIO-Pins ===
RPWM = 17
LPWM = 18
ANEMO_PIN = 23
PIN_CS = 5
PIN_DRDY = 4
RELAIS_PIN = 16

# === GPIO Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(RPWM, GPIO.OUT)
GPIO.setup(LPWM, GPIO.OUT)
GPIO.setup(ANEMO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(PIN_CS, GPIO.OUT)
GPIO.setup(PIN_DRDY, GPIO.IN)
GPIO.setup(RELAIS_PIN, GPIO.OUT)
GPIO.output(RELAIS_PIN, GPIO.LOW)  # Anfangszustand: aus


# === Bewässerung ===
bewaesserung_aktiv = False

# === PWM Setup ===
freq = 2000
rpwm_pwm = GPIO.PWM(RPWM, freq)
lpwm_pwm = GPIO.PWM(LPWM, freq)
rpwm_pwm.start(0)
lpwm_pwm.start(0)

# === Windmessung & Motorstatus ===
impuls_count = 0
lock = threading.Lock()
wind_kmh = 0.0
motor_status = "stopp"

# === Konstante ===
IMPULSE_PRO_UMDREHUNG = 1
UMDREHUNGEN_PRO_METER_PRO_SEKUNDE = 1.0
WIND_MAX_AUTO_EINFHREN = 40.0

# === Settings Datei ===
SETTINGS_FILE = "settings.json"
settings = {
    "windLimit": 40.0,
    "motorSpeed": 75,
    "autoMode": True,
    "notifications": False,
    "updateInterval": 1000,
    "dataRetention": 7
}

def load_settings():
    global settings, WIND_MAX_AUTO_EINFHREN
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings.update(json.load(f))
    WIND_MAX_AUTO_EINFHREN = settings["windLimit"]

def save_settings():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

# === SPI/ADS1256 ===
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
    spi.xfer2([0x01])
    time.sleep(0.01)
    raw = spi.readbytes(3)
    cs_high()
    result = (raw[0] << 16) | (raw[1] << 8) | raw[2]
    if result & 0x800000:
        result -= 0x1000000
    return result

def init_ads1256():
    send_cmd(0xFE)
    time.sleep(0.1)
    write_register(0x00, 0x01)
    write_register(0x01, 0x08)
    write_register(0x02, 0x00)
    write_register(0x03, 0xF0)
    send_cmd(0xF0)
    time.sleep(0.1)

def read_voltage():
    send_cmd(0xFC)
    send_cmd(0x00)
    if not wait_drdy():
        return None
    raw = read_data()
    return (raw * 2.5) / 0x7FFFFF

def feuchtigkeits_status(spannung):
    if spannung > 2.4:
        return "zu nass"
    elif 2.0 <= spannung <= 2.4:
        return "perfekt"
    else:
        return "zu trocken"

# === Windmessung ===
def count_impulse(channel):
    global impuls_count
    with lock:
        impuls_count += 1
GPIO.add_event_detect(ANEMO_PIN, GPIO.FALLING, callback=count_impulse)

def windmessung_loop():
    global impuls_count, wind_kmh, motor_status
    while True:
        with lock:
            impuls_count = 0
        start = time.time()
        time.sleep(1)
        duration = time.time() - start
        with lock:
            umdrehungen = impuls_count / IMPULSE_PRO_UMDREHUNG
        wind_mps = umdrehungen / duration / UMDREHUNGEN_PRO_METER_PRO_SEKUNDE
        wind_kmh = wind_mps * 3.6
        print(f"[INFO] Wind: {wind_kmh:.2f} km/h | Status: {motor_status}")

        if wind_kmh > WIND_MAX_AUTO_EINFHREN and motor_status == "ausgefahren":
            print(f"[WARNUNG] Wind zu stark ({wind_kmh:.2f} km/h), fahre Motor ein!")
            motor_einfahren()

# === Motorsteuerung ===
def motor_ausfahren():
    global motor_status
    rpwm_pwm.ChangeDutyCycle(settings["motorSpeed"])
    lpwm_pwm.ChangeDutyCycle(0)
    motor_status = "ausgefahren"

def motor_einfahren():
    global motor_status
    rpwm_pwm.ChangeDutyCycle(0)
    lpwm_pwm.ChangeDutyCycle(settings["motorSpeed"])
    motor_status = "eingefahren"

def motor_stopp():
    global motor_status
    rpwm_pwm.ChangeDutyCycle(0)
    lpwm_pwm.ChangeDutyCycle(0)
    motor_status = "stopp"

# === Flask Routes ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/steuerung')
def steuerung():
    return render_template('steuerung.html')

@app.route('/verlauf')
def verlauf():
    return render_template('verlauf.html')

@app.route('/einstellungen')
def einstellungen():
    return render_template('einstellungen.html', settings=settings)

@app.route('/einstellungen/speichern', methods=['POST'])
def einstellungen_speichern():
    global settings, WIND_MAX_AUTO_EINFHREN
    try:
        settings["windLimit"] = float(request.form.get("windLimit", 40))
        settings["motorSpeed"] = int(request.form.get("motorSpeed", 75))
        settings["autoMode"] = 'autoMode' in request.form
        settings["notifications"] = 'notifications' in request.form
        settings["updateInterval"] = int(request.form.get("updateInterval", 1000))
        settings["dataRetention"] = int(request.form.get("dataRetention", 7))

        WIND_MAX_AUTO_EINFHREN = settings["windLimit"]
        save_settings()
        print("[INFO] Einstellungen gespeichert:", settings)
    except Exception as e:
        print("[FEHLER] Einstellungen speichern fehlgeschlagen:", e)
    return redirect(url_for("einstellungen"))

@app.route('/motor', methods=['POST'])
def motor():
    action = request.form['action']
    if action == 'ein':
        motor_einfahren()
    elif action == 'aus':
        motor_ausfahren()
    elif action == 'stopp':
        motor_stopp()
    return '', 204

@app.route('/bewaesserung', methods=['POST'])
def bewaesserung():
    global bewaesserung_aktiv
    action = request.form.get('action')
    if action == 'ein':
        print("Relais an (Pin als OUTPUT)")
        GPIO.setup(RELAIS_PIN, GPIO.OUT)
        GPIO.output(RELAIS_PIN, GPIO.HIGH)  # Relais schaltet ein
        bewaesserung_aktiv = True
    elif action == 'aus':
        print("Relais aus (Pin als INPUT)")
        GPIO.setup(RELAIS_PIN, GPIO.IN)    # Relais schaltet aus
        bewaesserung_aktiv = False

    return '', 204

@app.route('/bewaesserung/status')
def bewaesserung_status():
    return jsonify({'aktiv': bewaesserung_aktiv})

@app.route('/wind')
def wind():
    return jsonify({'wind_kmh': round(wind_kmh, 2), 'status': motor_status})

@app.route('/bodenfeuchte')
def bodenfeuchte():
    voltage = read_voltage()
    if voltage is None:
        return jsonify({'error': 'Messfehler'}), 500

    # Beispielhafte Statuslogik (angepasst an deine Sensorwerte):
    if voltage > 1.3:
        status = "Sehr trocken"
    elif voltage > 0.8:
        status = "Optimal"
    else:
        status = "Zu nass"

    return jsonify({'spannung_v': round(voltage, 4), 'status': status})



import pymysql

def db_connection():
    return pymysql.connect(
        host="localhost",
        user="grafana",
        password="starkespasswort",
        database="sensordaten",
        cursorclass=pymysql.cursors.DictCursor  # Optional, wenn du dict statt tuples willst
    )

def speicher_daten_loop():
    while True:
        try:
            with lock:
                wind = wind_kmh
            boden = read_voltage()
            conn = db_connection()
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO winddaten (wind_kmh) VALUES (%s)", (wind,))
                if boden is not None:
                    cursor.execute("INSERT INTO bodenfeuchte (spannung_v) VALUES (%s)", (boden,))
            conn.commit()
            conn.close()
            print(f"[INFO] Daten gespeichert: Wind={wind:.2f} km/h, Boden={boden:.3f} V")
        except Exception as e:
            print(f"[FEHLER] Beim Speichern in DB: {e}")
        time.sleep(60)

# === Start ===
if __name__ == '__main__':
    try:
        load_settings()
        init_ads1256()
        threading.Thread(target=windmessung_loop, daemon=True).start()
        threading.Thread(target=speicher_daten_loop, daemon=True).start()
        app.run(host='0.0.0.0', port=5001)
    finally:
        print("[CLEANUP] Stoppe Motor & GPIO")
        motor_stopp()
        rpwm_pwm.stop()
        lpwm_pwm.stop()
        spi.close()
        GPIO.cleanup()

