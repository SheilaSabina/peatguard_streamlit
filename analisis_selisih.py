import argparse
import sys

import pandas as pd

URUT = {"Normal": 0, "Waspada": 1, "Siaga": 2}
NAMA = {v: k for k, v in URUT.items()}


def bagi_run(df: pd.DataFrame) -> pd.Series:
    init = df["warning_status"].eq("Initializing")
    awal = (
        (init & ~init.shift(fill_value=True))
        | df["skenario"].ne(df["skenario"].shift())
        | df["mode"].ne(df["mode"].shift())
    )
    return awal.cumsum()


def baris_pertama(g: pd.DataFrame, mask: pd.Series):
    """Posisi (1-based, dihitung dari awal run) baris pertama yang memenuhi mask."""
    idx = g.index[mask]
    return int(idx[0]) + 1 if len(idx) else None


def analisis_run(nomor: int, g: pd.DataFrame) -> dict:
    g = g.reset_index(drop=True)
    ada_status = g["warning_status"].ne("Initializing")
    st = g["static_threshold_status"].map(URUT)
    fin = g["warning_status"].map(URUT)

    ev = ada_status
    hasil = {
        "run": nomor,
        "skenario": g["skenario"].iloc[0] or "(sensor)",
        "baris_total": len(g),
        "baris_dievaluasi": int(ev.sum()),
        "alarm_static": int(((st >= 1) & ev).sum()),
        "alarm_tren_aware": int(((fin >= 1) & ev).sum()),
    }
    hasil["selisih_alarm"] = hasil["alarm_tren_aware"] - hasil["alarm_static"]

    beda = ev & (st != fin)
    hasil["baris_beda_status"] = int(beda.sum())
    for a, b in [(0, 1), (0, 2), (1, 2), (1, 0), (2, 0), (2, 1)]:
        n = int((beda & (st == a) & (fin == b)).sum())
        if n or (a, b) in [(0, 1), (0, 2), (1, 2)]:
            hasil[f"{NAMA[a]}->{NAMA[b]}"] = n

    for label, minimal in [("waspada", 1), ("siaga", 2)]:
        ps = baris_pertama(g, ev & (st >= minimal))
        pt = baris_pertama(g, ev & (fin >= minimal))
        hasil[f"deteksi_{label}_static"] = ps if ps else "-"
        hasil[f"deteksi_{label}_tren"] = pt if pt else "-"
        if ps and pt:
            hasil[f"lead_{label}"] = ps - pt
        elif pt and not ps:
            hasil[f"lead_{label}"] = "static tidak mendeteksi"
        else:
            hasil[f"lead_{label}"] = "-"

    hasil["pelanggaran_tren_lebih_rendah"] = int((ev & (fin < st)).sum())
    return hasil


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="CSV hasil mqtt_ke_csv.py")
    ap.add_argument("--mode", default="simulasi", choices=["simulasi", "sensor", "semua"],
                    help="mode data yang dianalisis (default: simulasi)")
    ap.add_argument("--out", default="hasil_analisis.csv", help="file CSV hasil (default: hasil_analisis.csv)")
    a = ap.parse_args()

    df = pd.read_csv(a.csv, dtype=str, keep_default_na=False)
    for kol in ("mode", "skenario", "warning_status", "static_threshold_status"):
        if kol not in df.columns:
            sys.exit(f"Kolom '{kol}' tidak ada di {a.csv}. Pakai CSV dari mqtt_ke_csv.py versi terbaru.")
    if a.mode != "semua":
        df = df[df["mode"] == a.mode]
    if df.empty:
        sys.exit("Tidak ada baris yang cocok dengan mode yang dipilih.")
    df = df.reset_index(drop=True)
    df["run"] = bagi_run(df)

    tabel = pd.DataFrame([analisis_run(i + 1, g) for i, (_, g) in enumerate(df.groupby("run", sort=True))])
    tabel = tabel.fillna(0)

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 50)
    print(f"\nDianalisis: {len(df)} baris, {len(tabel)} run, mode = {a.mode}\n")
    print(tabel.to_string(index=False))
    tabel.to_csv(a.out, index=False)
    print(f"\nTabel disimpan ke {a.out}")

    bermasalah = int(tabel["pelanggaran_tren_lebih_rendah"].sum())
    if bermasalah:
        print(f"PERHATIAN: {bermasalah} baris tren-aware lebih rendah dari static "
              f"(tidak seharusnya terjadi dengan aturan sekarang).")
    print("Catatan: selisih = peringatan tambahan/lebih dini dari tren-aware, bukan false alarm "
          "(belum ada label kondisi sebenarnya).")


if __name__ == "__main__":
    main()
