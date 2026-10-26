
# 🌿 PeatGuard — IoT-Based Peatland Fire Early Warning with Trend-Aware

PeatGuard merupakan prototipe sistem peringatan dini kebakaran lahan gambut berbasis Internet of Things (IoT) yang menggunakan ESP32, komunikasi MQTT, dan dashboard Streamlit.

Sistem memantau suhu udara, kelembapan relatif udara, serta kelembapan tanah untuk menentukan status kewaspadaan **Normal, Waspada, atau Siaga** berdasarkan aturan yang diterapkan pada ESP32.

Dashboard digunakan untuk menampilkan data pemantauan, analisis indikator, grafik perubahan lingkungan, serta perbandingan hasil **Static Threshold** dan **Trend-Aware**.

## 1. Teknologi yang Digunakan

| Teknologi | Fungsi |
|---|---|
| ESP32 | Pengolahan data dan penentuan status kewaspadaan |
| Wokwi | Simulasi perangkat dan sensor |
| MQTT | Komunikasi data IoT |
| HiveMQ Public Broker | Perantara pengiriman pesan MQTT |
| Python dan paho-mqtt | Penerimaan data MQTT |
| CSV | Penyimpanan hasil pembacaan |
| Streamlit | Antarmuka dashboard |
| pandas | Pengolahan data |
| Plotly | Visualisasi grafik |

## 2. Struktur File

```text
peatguard_streamlit/
├── dashboard.py
├── mqtt_ke_csv.py
├── analisis_selisih.py
├── requirements.txt
└── README.md
```

File CSV hasil pengujian dan file `.connection.json` dibuat ketika collector dijalankan. File `sketch.ino` digunakan pada simulasi ESP32 di Wokwi.

## 3. Instalasi

Pastikan Python sudah terpasang pada komputer.

Buka folder proyek melalui VS Code, kemudian jalankan perintah berikut pada terminal:

```bash
python -m pip install -r requirements.txt
```

## 4. Menjalankan Dashboard

### A. Menggunakan data CSV yang sudah tersimpan

Jalankan perintah:

```bash
python -m streamlit run dashboard.py
```

Buka dashboard melalui:

http://localhost:8501

Pada sidebar Streamlit:

1. Pilih **Unggah CSV**.
2. Pilih file CSV hasil pengujian.
3. Dashboard akan menampilkan data dan hasil analisis berdasarkan file tersebut.

Cara ini tidak memerlukan Wokwi atau MQTT collector yang sedang aktif.

### B. Menggunakan data langsung dari MQTT

Buka dua terminal pada folder proyek.

**Terminal 1 — MQTT Collector**

```bash
python mqtt_ke_csv.py data_normal_72.csv
```

Pastikan subscriber berhasil terhubung ke broker MQTT.

Selanjutnya, jalankan simulasi ESP32 di Wokwi dan pilih skenario melalui Serial Monitor.

**Terminal 2 — Streamlit Dashboard**

```bash
python -m streamlit run dashboard.py
```

Pada sidebar dashboard:

1. Pilih **CSV dari MQTT collector**.
2. Masukkan nama file `data_normal_72.csv`.
3. Periksa jumlah pembacaan, nilai parameter, dan status kewaspadaan.

Gunakan nama CSV yang berbeda untuk setiap sesi pengujian agar data tidak tercampur.

## 5. Skenario Pengujian

PeatGuard menyediakan empat skenario simulasi.

| Input Serial | Skenario | Deskripsi |
|---|---|---|
| 1 | Normal | Kondisi parameter lingkungan relatif stabil |
| 2 | Waspada | Perubahan kondisi lingkungan menuju tingkat Waspada |
| 3 | Siaga | Perubahan kondisi lingkungan menuju tingkat Siaga |
| 4 | Udara_kering | Suhu udara tinggi dan kelembapan udara rendah, sementara tanah masih relatif lembap |

Setiap skenario menghasilkan **72 pembacaan sintetis** dengan interval timestamp satu jam.

Sistem menggunakan jendela pengamatan sebanyak **24 pembacaan** untuk menghitung tren.

- Pembacaan 1–23: status `Initializing`.
- Pembacaan 24–72: status akhir sudah tersedia.
- Total pembacaan yang dievaluasi: **49 data per skenario**.

Data simulasi tidak merepresentasikan pengukuran langsung di lahan gambut.

## 6. Analisis Static Threshold dan Trend-Aware

PeatGuard membandingkan dua pendekatan penentuan status kewaspadaan.

**Static Threshold**

Menentukan status berdasarkan batas nilai kelembapan tanah pada pembacaan saat ini.

**Trend-Aware**

Menentukan status akhir menggunakan kombinasi parameter lingkungan dan hasil analisis tren historis.

Perbandingan menggunakan status **Waspada** dan **Siaga** sebagai alarm. Status `Initializing` tidak dimasukkan dalam evaluasi.

Selisih alarm dihitung menggunakan:

```text
Selisih alarm = Jumlah alarm Trend-Aware - Jumlah alarm Static Threshold
```

### Menjalankan analisis

Gunakan perintah:

```bash
python analisis_selisih.py data_normal_72.csv --out hasil_normal.csv
```

Ganti nama file sesuai skenario yang ingin dianalisis.

Skrip menghasilkan ringkasan:

- Jumlah pembacaan yang dievaluasi.
- Jumlah pembacaan berstatus alarm pada masing-masing pendekatan.
- Selisih jumlah alarm.
- Jumlah pembacaan dengan perbedaan status.
- Posisi pembacaan pertama yang mencapai Waspada atau Siaga.
- Selisih waktu peringatan dalam satuan jam sintetis.

### Hasil Acuan Pengujian

Berikut hasil acuan berdasarkan pengujian yang disampaikan tim pengembang.

| Skenario | Data Dievaluasi | Static | Trend-Aware | Selisih Alarm |
|---|---:|---:|---:|---:|
| Normal | 49 | 0 | 0 | 0 |
| Waspada | 49 | 31 | 36 | +5 |
| Siaga | 49 | 31 | 37 | +6 |
| Udara_kering | 49 | 0 | 38 | +38 |

Angka pada tabel merupakan acuan pemeriksaan. Hasil aktual harus diperiksa menggunakan CSV dari sesi pengujian masing-masing.

Selisih alarm menunjukkan perbedaan jumlah pembacaan berstatus peringatan, bukan jumlah *false alarm*.

## 7. Fitur Dashboard

Dashboard PeatGuard menyediakan:

- Tampilan suhu udara, kelembapan relatif udara, dan kelembapan tanah.
- Status kewaspadaan Normal, Waspada, dan Siaga.
- Analisis indikator berdasarkan status setiap parameter.
- Progres pembacaan dan jendela analisis tren.
- Grafik perubahan parameter lingkungan.
- Perbandingan keluaran Static Threshold dan Trend-Aware.
- Ringkasan selisih jumlah alarm dan waktu peringatan pertama.
- Visualisasi garis waktu peringatan.
- Distribusi status kewaspadaan.
- Tabel riwayat pembacaan.
- Unduhan hasil pengamatan dalam format CSV.
- Informasi koneksi Python MQTT subscriber melalui heartbeat.

## 8. Konfigurasi MQTT

Konfigurasi komunikasi yang digunakan:

```text
Broker : broker.hivemq.com
Port   : 1883
Topic  : sic8/karhutla/banjarbaru/data
```

ESP32 bertindak sebagai MQTT publisher, sedangkan program Python `mqtt_ke_csv.py` bertindak sebagai subscriber.

Alur komunikasi:

```text
Sensor / Data Simulasi
          |
          v
      ESP32 Wokwi
          |
          v
      MQTT Broker
          |
          v
   Python Subscriber
          |
          v
       File CSV
          |
          v
  Dashboard Streamlit
```

Status koneksi MQTT pada dashboard menunjukkan koneksi antara Python subscriber dan broker, bukan secara langsung koneksi ESP32 dengan broker.

## 9. Catatan Penggunaan

1. Data pada skenario Wokwi merupakan data sintetis, bukan hasil pengukuran lapangan.
2. Gunakan satu file CSV untuk setiap sesi pengujian agar hasil tidak tercampur.
3. Kolom `skenario` digunakan untuk mengidentifikasi skenario simulasi.
4. Pada tahap `Initializing`, beberapa nilai tren masih kosong karena jendela pengamatan belum terpenuhi.
5. File `.connection.json` digunakan oleh dashboard untuk memantau heartbeat MQTT collector.
6. Koneksi menggunakan broker MQTT publik pada port 1883 tanpa TLS. Jangan mengirimkan informasi rahasia.
7. Hasil perbandingan alarm dan waktu peringatan merupakan hasil pengujian fungsional pada data sintetis.
8. Perbedaan jumlah alarm belum membuktikan peningkatan akurasi atau penurunan *false alarm* tanpa data referensi kondisi sebenarnya.

---

**PeatGuard — Samsung Innovation Campus Batch 8**