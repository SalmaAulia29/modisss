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
    """Hitung satu garis regresi linear untuk seluruh seri observasi."""
    return [(0, len(y), np.polyfit(x, y, 1))] if len(y) >= 2 else []


def energy_time_series(rows, volcano_name):
    """Plot MeanE blok ketiga dengan envelope Ecold dan Ehot."""
    figure, axis = _figure(f"Scatter / Time Series MeanE · {volcano_name}", "Nilai E kumulatif (m³)")
    if not rows:
        axis.text(0.5, 0.5, "Belum ada data", color=MUTED, ha="center", va="center", transform=axis.transAxes)
        return _png_response(figure)

    dates = [row["observation_datetime"] for row in rows]
    cold = np.asarray([float(row["cumulative_cold"]) for row in rows])
    hot = np.asarray([float(row["cumulative_hot"]) for row in rows])
    mean = (cold + hot) / 2
    lower, upper = np.minimum(cold, hot), np.maximum(cold, hot)
    x = mdates.date2num(dates) - mdates.date2num(dates[0])

    axis.fill_between(dates, lower, upper, color=ENVELOPE, alpha=0.22, label="Envelope estimasi E")
    axis.plot(dates, cold, color=COLD, linewidth=1.8, label="Ecold")
    axis.plot(dates, hot, color=HOT, linewidth=1.8, label="Ehot")
    axis.scatter(dates, mean, color=MEAN, edgecolors=BACKGROUND, linewidths=0.7, s=30, zorder=4, label="MeanE")
    for fit_number, (start, end, coefficients) in enumerate(_phase_regressions(x, mean), 1):
        axis.plot(dates[start:end], np.polyval(coefficients, x[start:end]), color=MEAN, linewidth=2.2,
                  label="Linear fitting" if fit_number == 1 else None)

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
        ncol=2,
    )
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
