"""Pembuatan grafik API MODIS menggunakan Matplotlib."""

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import numpy as np
from matplotlib.figure import Figure

BACKGROUND = "#ffffff"
GRID = "#c7cdd4"
TEXT = "#1f2937"
MUTED = "#4b5563"
COLD = "#3498db"
HOT = "#ff7f0e"
MEAN = "#202938"
ENVELOPE = "#94a3b8"


def _figure(title, y_label):
    figure = Figure(figsize=(10, 5.6), facecolor=BACKGROUND, constrained_layout=True)
    axis = figure.subplots()
    axis.set_facecolor(BACKGROUND)
    axis.set_title(title, color=TEXT, fontsize=13, fontweight="semibold", pad=14)
    axis.set_xlabel("Waktu pengamatan", color=MUTED, fontsize=10, labelpad=10)
    axis.set_ylabel(y_label, color=MUTED, fontsize=10, labelpad=10)
    axis.tick_params(colors=MUTED, labelsize=8, length=3)
    axis.grid(True, color=GRID, linewidth=0.8, alpha=0.85)
    axis.set_axisbelow(True)
    for spine in axis.spines.values():
        spine.set_color("#7b8490")
        spine.set_linewidth(0.8)
    return figure, axis


def _png_response(figure):
    output = BytesIO()
    figure.savefig(
        output,
        format="png",
        dpi=150,
        facecolor=BACKGROUND,
        edgecolor=BACKGROUND,
        bbox_inches="tight",
    )
    output.seek(0)
    return output


def _phase_regressions(x, y):
    """Bagi seri menjadi fase dengan slope yang relatif stabil.

    Segmentasi dipilih dengan dynamic programming. Penalti kecil untuk setiap
    fase mencegah garis baru dibuat kecuali benar-benar menurunkan error fit.
    """
    minimum_points = 3
    if len(y) < minimum_points:
        return [(0, len(y), np.polyfit(x, y, 1))] if len(y) >= 2 else []

    y_scale = max(float(np.max(y) - np.min(y)), 1.0)
    normalized_y = y / y_scale
    cache = {}

    def fit(start, end):
        key = (start, end)
        if key not in cache:
            coefficients = np.polyfit(x[start:end], normalized_y[start:end], 1)
            residual = normalized_y[start:end] - np.polyval(coefficients, x[start:end])
            cache[key] = (coefficients, float(np.sum(residual ** 2)))
        return cache[key]

    costs = [float("inf")] * (len(y) + 1)
    phases = [[] for _ in range(len(y) + 1)]
    costs[0] = 0.0
    penalty = 0.005
    for end in range(minimum_points, len(y) + 1):
        for start in range(0, end - minimum_points + 1):
            if not np.isfinite(costs[start]):
                continue
            _, residual = fit(start, end)
            candidate = costs[start] + residual + penalty
            if candidate < costs[end]:
                costs[end] = candidate
                phases[end] = phases[start] + [start]

    boundaries = phases[-1]
    regressions = []
    for phase_number, start in enumerate(boundaries):
        end = boundaries[phase_number + 1] if phase_number + 1 < len(boundaries) else len(y)
        coefficients, _ = fit(start, end)
        regressions.append((start, end, coefficients * np.array([y_scale, y_scale])))
    return regressions


def _combined_envelope(power_cold, power_hot, volume_cold, volume_hot):
    """Buat satu envelope dari Power dan Volume yang beda orde besarnya."""
    power_scale = max(float(np.max(np.abs(np.r_[power_cold, power_hot]))), 1.0)
    volume_scale = max(float(np.max(np.abs(np.r_[volume_cold, volume_hot]))), 1.0)
    cold_index = (power_cold / power_scale + volume_cold / volume_scale) / 2
    hot_index = (power_hot / power_scale + volume_hot / volume_scale) / 2
    return (np.minimum(cold_index, hot_index), np.maximum(cold_index, hot_index),
            (cold_index + hot_index) / 2, power_scale, volume_scale)


def energy_time_series(rows, volcano_name):
    """Plot cumulative power dan volume dengan sumbu terpisah."""
    figure, axis = _figure(f"Cumulative Power & Volume · {volcano_name}", "Cumulative Power (J)")
    if not rows:
        axis.text(0.5, 0.5, "Belum ada data", color=MUTED, ha="center", va="center", transform=axis.transAxes)
        return _png_response(figure)

    dates = [row["observation_datetime"] for row in rows]
    cold = np.asarray([float(row["cumulative_cold"]) for row in rows])
    hot = np.asarray([float(row["cumulative_hot"]) for row in rows])
    power_cold = [float(rows[0]["heat_flux_cold"] or 0)]
    power_hot = [float(rows[0]["heat_flux_hot"] or 0)]
    for previous, current in zip(rows, rows[1:]):
        seconds = max(0, int((current["observation_datetime"] - previous["observation_datetime"]).total_seconds()))
        power_cold.append(power_cold[-1] + float(previous["heat_flux_cold"] or 0) * seconds)
        power_hot.append(power_hot[-1] + float(previous["heat_flux_hot"] or 0) * seconds)
    power_cold = np.asarray(power_cold)
    power_hot = np.asarray(power_hot)
    lower, upper, midpoint, power_scale, volume_scale = _combined_envelope(power_cold, power_hot, cold, hot)
    x = mdates.date2num(dates) - mdates.date2num(dates[0])

    volume_axis = axis.twinx()
    volume_axis.set_ylabel("Cumulative Volume (m³)", color=MUTED, fontsize=10, labelpad=10)
    volume_axis.tick_params(colors=MUTED, labelsize=8, length=3)
    volume_axis.grid(False)
    axis.set_ylim(0, 1.05)
    volume_axis.set_ylim(0, 1.05)
    volume_axis.fill_between(dates, lower, upper, color="#8795dc", alpha=0.30, label="Batas bawah--atas (indeks gabungan)")
    volume_axis.plot(dates, lower, color="#5b5bd6", linewidth=1.2)
    volume_axis.plot(dates, upper, color="#c75a88", linewidth=1.2)
    volume_axis.scatter(dates, midpoint, color=MEAN, edgecolors=BACKGROUND, linewidths=0.7, s=30, zorder=4, label="Titik tengah")
    axis.yaxis.set_major_formatter(lambda value, _: f"{value * power_scale:.2e}")
    volume_axis.yaxis.set_major_formatter(lambda value, _: f"{value * volume_scale:.2e}")

    axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
    figure.autofmt_xdate(rotation=30, ha="right")
    handles, labels = axis.get_legend_handles_labels()
    volume_handles, volume_labels = volume_axis.get_legend_handles_labels()
    axis.legend(
        handles + volume_handles,
        labels + volume_labels,
        loc="upper right",
        facecolor=BACKGROUND,
        edgecolor="#9aa3ad",
        labelcolor=TEXT,
        fontsize=8,
        framealpha=1,
        fancybox=False,
        ncol=2,
    )
    return _png_response(figure)


def thermal_anomaly_chart(rows, volcano_name):
    """Plot a compact five-panel figure, omitting observations without hotspots."""
    plot_rows = [row for row in rows if float(row.get("pixel_count") or 0) > 0]
    figure = Figure(figsize=(10, 14), facecolor=BACKGROUND, constrained_layout=True)
    axes = figure.subplots(5, 1, sharex=True)
    if not plot_rows:
        axes[0].text(0.5, 0.5, "Belum ada data hotspot", color=MUTED, ha="center", va="center", transform=axes[0].transAxes)
        return _png_response(figure)

    dates = [row["observation_datetime"] for row in plot_rows]
    panel_values = [
        ("(a) Jumlah Hotspot Terdeteksi", "pixel_count", "No. Hot Pixels Detected", 10),
        ("(b) Spectral Radiance Maximum", "max_b21", "B21max (W/m² sr µm)", 30),
        ("(c) Spectral Radiance Total", "sum_b21", "Σ B21 (W/m² sr µm)", 50),
    ]
    for axis, (title, field, y_label, y_max) in zip(axes[:3], panel_values):
        values = np.asarray([float(row[field] or 0) for row in plot_rows])
        axis.scatter(dates, values, color="#111111", edgecolors="#111111", linewidths=0.4, s=28, alpha=0.75)
        axis.vlines(dates, 0, values, color="#777777", alpha=0.5, linewidth=0.8)
        axis.set_title(title, loc="left", fontsize=10, color=TEXT, pad=4,
                       bbox={"facecolor": BACKGROUND, "edgecolor": "#7b8490", "pad": 3})
        axis.set_ylabel(y_label, color=MUTED, fontsize=9)
        axis.set_ylim(0, max(y_max, float(values.max()) * 1.08))
        axis.grid(True, color=GRID, linestyle=":", linewidth=0.8)

    heat_cold = np.asarray([float(row["heat_flux_cold"] or 0) for row in plot_rows])
    heat_hot = np.asarray([float(row["heat_flux_hot"] or 0) for row in plot_rows])
    heat_axis = axes[3]
    heat_axis.set_title("(d) Heat & Volume Flux", loc="left", fontsize=10, color=TEXT, pad=4,
                        bbox={"facecolor": BACKGROUND, "edgecolor": "#7b8490", "pad": 3})
    heat_axis.plot(dates, heat_cold, "o--", color="#1f77b4", markersize=4, linewidth=1, label="Qcold / Heat Flux cold (W)")
    heat_axis.plot(dates, heat_hot, "o--", color="#d62728", markersize=4, linewidth=1, label="Qhot / Heat Flux hot (W)")
    heat_axis.set_ylabel("Heat Flux (W)", color=MUTED, fontsize=9)
    heat_axis.set_ylim(0, max(6e9, float(max(heat_cold.max(), heat_hot.max())) * 1.08))
    heat_axis.grid(True, color=GRID, linestyle=":", linewidth=0.8)
    heat_axis.legend(fontsize=8, ncol=2, loc="upper right")

    cold = np.asarray([float(row["cumulative_cold"] or 0) for row in plot_rows])
    hot = np.asarray([float(row["cumulative_hot"] or 0) for row in plot_rows])
    power_cold = np.asarray([float(row.get("cumulative_q_cold") or 0) for row in plot_rows])
    power_hot = np.asarray([float(row.get("cumulative_q_hot") or 0) for row in plot_rows])
    power_axis = axes[4]
    volume_axis = power_axis.twinx()
    power_axis.set_title("(e) Cumulative Power & Volume", loc="left", fontsize=10, color=TEXT, pad=4,
                         bbox={"facecolor": BACKGROUND, "edgecolor": "#7b8490", "pad": 3})
    lower, upper, midpoint, power_scale, volume_scale = _combined_envelope(power_cold, power_hot, cold, hot)
    power_axis.set_ylim(0, 1.05)
    volume_axis.set_ylim(0, 1.05)
    volume_lower, volume_upper = lower, upper
    volume_axis.fill_between(dates, volume_lower, volume_upper, color="#8795dc", alpha=0.3, label="Cumulative Volume (m³)")
    volume_axis.plot(dates, cold, color=COLD, linewidth=1.2, label="Cumulative volume cold (m³)")
    volume_axis.plot(dates, hot, color=HOT, linewidth=1.2, label="Cumulative volume hot (m³)")
    mean_e = (cold + hot) / 2
    volume_axis.scatter(dates, mean_e, color=MEAN, s=22, zorder=4, label="Mean E (m³)")
    volume_axis.scatter(dates, midpoint, color=MEAN, s=22, zorder=5, label="Titik tengah")
    for phase_index, (start, end, coefficients) in enumerate(_phase_regressions(x, midpoint)):
        fit_x = x[start:end]
        fit_y = np.polyval(coefficients, fit_x)
        volume_axis.plot(dates[start:end], fit_y, color=MEAN, linewidth=2.0,
                         label="Linear fitting" if phase_index == 0 else None)
    power_axis.plot(dates, power_cold / power_scale, color="#e76f51", linewidth=1.1,
                    label="Cumulative Q cold (J)")
    power_axis.plot(dates, power_hot / power_scale, color="#c1121f", linewidth=1.1,
                    label="Cumulative Q hot (J)")
    power_axis.scatter(dates, (power_cold + power_hot) / (2 * power_scale), color="#9b2226",
                       s=22, zorder=4, label="Mean Q (J)")
    power_axis.yaxis.set_major_formatter(lambda value, _: f"{value * power_scale:.2e}")
    volume_axis.yaxis.set_major_formatter(lambda value, _: f"{value * volume_scale:.2e}")
    power_axis.set_ylabel("Cumulative Power (J)", color=MUTED, fontsize=9)
    volume_axis.set_ylabel("Cumulative Volume (m³)", color=MUTED, fontsize=9)
    power_axis.grid(True, color=GRID, linestyle=":", linewidth=0.8)

    for axis in axes:
        axis.tick_params(colors=MUTED, labelsize=8, length=3)
        for spine in axis.spines.values():
            spine.set_color("#7b8490")
            spine.set_linewidth(0.8)
    axes[-1].set_xlabel("Tanggal", color=MUTED, fontsize=9)
    axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=8))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    figure.suptitle(f"Anomali Termal (Modis Satellite-Band21) {volcano_name}", color=TEXT, fontsize=13, fontweight="semibold")
    return _png_response(figure)


def daily_volume_chart(rows, volcano_name):
    """Plot total volume interval cold dan hot yang dikelompokkan per hari."""
    figure, axis = _figure(f"Volume Lava Harian · {volcano_name}", "Volume (m³/hari)")
    if not rows:
        axis.text(0.5, 0.5, "Belum ada data", color=MUTED, ha="center", va="center", transform=axis.transAxes)
        return _png_response(figure)

    dates = [row["observation_date"] for row in rows]
    cold = [float(row["volume_cold"]) for row in rows]
    hot = [float(row["volume_hot"]) for row in rows]
    axis.plot(dates, cold, color=COLD, linewidth=1.9, label="Cold")
    axis.plot(dates, hot, color=HOT, linewidth=1.9, label="Hot")
    axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7))
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m-%Y"))
    figure.autofmt_xdate(rotation=30, ha="right")
    axis.legend(
        loc="upper right",
        facecolor=BACKGROUND,
        edgecolor="#9aa3ad",
        labelcolor=TEXT,
        fontsize=8,
        framealpha=1,
        fancybox=False,
    )
    return _png_response(figure)
