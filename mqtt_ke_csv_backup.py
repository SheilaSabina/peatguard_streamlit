import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "sic8/karhutla/banjarbaru/data"
FILE_CSV = sys.argv[1] if len(sys.argv) > 1 else "data_mqtt.csv"

KOLOM = [
    "timestamp", "lokasi", "latitude", "longitude",
    "air_temperature_c", "air_temperature_trend_pct",
    "relative_humidity_pct", "relative_humidity_trend_pct",
    "soil_moisture_pct", "moisture_trend_pct",
    "status_suhu", "status_rh", "status_tanah", "status_tren",
    "static_threshold_status", "warning_status", "mode",
]

# Append supaya histori tidak hilang ketika collector di-restart.
# Gunakan nama file berbeda jika ingin merekam skenario terpisah.
file_path = Path(FILE_CSV)
STATUS_FILE = file_path.with_suffix(".connection.json")
connected = False
last_message_utc = None
write_header = not file_path.exists() or file_path.stat().st_size == 0
if not write_header:
    with file_path.open("r", encoding="utf-8", newline="") as check_file:
        existing_header = next(csv.reader(check_file), [])
    if existing_header != KOLOM:
        raise SystemExit("Header CSV lama tidak sesuai format MQTT terbaru. Gunakan nama CSV baru, misalnya data_mqtt_baru.csv.")
berkas = open(FILE_CSV, "a", newline="", encoding="utf-8")
penulis = csv.DictWriter(berkas, fieldnames=KOLOM)
if write_header:
    penulis.writeheader()
jumlah = 0


def simpan_pesan(payload: bytes):
    global jumlah
    data = json.loads(payload.decode("utf-8"))
    baris = {k: ("" if data.get(k) is None else data[k]) for k in KOLOM}
    penulis.writerow(baris)
    berkas.flush()
    jumlah += 1
    global last_message_utc
    last_message_utc = datetime.now(timezone.utc).isoformat()
    print(f"[{jumlah:>3}] {baris['timestamp']}  tanah={baris['soil_moisture_pct']}  "
          f"[{baris['mode'] or '?'}]  static={baris['static_threshold_status']}  final={baris['warning_status']}")


def on_connect(client, userdata, flags, reason_code, properties=None):
    global connected
    connected = (reason_code == 0)
    print(f"Terhubung ke {BROKER} (kode {reason_code}). Subscribe: {TOPIC}")
    if connected:
        client.subscribe(TOPIC)
    print(f"Menyimpan ke {FILE_CSV}. Jalankan mode sensor atau simulasi di Wokwi sekarang...")


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    global connected
    connected = False

def on_message(client, userdata, msg):
    try:
        simpan_pesan(msg.payload)
    except Exception as e:                 
        print("Pesan dilewati:", e)


try:                                 
    klien = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:                  
    klien = mqtt.Client()
klien.on_connect = on_connect
klien.on_disconnect = on_disconnect
klien.on_message = on_message

def write_heartbeat():
    record = {
        "connected": bool(connected),
        "heartbeat_utc": datetime.now(timezone.utc).isoformat(),
        "last_message_utc": last_message_utc,
        "broker": BROKER,
        "topic": TOPIC,
    }
    tmp = STATUS_FILE.with_name(STATUS_FILE.name + ".tmp")
    tmp.write_text(json.dumps(record), encoding="utf-8")
    tmp.replace(STATUS_FILE)

if __name__ == "__main__":
    try:
        klien.connect(BROKER, PORT, keepalive=60)
        klien.loop_start()
        while True:
            write_heartbeat()
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\nSelesai. {jumlah} baris baru tersimpan di {FILE_CSV}")
    finally:
        klien.loop_stop()
        klien.disconnect()
        berkas.close()
        # heartbeat sengaja berhenti; dashboard mendeteksi data status kadaluarsa
