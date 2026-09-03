"""Flask API untuk dashboard monitoring MODIS."""

import os
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, jsonify, request, send_file

from chart_plot import daily_volume_chart, energy_time_series
from connect_db import get_connection
from rumus import COLD_HEAT_DENSITY, HOT_HEAT_DENSITY

app = Flask(__name__)
app.json.sort_keys = False


def fetch_all(sql, params=()):
    """Jalankan query dan kembalikan seluruh hasil sebagai dictionary."""
    with get_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
    return rows


def fetch_one(sql, params=()):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def json_ready(value):
    """Ubah tipe MySQL/Python menjadi struktur yang aman untuk JSON."""
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def get_worker_state():
    return fetch_one(
        """
        SELECT *, GREATEST(0, TIMESTAMPDIFF(SECOND, NOW(), next_run_at)) seconds_remaining
        FROM worker_state WHERE id = 1
        """
    )


def get_volcanoes():
    return fetch_all(
        """
        SELECT v.id, v.name, COUNT(d.id) total_data, MAX(d.datetime) last_data,
            (SELECT status FROM collection_runs r WHERE r.volcano_id = v.id
             ORDER BY r.id DESC LIMIT 1) last_status,
            (SELECT started_at FROM collection_runs r WHERE r.volcano_id = v.id
             ORDER BY r.id DESC LIMIT 1) last_check,
            (SELECT rows_received FROM collection_runs r WHERE r.volcano_id = v.id
             ORDER BY r.id DESC LIMIT 1) last_rows_received,
            (SELECT rows_inserted FROM collection_runs r WHERE r.volcano_id = v.id
             ORDER BY r.id DESC LIMIT 1) last_rows_inserted
        FROM volcanoes v
        LEFT JOIN modis_data d ON d.volcano_id = v.id
        GROUP BY v.id, v.name
        ORDER BY v.name
        """
    )


def get_chart_data(volcanoes):
    """Siapkan seri numerik untuk grafik interaktif React."""
    series = {}
    for volcano in volcanoes:
        volcano_id = volcano["id"]
        daily = fetch_all(
            """
            SELECT DATE(observation_datetime) observation_date,
                SUM(volume_cold) volume_cold, SUM(volume_hot) volume_hot
            FROM lava_volume_calculations
            WHERE volcano_id = %s
            GROUP BY DATE(observation_datetime)
            ORDER BY observation_date
            """,
            (volcano_id,),
        )
        energy = fetch_all(
            """
            SELECT observation_datetime, effusion_cold, effusion_hot
            FROM lava_volume_calculations
            WHERE volcano_id = %s
            ORDER BY observation_datetime
            """,
            (volcano_id,),
        )
        for row in energy:
            cold = float(row["effusion_cold"])
            hot = float(row["effusion_hot"])
            row["mean_e"] = (cold + hot) / 2
            row["envelope"] = [min(cold, hot), max(cold, hot)]
        series[str(volcano_id)] = {"daily": daily, "energy": energy}
    return series


@app.get("/")
def index():
    return {
        "name": "MODIS Volcano Monitor API",
        "status": "ok",
        "endpoints": ["/api/dashboard", "/api/lava-volume", "/health"],
    }


@app.get("/api/dashboard")
def api_dashboard():
    modis_limit = max(1, min(request.args.get("modis_limit", 100, type=int), 500))
    run_limit = max(1, min(request.args.get("run_limit", 50, type=int), 200))

    modis_rows = fetch_all(
        """
        SELECT * FROM (
            SELECT d.id, v.name volcano_name, d.UNIX_Time, d.Sat, d.datetime,
                d.Longitude, d.Latitude, d.B21, d.B22, d.B6, d.B31, d.B32,
                d.SatZen, d.SatAzi, d.SunZen, d.SunAzi, d.Line, d.Samp,
                d.Nti, d.Glint, d.Excess, d.Temp, d.Err, d.created_at
            FROM modis_data d
            JOIN volcanoes v ON v.id = d.volcano_id
            ORDER BY d.id DESC
            LIMIT %s
        ) recent
        ORDER BY id ASC
        """,
        (modis_limit,),
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
    volcanoes = get_volcanoes()
    payload = {
        "volcanoes": volcanoes,
        "chart_data": get_chart_data(volcanoes),
        "runs": fetch_all(
            "SELECT * FROM collection_runs ORDER BY id DESC LIMIT %s", (run_limit,)
        ),
        "modis_data": modis_rows,
        "totals": totals,
        "worker": get_worker_state(),
        "settings": {
            "refresh_seconds": max(
                5, int(os.getenv("DASHBOARD_REFRESH_SECONDS", "30"))
            )
        },
        "generated_at": datetime.now().isoformat(),
    }
    return jsonify(json_ready(payload))


@app.get("/api/lava-volume")
def api_lava_volume():
    limit = max(1, min(request.args.get("limit", 500, type=int), 2000))
    summary = fetch_all(
        """
        SELECT v.id, v.name, COUNT(c.id) observations,
            COALESCE(MAX(c.cumulative_cold), 0) cumulative_cold,
            COALESCE(MAX(c.cumulative_hot), 0) cumulative_hot
        FROM volcanoes v
        LEFT JOIN lava_volume_calculations c ON c.volcano_id = v.id
        GROUP BY v.id, v.name
        ORDER BY v.name
        """
    )
    payload = {
        "calculations": fetch_all(
            """
            SELECT c.*, v.name volcano_name
            FROM lava_volume_calculations c
            JOIN volcanoes v ON v.id = c.volcano_id
            ORDER BY c.observation_datetime DESC, c.volcano_id
            LIMIT %s
            """,
            (limit,),
        ),
        "summary": summary,
        "chart_data": get_chart_data(summary),
        "constants": {
            "cold_heat_density": COLD_HEAT_DENSITY,
            "hot_heat_density": HOT_HEAT_DENSITY,
        },
    }
    return jsonify(json_ready(payload))


@app.get("/charts/daily-volume/<int:volcano_id>.png")
def daily_volume_png(volcano_id):
    volcano = fetch_one("SELECT name FROM volcanoes WHERE id = %s", (volcano_id,))
    if not volcano:
        return {"error": "Gunung tidak ditemukan"}, 404
    rows = fetch_all(
        """
        SELECT DATE(observation_datetime) observation_date,
            SUM(volume_cold) volume_cold, SUM(volume_hot) volume_hot
        FROM lava_volume_calculations
        WHERE volcano_id = %s
        GROUP BY DATE(observation_datetime)
        ORDER BY observation_date
        """,
        (volcano_id,),
    )
    return send_file(
        daily_volume_chart(rows, volcano["name"]),
        mimetype="image/png",
        as_attachment=request.args.get("download") == "1",
        download_name=f"volume-harian-{volcano_id}.png",
        max_age=0,
    )


@app.get("/charts/energy/<int:volcano_id>.png")
def energy_chart_png(volcano_id):
    volcano = fetch_one("SELECT name FROM volcanoes WHERE id = %s", (volcano_id,))
    if not volcano:
        return {"error": "Gunung tidak ditemukan"}, 404
    rows = fetch_all(
        """
        SELECT observation_datetime, effusion_cold, effusion_hot
        FROM lava_volume_calculations
        WHERE volcano_id = %s
        ORDER BY observation_datetime
        """,
        (volcano_id,),
    )
    return send_file(
        energy_time_series(rows, volcano["name"]),
        mimetype="image/png",
        as_attachment=request.args.get("download") == "1",
        download_name=f"mean-energy-{volcano_id}.png",
        max_age=0,
    )


@app.get("/api/status")
def api_status():
    limit = max(1, min(request.args.get("limit", 20, type=int), 100))
    rows = fetch_all("SELECT * FROM collection_runs ORDER BY id DESC LIMIT %s", (limit,))
    return jsonify(json_ready(rows))


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


@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("Kesalahan API: %s", error)
    return {"error": "Terjadi kesalahan pada backend"}, 500
