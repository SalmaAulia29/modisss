import os
from connect_db import get_connection

COLD_HEAT_DENSITY = float(os.getenv("COLD_HEAT_DENSITY", "150000000"))
HOT_HEAT_DENSITY = float(os.getenv("HOT_HEAT_DENSITY", "350000000"))

def recalculate_lava_volumes():
    """Hitung ulang seri volume agar cumulative sum selalu konsisten."""
    with get_connection() as db:
        read = db.cursor(dictionary=True)
        write = db.cursor()
        read.execute("""SELECT volcano_id,datetime observation_datetime,COUNT(*) pixel_count,
            SUM(B21) sum_b21,MAX(B21) max_b21 FROM modis_data
            WHERE B21 IS NOT NULL AND datetime IS NOT NULL
            GROUP BY volcano_id,datetime ORDER BY volcano_id,datetime""")
        groups = read.fetchall()
        # Reset hasil turunan dan nomor ID; sumber modis_data tidak diubah.
        write.execute("TRUNCATE TABLE lava_volume_calculations")
        previous, cumulative = {}, {}
        values = []
        for row in groups:
            volcano_id, observed = row["volcano_id"], row["observation_datetime"]
            delta = max(0, int((observed - previous[volcano_id]).total_seconds())) if volcano_id in previous else 0
            sum_b21 = float(row["sum_b21"])
            e_cold = max(0.0, 0.450 * sum_b21 - 0.127)
            e_hot = max(0.0, 0.164 * sum_b21 - 0.045)
            volume_cold, volume_hot = e_cold * delta, e_hot * delta
            cold_total, hot_total = cumulative.get(volcano_id, (0.0, 0.0))
            cold_total += volume_cold
            hot_total += volume_hot
            cumulative[volcano_id] = (cold_total, hot_total)
            previous[volcano_id] = observed
            values.append((volcano_id, observed, row["pixel_count"], sum_b21, row["max_b21"], delta,
                           e_cold, e_hot, e_cold*COLD_HEAT_DENSITY, e_hot*HOT_HEAT_DENSITY,
                           volume_cold, volume_hot, cold_total, hot_total))
        if values:
            write.executemany("""INSERT INTO lava_volume_calculations
              (volcano_id,observation_datetime,pixel_count,sum_b21,max_b21,delta_seconds,
               effusion_cold,effusion_hot,heat_flux_cold,heat_flux_hot,volume_cold,volume_hot,cumulative_cold,cumulative_hot)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", values)
        db.commit()
        read.close(); write.close()
    return len(values)
