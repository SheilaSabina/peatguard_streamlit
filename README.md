# PeatGuard — Dashboard Streamlit (versi kompatibel MQTT Ghani terbaru)

1. Buka terminal pada folder ini.
2. `python -m pip install -r requirements.txt`
3. Terminal pertama: `python mqtt_ke_csv.py data_mqtt_baru.csv`
4. Jalankan skenario Wokwi.
5. Terminal kedua: `python -m streamlit run dashboard.py`
6. Di sidebar Streamlit masukkan `data_mqtt_baru.csv`.

Dashboard kompatibel dengan payload lama dan baru, tetapi status perbandingan static threshold hanya tampil bila firmware benar-benar mengirim `static_threshold_status`. CSV kolektor baru menambahkan baris (append), bukan menimpa file, dan menolak mencampur header format lama dan baru. Gunakan file berbeda setiap skenario bila memerlukan pengujian terpisah.

PENTING: link Wokwi yang ditinjau pada 25 Oktober masih menunjukkan payload lama dengan `warning_status` saja. Minta Ghani memastikan versi kode terbaru telah disimpan dan dapat diakses di tautan tersebut. Broker yang digunakan adalah broker MQTT publik tanpa TLS; jangan gunakan informasi rahasia.
