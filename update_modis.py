import os
import socket
import time
from datetime import datetime, timedelta
import requests
from connect_db import get_connection
from lava_calculation import recalculate_lava_volumes

GUNUNG = {
    "Gunung Ibu": {"volcano_id": 1, "lonmin": 127.50, "lonmax": 127.75, "latmin": 1.35, "latmax": 1.60},
    "Gunung Lewotolok": {"volcano_id": 2, "lonmin": 123.40, "lonmax": 123.60, "latmin": -8.40, "latmax": -8.20},
}
SOURCE_URL = os.getenv("MODIS_URL", "http://modis.higp.hawaii.edu/cgi-bin/mergeimage")
DEFAULT_START_DATE = os.getenv("DEFAULT_START_DATE", "2026-08-25")

def last_date(volcano_id):
    with get_connection() as db:
        cursor = db.cursor()
        cursor.execute("""SELECT
            (SELECT MAX(datetime) FROM modis_data WHERE volcano_id=%s),
            (SELECT MAX(target_date) FROM collection_runs WHERE volcano_id=%s AND status IN ('success','no_data'))
        """, (volcano_id, volcano_id))
        data_date, checked_date = cursor.fetchone()
        cursor.close()
    candidates = [datetime.combine(value, datetime.min.time()) if not isinstance(value, datetime) else value
                  for value in (data_date, checked_date) if value]
    if not candidates:
        return datetime.strptime(DEFAULT_START_DATE, "%Y-%m-%d")
    return max(candidates)

def start_run(name, volcano_id, target_date):
    with get_connection() as db:
        cursor = db.cursor()
        cursor.execute("INSERT INTO collection_runs (volcano_id,volcano_name,target_date,status,worker) VALUES (%s,%s,%s,'running',%s)", (volcano_id, name, target_date.date(), socket.gethostname()))
        db.commit()
        run_id = cursor.lastrowid
        cursor.close()
    return run_id

def finish_run(run_id, status, received=0, inserted=0, message=None, http_status=None):
    with get_connection() as db:
        cursor = db.cursor()
        cursor.execute("UPDATE collection_runs SET status=%s,rows_received=%s,rows_inserted=%s,message=%s,http_status=%s,finished_at=NOW() WHERE id=%s", (status, received, inserted, message, http_status, run_id))
        db.commit()
        cursor.close()

def parse_rows(text, info):
    rows = []
    for line_text in text.splitlines():
        if not line_text.strip() or line_text.startswith("#") or "UNIX_Time" in line_text:
            continue
        col = line_text.split()
        if len(col) < 25:
            continue
        try:
            dt = datetime(*(int(col[i]) for i in range(2, 7)))
            lon, lat = float(col[7]), float(col[8])
            if not (info["lonmin"] <= lon <= info["lonmax"] and info["latmin"] <= lat <= info["latmax"]):
                continue
            rows.append((info["volcano_id"], int(col[0]), col[1], dt, lon, lat,
                         *(float(col[i]) for i in range(9, 18)), int(col[18]), int(col[19]),
                         *(float(col[i]) for i in range(20, 25))))
        except (ValueError, TypeError):
            continue
    return rows

def collect_date(name, info, target_date):
    run_id = start_run(name, info["volcano_id"], target_date)
    params = {"maptype": "alerts", "jyear": target_date.strftime("%Y"), "jday": target_date.strftime("%j"), "jperiod": 1,
              "lonmin": info["lonmin"], "latmin": info["latmin"], "lonmax": info["lonmax"], "latmax": info["latmax"]}
    try:
        response = requests.get(SOURCE_URL, params=params, timeout=30)
        response.raise_for_status()
        if "text/html" in response.headers.get("content-type", "").lower():
            finish_run(run_id, "no_data", message="Server mengembalikan HTML/tidak ada data", http_status=response.status_code)
            return
        rows = parse_rows(response.text, info)
        inserted = 0
        if rows:
            with get_connection() as db:
                cursor = db.cursor()
                cursor.executemany("""INSERT IGNORE INTO modis_data
                    (volcano_id,UNIX_Time,Sat,datetime,Longitude,Latitude,B21,B22,B6,B31,B32,SatZen,SatAzi,SunZen,SunAzi,Line,Samp,Nti,Glint,Excess,Temp,Err)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", rows)
                inserted = cursor.rowcount
                db.commit()
                cursor.close()
        finish_run(run_id, "success" if rows else "no_data", len(rows), inserted, "Selesai" if rows else "Tidak ada hotspot dalam area", response.status_code)
    except Exception as exc:
        finish_run(run_id, "failed", message=str(exc)[:1000])

def update_data_modis():
    for name, info in GUNUNG.items():
        target = last_date(info["volcano_id"]) + timedelta(days=1)
        while target.date() <= datetime.now().date():
            collect_date(name, info, target)
            target += timedelta(days=1)
    recalculate_lava_volumes()

def worker_loop():
    from bootstrap_db import bootstrap_database
    bootstrap_database()
    interval = int(os.getenv("FETCH_INTERVAL_MINUTES", "60")) * 60
    # Container lama dapat berhenti saat status masih "running" (restart/deploy).
    with get_connection() as db:
        cursor = db.cursor()
        cursor.execute("""UPDATE collection_runs SET status='failed', finished_at=NOW(),
            message='Proses terputus karena worker dimulai ulang'
            WHERE status='running' AND worker<>%s""", (socket.gethostname(),))
        db.commit()
        cursor.close()
    while True:
        try:
            update_data_modis()
        except Exception as exc:
            print(f"[ERROR] Siklus collector gagal: {exc}", flush=True)
        time.sleep(interval)

if __name__ == "__main__":
    update_data_modis()
