
# 🌱 Gewächshaus Steuerungssystem

Ein leichtgewichtiges Python-Webinterface zur Überwachung und Steuerung eines Gewächshauses auf dem Raspberry Pi.

## 📦 Features

- 🌡️ Sensorüberwachung (z. B. Bodenfeuchtigkeit)
- ⚙️ Steuerung von Relais (z. B. für Ventile)
- 🌐 Web-Interface zur Bedienung über Browser
- 🧠 Einstellbare Parameter via JSON
- 📊 Verlaufsspeicherung von Sensordaten (optional)

## 🖥️ Technologie-Stack

- Python 3
- Flask (Webserver)
- HTML + Jinja2 Templates
- Raspberry Pi GPIO

## 🚀 Setup

1. Repository klonen:
   ```
   git clone https://github.com/aburger774/gewaechshaus.git
   cd gewaechshaus
   ```

2. Abhängigkeiten installieren:
   ```
   pip install -r requirements.txt
   ```

3. Skript starten:
   ```
   python3 motor_web.py
   ```

4. Im Browser öffnen:
   ```
   http://<RaspberryPi-IP>:5000
   ```

## ⚙️ Konfiguration

Passe die Datei `settings.json` an deine Sensor- und Relais-Konfiguration an.

Beispiel:
```
{
  "relais_1": true,
  "temperature_threshold": 25.0
}
```

## 📁 Projektstruktur

```
gewaechshaus/
├── motor_web.py            # Haupt-Webserver
├── settings.json           # Konfiguration
├── templates/              # HTML-Oberflächen
├── sensor_test.py          # Sensorskript
├── relaistest.py           # Relaissteuerung
```

## Gemacht von dem ITP TEAM (Alex, ELias, Lara, Julia)