"""Analisis terpadu grafik anomali termal.

Satu-satunya sumber perhitungan seri energi: hasil B1/B3 (kumulatif), indeks
gabungan power-volume, dan linear fitting fase. Dipakai bersama oleh API
dashboard (React) dan endpoint gambar PNG sehingga nilai & jumlah baris pada
grafik interaktif selalu sama dengan grafik yang diunduh.
"""

import datetime as _dt
import math

_FIT_MINIMUM_POINTS = 3
_FIT_PENALTY = 0.005


def add_calculation_outputs(rows):
    """Tambahkan hasil B1/B3 dalam urutan waktu yang konsisten.

    Untuk setiap baris setelah baris pertama, integrasi memakai nilai baris
    sebelumnya: hasil sebelumnya + (delta waktu baris ini x nilai sebelumnya).
    """
    indexed_rows = list(enumerate(rows))
    groups = {}
    for index, row in indexed_rows:
        groups.setdefault(row["volcano_id"], []).append((index, row))

    calculated = {}
    for group in groups.values():
        group.sort(key=lambda item: item[1]["observation_datetime"])
        block1_e_cold = block1_e_hot = 0.0
        block1_q_cold = block1_q_hot = 0.0
        cumulative_cold = cumulative_hot = 0.0
        cumulative_q_cold = cumulative_q_hot = 0.0

        for position, (index, original_row) in enumerate(group):
            row = dict(original_row)
            effusion_cold = float(row["effusion_cold"] or 0)
            effusion_hot = float(row["effusion_hot"] or 0)
            heat_cold = float(row["heat_flux_cold"] or 0)
            heat_hot = float(row["heat_flux_hot"] or 0)
            delta = int(row["delta_seconds"] or 0)

            block1_e_cold += effusion_cold
            block1_e_hot += effusion_hot
            block1_q_cold += heat_cold
            block1_q_hot += heat_hot

            if position == 0:
                cumulative_cold = effusion_cold
                cumulative_hot = effusion_hot
                cumulative_q_cold = heat_cold
                cumulative_q_hot = heat_hot
            else:
                previous = group[position - 1][1]
                cumulative_cold += float(previous["effusion_cold"] or 0) * delta
                cumulative_hot += float(previous["effusion_hot"] or 0) * delta
                cumulative_q_cold += float(previous["heat_flux_cold"] or 0) * delta
                cumulative_q_hot += float(previous["heat_flux_hot"] or 0) * delta

            row["cum_e_cold_block1"] = block1_e_cold
            row["cum_e_hot_block1"] = block1_e_hot
            row["mean_e_block1"] = (block1_e_cold + block1_e_hot) / 2
            row["cum_q_cold_block1"] = block1_q_cold
            row["cum_q_hot_block1"] = block1_q_hot
            row["mean_q_block1"] = (block1_q_cold + block1_q_hot) / 2
            row["cumulative_cold"] = cumulative_cold
            row["cumulative_hot"] = cumulative_hot
            row["mean_e_block3"] = (cumulative_cold + cumulative_hot) / 2
            row["mean_e"] = (cumulative_cold + cumulative_hot) / 2
            row["cumulative_q_cold"] = cumulative_q_cold
            row["cumulative_q_hot"] = cumulative_q_hot
            row["mean_q"] = (cumulative_q_cold + cumulative_q_hot) / 2
            row["envelope"] = [min(cumulative_cold, cumulative_hot), max(cumulative_cold, cumulative_hot)]
            row["power_envelope"] = [min(cumulative_q_cold, cumulative_q_hot), max(cumulative_q_cold, cumulative_q_hot)]
            calculated[index] = row

    return [calculated[index] for index in range(len(rows))]


def _to_millis(value):
    """Ubahlah nilai waktu (datetime/string) menjadi epoch milidetik."""
    if isinstance(value, _dt.datetime):
        return value.timestamp() * 1000.0
    if isinstance(value, _dt.date):
        return _dt.datetime(value.year, value.month, value.day).timestamp() * 1000.0
    text = str(value).strip()
    if not text:
        return float("nan")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return _dt.datetime.fromisoformat(text.replace(" ", "T")).timestamp() * 1000.0


def _linear_fit_segments(points):
    """Bagi seri titik menjadi fase dengan slope stabil (dynamic programming).

    Meniru algoritma yang dipakai UI React agar garis spektrum kedua sisi sama:
    observasi ketiga hingga akhir, penalti 0.005 per fase, tiap fase minimal
    3 titik. Mengembalikan daftar fase beserta slope/intercept skala-natural.
    Setiap elemen ``points`` adalah ``(indeks_baris_asli, epoch_milidetik, nilai_y)``.
    """
    if len(points) < 5:
        return []
    fit_points = points[2:]
    origin = fit_points[0][1]
    raw_values = [p[2] for p in fit_points]
    scale = (max(raw_values) - min(raw_values)) or 1.0
    items = [
        {"index": p[0], "x": (p[1] - origin) / 86400000.0, "y": p[2] / scale}
        for p in fit_points
    ]
    if len(items) < _FIT_MINIMUM_POINTS:
        return []

    cache = {}

    def fit(start, end):
        key = (start, end)
        if key in cache:
            return cache[key]
        segment = items[start:end]
        count = len(segment)
        mean_x = sum(p["x"] for p in segment) / count
        mean_y = sum(p["y"] for p in segment) / count
        denominator = sum((p["x"] - mean_x) ** 2 for p in segment)
        slope = sum((p["x"] - mean_x) * (p["y"] - mean_y) for p in segment) / denominator if denominator else 0.0
        intercept = mean_y - slope * mean_x
        residual = sum((p["y"] - (slope * p["x"] + intercept)) ** 2 for p in segment)
        result = {"slope": slope, "intercept": intercept, "residual": residual}
        cache[key] = result
        return result

    count = len(items)
    costs = [float("inf")] * (count + 1)
    phases = [[] for _ in range(count + 1)]
    costs[0] = 0.0
    for end in range(_FIT_MINIMUM_POINTS, count + 1):
        for start in range(0, end - _FIT_MINIMUM_POINTS + 1):
            if not math.isfinite(costs[start]):
                continue
            candidate = costs[start] + fit(start, end)["residual"] + _FIT_PENALTY
            if candidate < costs[end]:
                costs[end] = candidate
                phases[end] = phases[start] + [start]

    boundaries = phases[count]
    segments = []
    for phase_index, start in enumerate(boundaries):
        end = boundaries[phase_index + 1] if phase_index + 1 < len(boundaries) else count
        segments.append({"start": start, "end": end, "scale": scale, **fit(start, end)})
    return segments


def annotate_energy_rows(rows):
    """Tambahkan envelope gabungan, titik tengah, dan linear fitting fase."""
    out = [dict(row) for row in rows]

    power_cold = [abs(float(row.get("cumulative_q_cold") or 0)) for row in out]
    power_hot = [abs(float(row.get("cumulative_q_hot") or 0)) for row in out]
    volume_cold = [abs(float(row.get("cumulative_cold") or 0)) for row in out]
    volume_hot = [abs(float(row.get("cumulative_hot") or 0)) for row in out]
    power_scale = max(1.0, *(power_cold + power_hot)) if out else 1.0
    volume_scale = max(1.0, *(volume_cold + volume_hot)) if out else 1.0

    points = []
    for index, row in enumerate(out):
        timestamp = _to_millis(row.get("observation_datetime"))
        cold_index = (abs(float(row.get("cumulative_q_cold") or 0)) / power_scale +
                      abs(float(row.get("cumulative_cold") or 0)) / volume_scale) / 2
        hot_index = (abs(float(row.get("cumulative_q_hot") or 0)) / power_scale +
                     abs(float(row.get("cumulative_hot") or 0)) / volume_scale) / 2
        row["combined_power_scale"] = power_scale
        row["combined_volume_scale"] = volume_scale
        row["combined_envelope"] = [min(cold_index, hot_index), max(cold_index, hot_index)]
        row["combined_midpoint"] = (cold_index + hot_index) / 2
        row["combined_fit_1"] = None
        if math.isfinite(timestamp) and math.isfinite(row["combined_midpoint"]):
            points.append((index, timestamp, row["combined_midpoint"]))

    fit_segments = _linear_fit_segments(points)
    if fit_segments:
        origin = points[2][1]
        for segment_number, segment in enumerate(fit_segments):
            first = points[2 + segment["start"]]
            last = points[2 + segment["end"] - 1]
            key = "combined_fit_%d" % (segment_number + 1)
            slope_key = "combined_fit_slope_%d" % (segment_number + 1)
            for row in out:
                row[key] = None
                row[slope_key] = segment["slope"] * segment["scale"]
            _set_fit(out, first[0], key, (segment["slope"] * (first[1] - origin) / 86400000.0 + segment["intercept"]) * segment["scale"])
            _set_fit(out, last[0], key, (segment["slope"] * (last[1] - origin) / 86400000.0 + segment["intercept"]) * segment["scale"])

    return out


def _set_fit(rows, index, key, value):
    if 0 <= index < len(rows):
        rows[index][key] = value


def analyze_energy(rows):
    """Perhitungan seri energi lengkap: B1/B3 kumulatif + indeks gabungan + fit."""
    return annotate_energy_rows(add_calculation_outputs(rows))