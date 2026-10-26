"""
pip install paho-mqtt
python mqtt_ke_csv.py
python mqtt_ke_csv.py hasil_siaga.csv
"""


import csv
import json
import sys

import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "sic8/karhutla/banjarbaru/data" 
FILE_CSV = sys.argv[1] if len(sys.argv) > 1 else "data_mqtt.csv"

KOLOM = [
    "timestamp", "lokasi", "latitude", "longitude",
    "air_temperature_c", "air_temperature_trend_pct",
    "relative_humidity_pct", "relative_humidity_trend_pct",
    "soil_moisture_pct", "moisture_trend_pct", "warning_status",
]

berkas = open(FILE_CSV, "w", newline="", encoding="utf-8")
penulis = csv.DictWriter(berkas, fieldnames=KOLOM)
penulis.writeheader()
jumlah = 0


def simpan_pesan(payload: bytes):
    """Ubah satu pesan JSON jadi satu baris CSV. null (saat Initializing) jadi sel kosong."""
    global jumlah
    data = json.loads(payload.decode("utf-8"))
    baris = {k: ("" if data.get(k) is None else data[k]) for k in KOLOM}
    penulis.writerow(baris)
    berkas.flush()
    jumlah += 1
    print(f"[{jumlah:>3}] {baris['timestamp']}  tanah={baris['soil_moisture_pct']}  "
          f"status={baris['warning_status']}")


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"Terhubung ke {BROKER} (kode {reason_code}). Subscribe: {TOPIC}")
    client.subscribe(TOPIC)
    print(f"Menyimpan ke {FILE_CSV}. Jalankan simulasi sekarang...")


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
klien.on_message = on_message

if __name__ == "__main__":
    klien.connect(BROKER, PORT, keepalive=60)
    try:
        klien.loop_forever()
    except KeyboardInterrupt:
        print(f"\nSelesai. {jumlah} baris tersimpan di {FILE_CSV}")
    finally:
        berkas.close()
