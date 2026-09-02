import os
from flask import Flask, jsonify, render_template, request
from connect_db import get_connection
from lava_calculation import COLD_HEAT_DENSITY, HOT_HEAT_DENSITY

app = Flask(__name__)

def query(sql, params=()):
    with get_connection() as db:
        cursor = db.cursor(dictionary=True)
        cursor.execute(sql, params)
        result = cursor.fetchall()
        cursor.close()
    return result

@app.get("/")
def dashboard():
    summary = query("""SELECT v.id,v.name,COUNT(d.id) total_data,MAX(d.datetime) last_data,
      (SELECT status FROM collection_runs r WHERE r.volcano_id=v.id ORDER BY r.id DESC LIMIT 1) last_status,
      (SELECT started_at FROM collection_runs r WHERE r.volcano_id=v.id ORDER BY r.id DESC LIMIT 1) last_check
      FROM volcanoes v LEFT JOIN modis_data d ON d.volcano_id=v.id GROUP BY v.id,v.name ORDER BY v.name""")
    runs = query("SELECT * FROM collection_runs ORDER BY id DESC LIMIT 50")
    modis_rows = query("""SELECT d.id,v.name volcano_name,d.UNIX_Time,d.Sat,d.datetime,
      d.Longitude,d.Latitude,d.B21,d.B22,d.B6,d.B31,d.B32,d.SatZen,d.SatAzi,
      d.SunZen,d.SunAzi,d.Line,d.Samp,d.Nti,d.Glint,d.Excess,d.Temp,d.Err,d.created_at
      FROM modis_data d JOIN volcanoes v ON v.id=d.volcano_id
      ORDER BY d.id ASC LIMIT 100""")
    totals = query("""SELECT COUNT(*) total_runs,SUM(status='success') success_runs,
      SUM(status='failed') failed_runs,COALESCE(SUM(rows_inserted),0) inserted,
      (SELECT COUNT(*) FROM modis_data) total_data FROM collection_runs""")[0]
    return render_template("dashboard.html", summary=summary, runs=runs, modis_rows=modis_rows,
                           totals=totals, refresh=int(os.getenv("DASHBOARD_REFRESH_SECONDS", "30")))

@app.get("/api/status")
def api_status():
    runs = query("SELECT * FROM collection_runs ORDER BY id DESC LIMIT %s", (min(request.args.get("limit", 20, type=int), 100),))
    for row in runs:
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                row[key] = value.isoformat()
    return jsonify(runs)

@app.get("/lava-volume")
def lava_volume():
    rows = query("""SELECT c.*,v.name volcano_name FROM lava_volume_calculations c
      JOIN volcanoes v ON v.id=c.volcano_id ORDER BY c.observation_datetime DESC,c.volcano_id""")
    summary = query("""SELECT v.name,COUNT(c.id) observations,
      COALESCE(MAX(c.cumulative_cold),0) cumulative_cold,
      COALESCE(MAX(c.cumulative_hot),0) cumulative_hot
      FROM volcanoes v LEFT JOIN lava_volume_calculations c ON c.volcano_id=v.id
      GROUP BY v.id,v.name ORDER BY v.name""")
    return render_template("lava_volume.html", rows=rows, summary=summary,
                           cold_density=COLD_HEAT_DENSITY, hot_density=HOT_HEAT_DENSITY)

@app.get("/health")
def health():
    try:
        query("SELECT 1 ok")
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        return {"status": "error", "database": str(exc)}, 503
