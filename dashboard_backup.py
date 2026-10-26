"""PeatGuard dashboard — shows MQTT data archived to CSV by the collector."""
from pathlib import Path
import os
import json
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="PeatGuard | SIC 8", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")
BASE = Path(__file__).resolve().parent
COLUMNS = ["timestamp", "lokasi", "latitude", "longitude", "air_temperature_c", "air_temperature_trend_pct", "relative_humidity_pct", "relative_humidity_trend_pct", "soil_moisture_pct", "moisture_trend_pct", "status_suhu", "status_rh", "status_tanah", "status_tren", "static_threshold_status", "warning_status", "mode"]
NUMBERS = ["latitude", "longitude", "air_temperature_c", "air_temperature_trend_pct", "relative_humidity_pct", "relative_humidity_trend_pct", "soil_moisture_pct", "moisture_trend_pct"]
COLORS = {"Normal":"#16A085", "Waspada":"#E6A23C", "Siaga":"#E45E5E", "Initializing":"#778399"}
st.markdown('''<style>
 .block-container {padding-top:1.6rem; max-width:1450px}
 .hero {background:linear-gradient(112deg,#103C38,#1C6155);color:#fff;padding:22px 28px;border-radius:16px;margin-bottom:16px}
 .hero h1{margin:0;font-size:2.15rem;color:white}.hero p{margin:.4rem 0 0;color:#D4E9E1}
 [data-testid="stMetric"]{background:#f4f8f7;padding:12px 16px;border-radius:12px;border:1px solid #dbe9e4}
 @media(prefers-color-scheme:dark){[data-testid="stMetric"]{background:#1a2928;border-color:#3b5550}}
</style>''', unsafe_allow_html=True)

@st.cache_data(show_spinner=False, ttl=1)
def from_csv(path, modified):
    try:
        return pd.read_csv(path, on_bad_lines="skip")
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return pd.DataFrame(columns=COLUMNS)

def clean(df):
    if df.empty:
        return df
    df = df.copy()
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    for col in NUMBERS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Timestamps supplied by the ESP32 are simulated local wall-clock times (UTC+8), no timezone suffix.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for status_col in ["warning_status", "static_threshold_status", "status_suhu", "status_rh", "status_tanah", "status_tren", "mode"]:
        df[status_col] = df[status_col].fillna("").astype(str).str.strip()
    df["warning_status"] = df["warning_status"].replace("", "Unknown")
    return df.dropna(subset=["timestamp"]).reset_index(drop=True)

def status_badge(value):
    color = COLORS.get(value, "#778399")
    st.markdown(f'<span style="background:{color};color:white;padding:7px 13px;border-radius:20px;font-weight:700">{value}</span>', unsafe_allow_html=True)

def plot_line(data, keys, labels, title, unit, palette):
    fig = go.Figure()
    for col, label, color in zip(keys,labels,palette):
        if col in data.columns and data[col].notna().any():
            fig.add_trace(go.Scatter(x=data["timestamp"], y=data[col], mode="lines+markers", name=label,
                                     line={"color":color,"width":2.6}, marker={"size":6}, connectgaps=False))
    fig.update_layout(height=335,title=title, xaxis_title="Waktu pengamatan sintetis (UTC+8)", yaxis_title=unit,
                      margin=dict(t=55,b=20,l=5,r=5), hovermode="x unified", legend=dict(orientation="h",y=1.12),
                      paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=True,gridcolor="rgba(130,130,130,.12)")
    fig.update_yaxes(showgrid=True,gridcolor="rgba(130,130,130,.12)")
    st.plotly_chart(fig,use_container_width=True,config={"displaylogo":False})

st.markdown('<div class="hero"><h1>🌿 PeatGuard Monitoring</h1><p>IoT-Based Peatland Fire Early Warning with Trend Aware · SIC Batch 8</p></div>', unsafe_allow_html=True)
with st.sidebar:
    st.header("⚙️ Data & Tampilan")
    mode = st.radio("Sumber data",["CSV dari MQTT collector","Unggah CSV"],help="Collector MQTT berjalan di terminal terpisah")
    if mode == "CSV dari MQTT collector":
        filename = st.text_input("Nama/path file CSV", value="data_mqtt.csv")
        path = Path(filename).expanduser()
        if not path.is_absolute():path = BASE/path
        if path.exists():
            raw = from_csv(str(path), path.stat().st_mtime_ns)
            st.success(f"File tersedia: {path.name}")
        else:
            raw = pd.DataFrame(columns=COLUMNS)
            st.info("File CSV belum tersedia. Jalankan collector dan simulasi Wokwi.")
    else:
        upload = st.file_uploader("Pilih CSV hasil MQTT",type=["csv"])
        try: raw = pd.read_csv(upload) if upload else pd.DataFrame(columns=COLUMNS)
        except Exception as exc:
            st.error(f"CSV tidak dapat dibaca: {exc}")
            raw = pd.DataFrame(columns=COLUMNS)
    if mode == "CSV dari MQTT collector":
        status_path = path.with_suffix(".connection.json")
        if status_path.exists():
            try:
                info = json.loads(status_path.read_text(encoding="utf-8"))
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(info["heartbeat_utc"])).total_seconds()
                if age > 6:
                    st.error("🔴 Collector tidak aktif / heartbeat terhenti")
                elif info.get("connected"):
                    st.success("🟢 MQTT subscriber terhubung ke broker")
                    if info.get("last_message_utc"):
                        msg_age = (datetime.now(timezone.utc) - datetime.fromisoformat(info["last_message_utc"])).total_seconds()
                        if msg_age > 10:
                            st.caption("Tidak ada pesan baru (>10 detik); simulasi mungkin selesai.")
                        else:
                            st.caption("Pesan MQTT diterima baru-baru ini.")
                else:
                    st.warning("🟠 Collector aktif, broker belum terhubung")
            except (ValueError, KeyError, OSError):
                st.warning("Status koneksi MQTT belum dapat dibaca.")
        else:
            st.info("Status MQTT tidak tersedia. Jalankan mqtt_ke_csv.py versi terbaru untuk mengaktifkan heartbeat.")
    else:
        st.caption("Mode CSV unggahan: status MQTT tidak berlaku.")
    st.caption("Status MQTT di atas adalah koneksi collector→broker.")
    st.caption("Broker: broker.hivemq.com:1883")
    st.code("sic8/karhutla/banjarbaru/data",language=None)
    st.caption("Mode MQTT publik: topic dapat menerima data dari publisher lain.")

def show_dashboard():
    if mode == "CSV dari MQTT collector" and path.exists():
        source = from_csv(str(path),path.stat().st_mtime_ns)
    else:
        source = raw
    df = clean(source)
    if df.empty:
        st.warning("Belum ada pembacaan valid. Jalankan `python mqtt_ke_csv.py data_mqtt.csv` lalu simulasi Wokwi. Dashboard ini otomatis membaca ulang CSV setiap 2 detik.")
        st.stop()
    locations = sorted(df["lokasi"].dropna().astype(str).unique().tolist())
    if len(locations) > 1:
        loc = st.selectbox("Lokasi",["Semua lokasi"]+locations)
        if loc != "Semua lokasi":
            df = df[df["lokasi"].astype(str) == loc]
    if df.empty:
        st.warning("Tidak ada data untuk lokasi ini.")
        return
    # Preserve recorded order, including repeated timestamps when simulation scenarios restart.
    latest = df.iloc[-1]
    st.caption(f"📍 {latest['lokasi']}  ·  Pembacaan tercatat: {len(df)}  ·  Waktu terakhir (simulasi): {latest['timestamp']:%d %b %Y %H:%M}")
    # Identifikasi awal sesi dari timestamp mundur atau pergantian mode;
    # untuk rekaman satu skenario jumlahnya 1–25.
    session_start = 0
    for i in range(1, len(df)):
        if (df.iloc[i]["timestamp"] <= df.iloc[i-1]["timestamp"] or
            str(df.iloc[i]["mode"]) != str(df.iloc[i-1]["mode"])):
            session_start = i
    session_rows = len(df) - session_start
    current_mode = str(latest["mode"])
    if current_mode == "simulasi":
        st.markdown(f"**Pengamatan skenario: {min(session_rows,25)}/25 data · Jendela tren: {min(session_rows,24)}/24 pembacaan**")
        st.progress(min(session_rows,24)/24)
        st.caption("Dalam mode simulasi: 1 baris mewakili 1 jam sintetis. 25 baris mencakup jam ke-0 hingga jam ke-24. Status tren dapat dihitung mulai baris ke-24.")
    elif current_mode == "sensor":
        st.markdown(f"**Jendela tren: {min(session_rows,24)}/24 pembacaan**")
        st.progress(min(session_rows,24)/24)
        st.caption("Mode sensor mengambil nilai sekitar setiap 2 detik; 24 pembacaan bukan 24 jam.")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("🌡️ Suhu udara",f"{latest['air_temperature_c']:.1f} °C" if pd.notna(latest['air_temperature_c']) else "—")
    m2.metric("💧 Kelembapan udara",f"{latest['relative_humidity_pct']:.1f} %" if pd.notna(latest['relative_humidity_pct']) else "—")
    m3.metric("🌱 Kelembapan tanah (simulasi)",f"{latest['soil_moisture_pct']:.1f} %" if pd.notna(latest['soil_moisture_pct']) else "—")
    with m4:
        st.markdown("**Status terkini**")
        status_badge(str(latest["warning_status"]))
    if str(latest["warning_status"]) == "Initializing":
        st.info(
            "Status masih Initializing. "
            "Analisis tren dan status akhir akan tersedia "
            "setelah 24 pembacaan dalam satu skenario."
        )
    # Penjelasan indikator diambil langsung dari payload ESP32, bukan perkiraan dashboard.
    status_akhir = str(latest["warning_status"])
    if status_akhir in ("Normal", "Waspada", "Siaga"):
        st.subheader("Analisis Indikator Kewaspadaan")
        def tampil_indikator(nama, kolom_nilai, kolom_status, satuan):
            nilai = latest[kolom_nilai]
            status = str(latest[kolom_status]).strip()
            teks_nilai = f"{nilai:.1f}{satuan}" if pd.notna(nilai) else "tidak tersedia"
            if not status or status.lower() in ("nan", "none", "<na>"):
                status = "Belum tersedia"
            return f"{nama} menunjukkan status **{status}** dengan nilai **{teks_nilai}**"
        isi = "; ".join([
            tampil_indikator("Suhu udara", "air_temperature_c", "status_suhu", "°C"),
            tampil_indikator("Kelembapan relatif udara", "relative_humidity_pct", "status_rh", "%"),
            tampil_indikator("Kelembapan tanah simulasi", "soil_moisture_pct", "status_tanah", "%"),
        ])
        tren = str(latest["status_tren"]).strip()
        if not tren or tren.lower() in ("nan", "none", "<na>"):
            tren = "Belum tersedia"
        pesan = (
            f"**Status Kewaspadaan: {status_akhir}.** "
            f"{isi}. "
            f"Analisis tren menunjukkan status **{tren}**. "
            f"Berdasarkan aturan klasifikasi pada ESP32, "
            f"sistem menetapkan status akhir **{status_akhir}**. "
        )
        if status_akhir == "Siaga":
            st.error(pesan)
        elif status_akhir == "Waspada":
            st.warning(pesan)
        else:
            st.success(pesan)
    elif status_akhir == "Initializing":
        st.caption("Analisis indikator lengkap akan muncul setelah status akhir tersedia (minimal 24 pembacaan).")
    if df["mode"].ne("").any():
        st.caption("Mode dari firmware: " + str(latest["mode"] or "tidak disebutkan"))
    else:
        st.info("Payload MQTT yang diterima belum memuat field `mode` dari versi terbaru.")
    if df["static_threshold_status"].ne("").any():
        st.subheader("Perbandingan status peringatan")
        c_static, c_final = st.columns(2)
        with c_static:
            st.markdown("**Static threshold**")
            status_badge(str(latest["static_threshold_status"] or "Belum tersedia"))
        with c_final:
            st.markdown("**Status akhir / Trend-Aware**")
            status_badge(str(latest["warning_status"]))
        status_cols = ["timestamp", "static_threshold_status", "warning_status"]
        st.dataframe(df[status_cols].rename(columns={"timestamp":"Waktu simulasi", "static_threshold_status":"Static threshold", "warning_status":"Status akhir"}).tail(25),hide_index=True,use_container_width=True)
        st.caption("Perbedaan status kedua metode hanya ditampilkan dari payload. Perhitungan false alarm memerlukan label referensi skenario dan aturan evaluasi yang disepakati.")
    else:
        st.info("Perbandingan static threshold belum tersedia: field `static_threshold_status` masih kosong pada data yang diterima. Pastikan kode Wokwi sudah diperbarui dan dipublish.")
    st.subheader("Perubahan parameter lingkungan")
    plot_line(df,["soil_moisture_pct"],["Kelembapan tanah"],"Tren kelembapan tanah (simulasi)","Kelembapan tanah (%)",["#138D75"])
    left,right=st.columns(2)
    with left:
        plot_line(df,["air_temperature_c"],["Suhu udara"],"Suhu udara","Suhu (°C)",["#E58A33"])
    with right:
        plot_line(df,["relative_humidity_pct"],["Kelembapan relatif udara"],"Kelembapan udara","RH (%)",["#478DD4"])
    t1,t2 = st.columns([1.55,1])
    with t1:
        plot_line(df,["moisture_trend_pct","air_temperature_trend_pct","relative_humidity_trend_pct"],
                  ["Tren tanah","Tren suhu","Tren RH"],"Indikator tren regresi linear dari ESP32","Perubahan relatif tren (%)",["#138D75","#E58A33","#478DD4"])
        st.caption("Nilai tren dikirim oleh firmware ESP32, bukan dihitung ulang pada dashboard. Null pada tahap inisialisasi dibiarkan kosong.")
    with t2:
        st.markdown("#### Distribusi status")

        counts = df["warning_status"].value_counts().reindex(
            ["Initializing", "Normal", "Waspada", "Siaga"],
            fill_value=0
        )

        f = go.Figure(
            go.Bar(
                x=counts.values,
                y=counts.index,
                orientation="h",
                marker_color=[COLORS[s] for s in counts.index]
            )
        )

        f.update_layout(
            height=300,
            margin=dict(t=10, b=20, l=10, r=10),
            xaxis_title="Jumlah pembacaan",
            yaxis_title="",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(f, use_container_width=True)

        # Keterangan untuk status Initializing
        st.caption(
            "Initializing menunjukkan tahap pengumpulan "
            "data sebelum jendela analisis tren terpenuhi, "
            "bukan kategori kewaspadaan."
        )
    st.subheader("Riwayat pembacaan")
    show_cols = ["timestamp","air_temperature_c","relative_humidity_pct","soil_moisture_pct","moisture_trend_pct","static_threshold_status","warning_status","mode"]
    st.dataframe(df[show_cols].rename(columns={"timestamp":"Waktu simulasi", "air_temperature_c":"Suhu °C", "relative_humidity_pct":"RH %", "soil_moisture_pct":"Tanah simulasi %", "moisture_trend_pct":"Tren tanah %", "static_threshold_status":"Static threshold", "warning_status":"Status akhir", "mode":"Mode"}), hide_index=True,use_container_width=True,height=270)
    st.download_button("⬇️ Unduh rekaman CSV",df[COLUMNS].to_csv(index=False).encode("utf-8-sig"),file_name="peatguard_rekaman.csv",mime="text/csv")
    st.caption("⚠️ Nilai dari mode simulasi merupakan data sintetis, bukan pengukuran lapangan. Dashboard menampilkan keluaran firmware tanpa mengklaim keakuratan deteksi kebakaran atau menghitung false alarm tanpa label referensi.")

@st.fragment(run_every="2s")
def auto_refresh():
    show_dashboard()
auto_refresh()