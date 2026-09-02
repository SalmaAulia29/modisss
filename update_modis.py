"""Collector MODVOLC dan proses worker berkala."""

import logging
import os
import socket
import time
from datetime import datetime, timedelta

import requests

from connect_db import get_connection
from lava_calculation import recalculate_lava_volumes

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("modis.worker")

VOLCANOES = {
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

SOURCE_URL = os.getenv(
    "MODIS_URL", "http://modis.higp.hawaii.edu/cgi-bin/mergeimage"
)
DEFAULT_START_DATE = os.getenv("DEFAULT_START_DATE", "2026-08-25")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
INSERT_SQL = """
    INSERT IGNORE INTO modis_data (
        volcano_id, UNIX_Time, Sat, datetime, Longitude, Latitude,
        B21, B22, B6, B31, B32, SatZen, SatAzi, SunZen, SunAzi,
        Line, Samp, Nti, Glint, Excess, Temp, Err
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
"""


def get_last_processed_date(volcano_id):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                (SELECT MAX(datetime) FROM modis_data WHERE volcano_id = %s),
                (SELECT MAX(target_date) FROM collection_runs
                 WHERE volcano_id = %s AND status IN ('success', 'no_data'))
            """,
            (volcano_id, volcano_id),
        )
        data_date, checked_date = cursor.fetchone()
        cursor.close()

    candidates = [
        value if isinstance(value, datetime) else datetime.combine(value, datetime.min.time())
        for value in (data_date, checked_date)
        if value
    ]
    return max(candidates) if candidates else datetime.strptime(DEFAULT_START_DATE, "%Y-%m-%d")


def create_run(volcano_name, volcano_id, target_date):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO collection_runs
                (volcano_id, volcano_name, target_date, status, worker)
            VALUES (%s, %s, %s, 'running', %s)
            """,
            (volcano_id, volcano_name, target_date.date(), socket.gethostname()),
        )
        connection.commit()
        run_id = cursor.lastrowid
        cursor.close()
    return run_id


def complete_run(run_id, status, received=0, inserted=0, message=None, http_status=None):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE collection_runs
            SET status = %s, rows_received = %s, rows_inserted = %s,
                message = %s, http_status = %s, finished_at = NOW()
            WHERE id = %s
            """,
            (status, received, inserted, message, http_status, run_id),
        )
        connection.commit()
        cursor.close()


def parse_modis_rows(payload, volcano):
    rows = []
    for raw_line in payload.splitlines():
        if not raw_line.strip() or raw_line.startswith("#") or "UNIX_Time" in raw_line:
            continue

        columns = raw_line.split()
        if len(columns) < 25:
            continue

        try:
            observed_at = datetime(*(int(columns[index]) for index in range(2, 7)))
            longitude, latitude = float(columns[7]), float(columns[8])
            inside_area = (
                volcano["lonmin"] <= longitude <= volcano["lonmax"]
                and volcano["latmin"] <= latitude <= volcano["latmax"]
            )
            if not inside_area:
                continue

            rows.append(
                (
                    volcano["volcano_id"],
                    int(columns[0]),
                    columns[1],
                    observed_at,
                    longitude,
                    latitude,
                    *(float(columns[index]) for index in range(9, 18)),
                    int(columns[18]),
                    int(columns[19]),
                    *(float(columns[index]) for index in range(20, 25)),
                )
            )
        except (TypeError, ValueError):
            logger.debug("Baris MODIS tidak valid dilewati: %s", raw_line)
    return rows


def collect_date(session, volcano_name, volcano, target_date):
    run_id = create_run(volcano_name, volcano["volcano_id"], target_date)
    params = {
        "maptype": "alerts",
        "jyear": target_date.strftime("%Y"),
        "jday": target_date.strftime("%j"),
        "jperiod": 1,
        "lonmin": volcano["lonmin"],
        "latmin": volcano["latmin"],
        "lonmax": volcano["lonmax"],
        "latmax": volcano["latmax"],
    }

    try:
        response = session.get(SOURCE_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" in content_type:
            complete_run(run_id, "no_data", message="Server mengembalikan HTML/tidak ada data", http_status=response.status_code)
            return 0

        rows = parse_modis_rows(response.text, volcano)
        inserted = 0
        if rows:
            with get_connection() as connection:
                cursor = connection.cursor()
                cursor.executemany(INSERT_SQL, rows)
                inserted = cursor.rowcount
                connection.commit()
                cursor.close()

        status = "success" if rows else "no_data"
        message = "Selesai" if rows else "Tidak ada hotspot dalam area"
        complete_run(run_id, status, len(rows), inserted, message, response.status_code)
        logger.info("%s %s: diterima=%d, baru=%d", volcano_name, target_date.date(), len(rows), inserted)
        return inserted
    except Exception as exc:
        complete_run(run_id, "failed", message=str(exc)[:1000])
        logger.exception("Pengambilan %s untuk %s gagal", volcano_name, target_date.date())
        return 0


def update_data_modis():
    total_inserted = 0
    with requests.Session() as session:
        session.headers.update({"User-Agent": "MODIS-Volcano-Monitor/1.0"})
        for volcano_name, volcano in VOLCANOES.items():
            target_date = get_last_processed_date(volcano["volcano_id"]) + timedelta(days=1)
            while target_date.date() <= datetime.now().date():
                total_inserted += collect_date(session, volcano_name, volcano, target_date)
                target_date += timedelta(days=1)

    calculated = recalculate_lava_volumes()
    logger.info("Siklus selesai: data_baru=%d, kalkulasi=%d", total_inserted, calculated)
    return total_inserted


def update_worker_state(status, interval_minutes, *, next_run_at=None, error=None, completed=False):
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE worker_state
            SET status = %s, interval_minutes = %s, worker = %s,
                next_run_at = %s, last_error = %s,
                last_started_at = IF(%s = 'running', NOW(), last_started_at),
                last_completed_at = IF(%s, NOW(), last_completed_at)
            WHERE id = 1
            """,
            (status, interval_minutes, socket.gethostname(), next_run_at, error, status, completed),
        )
        connection.commit()
        cursor.close()


def mark_interrupted_runs():
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE collection_runs
            SET status = 'failed', finished_at = NOW(),
                message = 'Proses terputus karena worker dimulai ulang'
            WHERE status = 'running' AND worker <> %s
            """,
            (socket.gethostname(),),
        )
        connection.commit()
        cursor.close()


def worker_loop():
    from bootstrap_db import bootstrap_database

    bootstrap_database()
    interval_minutes = max(1, int(os.getenv("FETCH_INTERVAL_MINUTES", "60")))
    interval_seconds = interval_minutes * 60
    mark_interrupted_runs()
    logger.info("Worker aktif dengan interval %d menit", interval_minutes)

    while True:
        cycle_started = time.monotonic()
        update_worker_state("running", interval_minutes)
        error = None
        try:
            update_data_modis()
        except Exception as exc:
            error = str(exc)[:1000]
            logger.exception("Siklus collector gagal")

        elapsed = time.monotonic() - cycle_started
        wait_seconds = max(1, interval_seconds - elapsed)
        next_run_at = datetime.now() + timedelta(seconds=wait_seconds)
        update_worker_state(
            "error" if error else "waiting",
            interval_minutes,
            next_run_at=next_run_at,
            error=error,
            completed=True,
        )
        logger.info("Pengambilan berikutnya pada %s", next_run_at.isoformat(timespec="seconds"))
        time.sleep(wait_seconds)


if __name__ == "__main__":
    from bootstrap_db import bootstrap_database

    bootstrap_database()
    update_data_modis()
