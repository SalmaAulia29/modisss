"""Pembuatan grafik API MODIS menggunakan Matplotlib dan scikit-learn."""

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import numpy as np
from matplotlib.figure import Figure
from sklearn.linear_model import LinearRegression

BACKGROUND = "#ffffff"
GRID = "#c7cdd4"
TEXT = "#1f2937"
MUTED = "#4b5563"
COLD = "#3498db"
HOT = "#ff7f0e"
MEAN = "#202938"
TREND = "#6f42c1"


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


def energy_time_series(rows, volcano_name):
    """Plot MeanE, amplop Ecold/Ehot, dan tren linear MeanE."""
    figure, axis = _figure(f"Scatter / Time Series MeanE · {volcano_name}", "Nilai E (m³/s)")
    if not rows:
        axis.text(0.5, 0.5, "Belum ada data", color=MUTED, ha="center", va="center", transform=axis.transAxes)
        return _png_response(figure)

    dates = [row["observation_datetime"] for row in rows]
    cold = np.asarray([float(row["effusion_cold"]) for row in rows])
    hot = np.asarray([float(row["effusion_hot"]) for row in rows])
    mean = (cold + hot) / 2
    lower, upper = np.minimum(cold, hot), np.maximum(cold, hot)

    axis.fill_between(dates, lower, upper, color=COLD, alpha=0.09, label="Rentang Ecold–Ehot")
    axis.plot(dates, cold, color=COLD, linewidth=1.8, label="Ecold")
    axis.plot(dates, hot, color=HOT, linewidth=1.8, label="Ehot")
    axis.scatter(dates, mean, color=MEAN, edgecolors=BACKGROUND, linewidths=0.7, s=30, zorder=4, label="MeanE")

    if len(dates) >= 2:
        elapsed_days = np.asarray([(value - dates[0]).total_seconds() / 86400 for value in dates]).reshape(-1, 1)
        model = LinearRegression().fit(elapsed_days, mean)
        trend = model.predict(elapsed_days)
        axis.plot(dates, trend, color=TREND, linestyle="--", linewidth=1.5, label="Tren MeanE")

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
