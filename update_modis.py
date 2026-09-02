from datetime import datetime, timedelta
import mysql.connector
import requests
from connect_db import get_connection

# ==============================
# KONFIGURASI GUNUNG & PARAMETER SPASIAL (BOUNDING BOX URL)
# ==============================
GUNUNG = {
    "Gunung Ibu": {
        "volcano_id": 1,
        "lonmin": 127.50,
        "lonmax": 127.75,
        "latmin": 1.35,
        "latmax": 1.60,
    },
    "Gunung Lewotolok": {
        "volcano_id": 2,
        "lonmin": 123.40,
        "lonmax": 123.60,
        "latmin": -8.40,
        "latmax": -8.20,
    },
}


def cek_tanggal_terakhir_di_db(volcano_id):
    db = get_connection()
    if not db:
        return None
    cursor = db.cursor()
    query = "SELECT datetime FROM modis_data WHERE volcano_id = %s ORDER BY datetime DESC LIMIT 1"
    cursor.execute(query, (volcano_id,))
    result = cursor.fetchone()
    cursor.close()
    db.close()

    if result:
        tanggal_terakhir = result[0]
        print(f"[INFO] Data terakhir di database untuk ID {volcano_id}: {tanggal_terakhir.strftime('%Y-%m-%d')}")
        return tanggal_terakhir
    else:
        default_date = datetime(2026, 8, 25)
        print(f"[INFO] Database kosong. Menggunakan tanggal default: {default_date.strftime('%Y-%m-%d')}")
        return default_date


def update_data_modis():
    print("=" * 60)
    print("SISTEM PEMBARUAN DATA MODIS OTOMATIS DIMULAI")
    print("=" * 60)

    for nama_gunung, info in GUNUNG.items():
        print(f"\nMemproses: {nama_gunung}...")
        last_date = cek_tanggal_terakhir_di_db(info["volcano_id"])
        if not last_date:
            print(f"[ERROR] Lewati {nama_gunung} karena gagal koneksi database.")
            continue

        target_date = last_date + timedelta(days=1)
        hari_ini = datetime.now()

        while target_date <= hari_ini:
            tgl_str = target_date.strftime('%Y-%m-%d')
            print(f"-> Mengecek tanggal: {tgl_str}...")

            jyear = target_date.strftime("%Y")
            jday = target_date.strftime("%j")
            periodemodis = 1  # Periode harian agar stabil

            # URL menggunakan parameter koordinat wilayah langsung (lonmin/latmin/lonmax/latmax)
            url= (
                f"http://modis.higp.hawaii.edu/cgi-bin/mergeimage?maptype=alerts"
                f"&jyear={jyear}&jday={jday}&jperiod={periodemodis}"
                f"&lonmin={info['lonmin']}&latmin={info['latmin']}"
                f"&lonmax={info['lonmax']}&latmax={info['latmax']}"
            )

            try:
                response = requests.get(url_pembimbing, timeout=30)
                if response.status_code == 200:
                    data_mentah = response.text.strip()

                    if not data_mentah or "<html>" in data_mentah.lower():
                        print(f"   [INFO] Tidak ada data dari server untuk tanggal {tgl_str}.")
                        target_date += timedelta(days=1)
                        continue

                    baris_data = data_mentah.split("\n")
                    list_to_insert = []

                    for baris in baris_data:
                        if not baris.strip() or baris.startswith("#") or "UNIX_Time" in baris:
                            continue

                        kolom = baris.split()
                        if len(kolom) >= 25:
                            try:
                                unix_time = int(kolom[0])
                                sat = kolom[1]
                                year = int(kolom[2])
                                mo = int(kolom[3])
                                dy = int(kolom[4])
                                hr = int(kolom[5])
                                mn = int(kolom[6])

                                if not (0 <= hr <= 23 and 0 <= mn <= 59 and 1 <= mo <= 12 and 1 <= dy <= 31):
                                    continue

                                dt_object = datetime(year, mo, dy, hr, mn)

                                lon = float(kolom[7])
                                lat = float(kolom[8])

                                # Filter keamanan ganda sesuai batas koordinat dictionary
                                if not (
                                    info["lonmin"] <= lon <= info["lonmax"]
                                    and info["latmin"] <= lat <= info["latmax"]
                                ):
                                    continue

                                b21 = float(kolom[9])
                                b22 = float(kolom[10])
                                b6 = float(kolom[11])
                                b31 = float(kolom[12])
                                b32 = float(kolom[13])
                                sat_zen = float(kolom[14])
                                sat_azi = float(kolom[15])
                                sun_zen = float(kolom[16])
                                sun_azi = float(kolom[17])
                                line = int(kolom[18])
                                samp = int(kolom[19])
                                nti = float(kolom[20])
                                glint = float(kolom[21])
                                excess = float(kolom[22])
                                temp = float(kolom[23])
                                err = float(kolom[24])

                                list_to_insert.append((
                                    info["volcano_id"], unix_time, sat, dt_object,
                                    lon, lat, b21, b22, b6, b31, b32,
                                    sat_zen, sat_azi, sun_zen, sun_azi,
                                    line, samp, nti, glint, excess, temp, err
                                ))
                            except Exception:
                                continue

                    if list_to_insert:
                        db = get_connection()
                        if db:
                            cursor = db.cursor()
                            query_insert = """
                                INSERT IGNORE INTO modis_data (
                                    volcano_id, UNIX_Time, Sat, datetime, 
                                    Longitude, Latitude, B21, B22, B6, B31, B32, 
                                    SatZen, SatAzi, SunZen, SunAzi, Line, Samp, 
                                    Nti, Glint, Excess, Temp, Err
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.executemany(query_insert, list_to_insert)
                            db.commit()
                            print(f"   [SUKSES] Berhasil memasukkan {cursor.rowcount} data baru ke database!")
                            cursor.close()
                            db.close()
                    else:
                        print(f"   [INFO] Ada respon server untuk {tgl_str}, tapi di luar wilayah koordinat.")

            except Exception as e:
                print(f"   [ERROR] Gagal terhubung ke server: {e}")

            target_date += timedelta(days=1)

        print(f"--- Proses untuk {nama_gunung} selesai ---\n")


if __name__ == "__main__":
    update_data_modis()