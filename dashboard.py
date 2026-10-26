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
COLUMNS = ["timestamp", "lokasi", "latitude", "longitude", "air_temperature_c", "air_temperature_trend_pct", "relative_humidity_pct", "relative_humidity_trend_pct", "soil_moisture_pct", "moisture_trend_pct", "status_suhu", "status_rh", "status_tanah", "status_tren", "static_threshold_status", "warning_status", "mode", "skenario"]
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
    for status_col in ["warning_status", "static_threshold_status", "status_suhu", "status_rh", "status_tanah", "status_tren", "mode", "skenario"]:
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
     # Informasi teknis MQTT dibuat ringkas dalam expander.
    with st.expander("ℹ️ Informasi Koneksi MQTT"):
        st.markdown("**Broker:** `broker.hivemq.com:1883`")
        st.markdown("**Topic:** `sic8/karhutla/banjarbaru/data`")

        st.caption(
            "Indikator koneksi menunjukkan hubungan Python subscriber "
            "dengan broker MQTT, bukan secara langsung koneksi ESP32 di Wokwi."
        )

        st.caption(
            "Broker MQTT bersifat publik sehingga topic dapat menerima "
            "pesan dari publisher lain. Pastikan sumber data sesuai "
            "sebelum digunakan sebagai hasil pengujian."
        )

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
    # Bagi pengujian berdasarkan pergantian skenario, reset waktu,
    # dan permulaan tahap Initializing pada run baru.
    start_flags = [True]
    for i in range(1, len(df)):
        prev, curr = df.iloc[i - 1], df.iloc[i]
        is_new = (
            curr["timestamp"] <= prev["timestamp"]
            or str(curr["mode"]) != str(prev["mode"])
            or str(curr["skenario"]) != str(prev["skenario"])
            or (curr["warning_status"] == "Initializing"
                and prev["warning_status"] != "Initializing")
        )
        start_flags.append(is_new)
    df["run_id"] = pd.Series(start_flags, index=df.index).cumsum()
    sesi_list = [g.copy().reset_index(drop=True) for _, g in df.groupby("run_id", sort=True)]
    labels = [f"Run {i+1} · {str(g['skenario'].iloc[0]) or str(g['mode'].iloc[0])} · {len(g)} data"
              for i, g in enumerate(sesi_list)]
    pilihan = st.selectbox("Sesi pengujian yang ditampilkan", list(range(len(labels))),
                          index=len(labels)-1, format_func=lambda i: labels[i])
    sesi = sesi_list[pilihan]
    latest = sesi.iloc[-1]
    session_rows = len(sesi)
    current_mode = str(latest["mode"])
    st.caption(f"📍 {latest['lokasi']} · Skenario: {latest['skenario'] or 'Sensor'} "
               f"· Data sesi: {session_rows} · Waktu terakhir: {latest['timestamp']:%d %b %Y %H:%M}")
    if current_mode == "simulasi":
        st.markdown(f"**Pengamatan skenario: {min(session_rows,72)}/72 data · Jendela tren: "
                    f"{min(session_rows,24)}/24 pembacaan**")
        st.progress(min(session_rows,72)/72)
        st.caption("72 baris mencakup jam sintetis ke-0 sampai ke-71. "
                   "23 baris awal Initializing; 49 baris berikutnya dapat dievaluasi.")
    elif current_mode == "sensor":
        st.markdown(f"**Jendela tren: {min(session_rows,24)}/24 pembacaan**")
        st.progress(min(session_rows,24)/24)
        st.caption("Mode sensor: pembacaan berkala bukan representasi 24 jam.")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("🌡️ Suhu udara",f"{latest['air_temperature_c']:.1f} °C" if pd.notna(latest['air_temperature_c']) else "—")
    m2.metric("💧 Kelembapan udara",f"{latest['relative_humidity_pct']:.1f} %" if pd.notna(latest['relative_humidity_pct']) else "—")
    m3.metric("🌱 Kelembapan tanah (simulasi)",f"{latest['soil_moisture_pct']:.1f} %" if pd.notna(latest['soil_moisture_pct']) else "—")
    with m4:
        st.markdown("**Status terkini**")
        status_badge(str(latest["warning_status"]))
    if str(latest["warning_status"]) == "Initializing":
        st.info("Status masih Initializing. Keputusan Trend-Aware tersedia mulai pembacaan ke-24.")
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
        pesan = (f"**Status Kewaspadaan: {status_akhir}.** {isi}. "
                 f"Analisis tren menunjukkan status **{tren}**. "
                 "Status akhir ditentukan oleh aturan gabungan ESP32. "
                 "Nilai simulasi bukan bukti kebakaran aktual.")
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
    if sesi["static_threshold_status"].ne("").any():
        st.subheader("Perbandingan Static Threshold dan Trend-Aware")
        c_static, c_final = st.columns(2)
        with c_static:
            st.markdown("**Static Threshold**")
            status_badge(str(latest["static_threshold_status"] or "Belum tersedia"))
        with c_final:
            st.markdown("**Trend-Aware**")
            status_badge(str(latest["warning_status"]))

        st.markdown("#### Selisih Alarm dan Peringatan Lebih Dini")
        alarm_levels = ["Waspada", "Siaga"]
        valid_levels = ["Normal", "Waspada", "Siaga"]
        # Persis pendekatan analisis_selisih.py: evaluasi hanya sesudah Initializing.
        ev = sesi["warning_status"].isin(valid_levels)
        evaluated = sesi.loc[ev].copy()
        sa = evaluated["static_threshold_status"].isin(alarm_levels)
        ta = evaluated["warning_status"].isin(alarm_levels)
        jumlah_s = int(sa.sum())
        jumlah_t = int(ta.sum())
        delta = jumlah_t - jumlah_s
        k0, k1, k2, k3 = st.columns(4)
        k0.metric("Baris dievaluasi", f"{len(evaluated)}/{len(sesi)}")
        k1.metric("Alarm Static", f"{jumlah_s}")
        k2.metric("Alarm Trend-Aware", f"{jumlah_t}")
        k3.metric("Selisih alarm (Trend − Static)", f"{delta:+d}")
        st.caption("Alarm = pembacaan berstatus Waspada atau Siaga; bukan jumlah kejadian alarm terpisah. "
                   "Initializing tidak dihitung sebagai alarm maupun Normal.")

        # Sama dengan definisi lead_waspada / lead_siaga pada analisis_selisih.py.
        def first_position(col, min_level):
            tingkat = {"Normal": 0, "Waspada": 1, "Siaga": 2}
            for i, row in sesi.iterrows():
                if row["warning_status"] not in valid_levels:
                    continue
                if tingkat.get(str(row[col]), -1) >= min_level:
                    return i
            return None

        lead_rows = []
        for name, level in [("Waspada atau lebih", 1), ("Siaga", 2)]:
            ps = first_position("static_threshold_status", level)
            pt = first_position("warning_status", level)
            # Timestamp hanya ditafsirkan sebagai jam sintetis dalam mode simulasi.
            if ps is not None and pt is not None:
                dt = (sesi.loc[ps, "timestamp"] - sesi.loc[pt, "timestamp"]).total_seconds()/3600
                hasil_lead = f"{dt:+.1f} jam sintetis" if current_mode == "simulasi" else f"{dt:+.1f} jam timestamp"
            elif pt is not None:
                hasil_lead = "Hanya Trend-Aware mendeteksi"
            elif ps is not None:
                hasil_lead = "Hanya Static mendeteksi"
            else:
                hasil_lead = "Tidak ada deteksi"
            lead_rows.append({
                "Tingkat peringatan": name,
                "Static pertama (baris)": ps+1 if ps is not None else "—",
                "Trend pertama (baris)": pt+1 if pt is not None else "—",
                "Static pertama (waktu)": sesi.loc[ps, "timestamp"].strftime("%d-%m %H:%M") if ps is not None else "—",
                "Trend pertama (waktu)": sesi.loc[pt, "timestamp"].strftime("%d-%m %H:%M") if pt is not None else "—",
                "Peringatan lebih dini (Static − Trend)": hasil_lead,
            })
        st.dataframe(pd.DataFrame(lead_rows), hide_index=True, use_container_width=True)

        st.markdown("#### Garis Waktu Deteksi")
        st.caption("Setiap kotak adalah satu pembacaan. Abu-abu = Initializing, hijau = Normal, "
                   "kuning = Waspada, merah = Siaga. Sumbu X menunjukkan jam sejak awal sesi pada simulasi.")
        time_axis = ((sesi["timestamp"] - sesi["timestamp"].iloc[0]).dt.total_seconds()/3600
                     if current_mode == "simulasi" else pd.Series(range(len(sesi)), dtype=float))
        fig_t = go.Figure()
        for method, col in [("Static Threshold", "static_threshold_status"),
                            ("Trend-Aware", "warning_status")]:
            for stat in ["Initializing", "Normal", "Waspada", "Siaga"]:
                # Static disembunyikan saat Trend-Aware masih Initializing HANYA di evaluasi,
                # tetapi garis waktu tetap memperlihatkan status Static yang tersedia.
                mask = sesi[col].eq(stat)
                if mask.any():
                    fig_t.add_trace(go.Scatter(
                        x=time_axis.loc[mask], y=[method]*int(mask.sum()),
                        mode="markers", name=stat, legendgroup=stat,
                        showlegend=(method == "Static Threshold" or
                                    not sesi["static_threshold_status"].eq(stat).any()),
                        marker={"symbol": "square", "size": 10, "color": COLORS[stat]},
                        customdata=sesi.loc[mask, "timestamp"].dt.strftime("%d-%m %H:%M"),
                        hovertemplate="%{y}<br>Jam/indeks: %{x}<br>%{customdata}<extra>" + stat + "</extra>"
                    ))
        if current_mode == "simulasi":
            fig_t.add_vrect(x0=0, x1=22.5, fillcolor="gray", opacity=.09,
                            layer="below", line_width=0,)
        fig_t.update_layout(height=295, xaxis_title=("Jam sintetis sejak awal sesi" if current_mode == "simulasi" else "Indeks pembacaan"),
                            yaxis_title="", legend={"orientation": "h", "y": 1.25},
                            margin=dict(t=55,b=20,l=5,r=5),
                            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_t, use_container_width=True)

        st.markdown("#### Perbandingan Jumlah Alarm")
        bars = go.Figure(go.Bar(x=["Static Threshold", "Trend-Aware"],
                                y=[jumlah_s, jumlah_t],
                                marker_color=["#E6A23C", "#16A085"],
                                text=[jumlah_s, jumlah_t], textposition="outside"))
        bars.update_layout(height=260, yaxis_title="Pembacaan berstatus alarm",yaxis={"rangemode":"tozero"},
                           margin=dict(t=15,b=20,l=5,r=5),
                           paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(bars, use_container_width=True)
        st.caption("Perbandingan hanya menggunakan baris yang sudah menghasilkan keputusan akhir. "
                   "Static pada kode saat ini hanya berdasarkan kelembapan tanah, sedangkan "
                   "Trend-Aware menggunakan gabungan parameter dan tren. Selisih bukan false alarm.")
        status_cols = ["timestamp", "static_threshold_status", "warning_status"]
        st.dataframe(sesi[status_cols].rename(columns={"timestamp": "Waktu simulasi",
                     "static_threshold_status": "Static Threshold", "warning_status": "Trend-Aware"}),
                     hide_index=True,use_container_width=True,height=270)
    else:
        st.info("Field static_threshold_status belum tersedia pada data ini.")
    st.subheader("Perubahan parameter lingkungan")
    plot_line(sesi,["soil_moisture_pct"],["Kelembapan tanah"],"Tren kelembapan tanah (simulasi)","Kelembapan tanah (%)",["#138D75"])
    left,right=st.columns(2)
    with left:
        plot_line(sesi,["air_temperature_c"],["Suhu udara"],"Suhu udara","Suhu (°C)",["#E58A33"])
    with right:
        plot_line(sesi,["relative_humidity_pct"],["Kelembapan relatif udara"],"Kelembapan udara","RH (%)",["#478DD4"])
    t1,t2 = st.columns([1.55,1])
    with t1:
        plot_line(sesi,["moisture_trend_pct","air_temperature_trend_pct","relative_humidity_trend_pct"],
                  ["Tren tanah","Tren suhu","Tren RH"],"Indikator tren regresi linear dari ESP32","Perubahan relatif tren (%)",["#138D75","#E58A33","#478DD4"])
        st.caption("Nilai tren dikirim oleh firmware ESP32, bukan dihitung ulang pada dashboard. Null pada tahap inisialisasi dibiarkan kosong.")
    with t2:
        st.markdown("#### Distribusi status")
        counts = sesi["warning_status"].value_counts().reindex(["Initializing","Normal","Waspada","Siaga"],fill_value=0)
        f = go.Figure(go.Bar(x=counts.values,y=counts.index,orientation="h",marker_color=[COLORS[s] for s in counts.index]))
        f.update_layout(height=300,margin=dict(t=10,b=20,l=10,r=10), xaxis_title="Jumlah pembacaan",yaxis_title="",paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(f,use_container_width=True)
        st.caption("Initializing berarti data historis belum cukup untuk keputusan Trend-Aware, bukan kategori kewaspadaan.")
    st.subheader("Riwayat pembacaan")
    show_cols = ["timestamp","air_temperature_c","relative_humidity_pct","soil_moisture_pct","moisture_trend_pct","static_threshold_status","warning_status","mode","skenario"]
    st.dataframe(sesi[show_cols].rename(columns={"timestamp":"Waktu simulasi", "air_temperature_c":"Suhu °C", "relative_humidity_pct":"RH %", "soil_moisture_pct":"Tanah simulasi %", "moisture_trend_pct":"Tren tanah %", "static_threshold_status":"Static threshold", "warning_status":"Status akhir", "mode":"Mode", "skenario":"Skenario"}), hide_index=True,use_container_width=True,height=270)
    st.download_button("⬇️ Unduh rekaman CSV",sesi[COLUMNS].to_csv(index=False).encode("utf-8-sig"),file_name="peatguard_rekaman.csv",mime="text/csv")
    st.caption("⚠️ Nilai dari mode simulasi merupakan data sintetis, bukan pengukuran lapangan. Dashboard menampilkan keluaran firmware tanpa mengklaim keakuratan deteksi kebakaran atau menghitung false alarm tanpa label referensi.")

@st.fragment(run_every="2s")
def auto_refresh():
    show_dashboard()
auto_refresh()
