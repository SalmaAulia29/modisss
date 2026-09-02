"""Aplikasi web monitoring MODIS."""

import os
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request

from connect_db import get_connection
from lava_calculation import COLD_HEAT_DENSITY, HOT_HEAT_DENSITY

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


def fetch_all(sql, params=()):
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
    return rows


def fetch_one(sql, params=()):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def json_ready(row):
    return {
        key: value.isoformat() if isinstance(value, (date, datetime)) else value
        for key, value in row.items()
    }


def get_worker_state():
    return fetch_one(
        """
        SELECT *, GREATEST(0, TIMESTAMPDIFF(SECOND, NOW(), next_run_at)) seconds_remaining
        FROM worker_state WHERE id = 1
        """
    )


@app.get("/")
def dashboard():
    volcanoes = fetch_all(
        """
        SELECT v.id, v.name, COUNT(d.id) total_data, MAX(d.datetime) last_data,
            (SELECT status FROM collection_runs r WHERE r.volcano_id = v.id ORDER BY r.id DESC LIMIT 1) last_status,
            (SELECT started_at FROM collection_runs r WHERE r.volcano_id = v.id ORDER BY r.id DESC LIMIT 1) last_check
        FROM volcanoes v
        LEFT JOIN modis_data d ON d.volcano_id = v.id
        GROUP BY v.id, v.name
        ORDER BY v.name
        """
    )
    runs = fetch_all("SELECT * FROM collection_runs ORDER BY id DESC LIMIT 50")
    modis_rows = fetch_all(
        """
        SELECT d.id, v.name volcano_name, d.UNIX_Time, d.Sat, d.datetime,
            d.Longitude, d.Latitude, d.B21, d.B22, d.B6, d.B31, d.B32,
            d.SatZen, d.SatAzi, d.SunZen, d.SunAzi, d.Line, d.Samp,
            d.Nti, d.Glint, d.Excess, d.Temp, d.Err, d.created_at
        FROM modis_data d
        JOIN volcanoes v ON v.id = d.volcano_id
        ORDER BY d.id ASC
        LIMIT 100
        """
    )
    totals = fetch_one(
        """
        SELECT COUNT(*) total_runs,
            COALESCE(SUM(status = 'success'), 0) success_runs,
            COALESCE(SUM(status = 'failed'), 0) failed_runs,
            COALESCE(SUM(rows_inserted), 0) inserted,
            (SELECT COUNT(*) FROM modis_data) total_data
        FROM collection_runs
        """
    )
    return render_template(
        "dashboard.html",
        volcanoes=volcanoes,
        runs=runs,
        modis_rows=modis_rows,
        totals=totals,
        worker=get_worker_state(),
        refresh_seconds=int(os.getenv("DASHBOARD_REFRESH_SECONDS", "30")),
    )


@app.get("/lava-volume")
def lava_volume():
    rows = fetch_all(
        """
        SELECT c.*, v.name volcano_name
        FROM lava_volume_calculations c
        JOIN volcanoes v ON v.id = c.volcano_id
        ORDER BY c.observation_datetime DESC, c.volcano_id
        """
    )
    summary = fetch_all(
        """
        SELECT v.name, COUNT(c.id) observations,
            COALESCE(MAX(c.cumulative_cold), 0) cumulative_cold,
            COALESCE(MAX(c.cumulative_hot), 0) cumulative_hot
        FROM volcanoes v
        LEFT JOIN lava_volume_calculations c ON c.volcano_id = v.id
        GROUP BY v.id, v.name
        ORDER BY v.name
        """
    )
    return render_template(
        "lava_volume.html",
        rows=rows,
        summary=summary,
        cold_density=COLD_HEAT_DENSITY,
        hot_density=HOT_HEAT_DENSITY,
    )


@app.get("/api/status")
def api_status():
    limit = max(1, min(request.args.get("limit", 20, type=int), 100))
    rows = fetch_all("SELECT * FROM collection_runs ORDER BY id DESC LIMIT %s", (limit,))
    return jsonify([json_ready(row) for row in rows])


@app.get("/api/worker-status")
def api_worker_status():
    state = get_worker_state()
    return jsonify(json_ready(state)) if state else ({"status": "unknown"}, 404)


@app.get("/health")
def health():
    try:
        fetch_one("SELECT 1 ok")
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        app.logger.exception("Health check gagal")
        return {"status": "error", "database": str(exc)}, 503
