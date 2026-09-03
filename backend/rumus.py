"""Rumus estimasi laju, heat flux, dan volume lava.

Modul ini tidak mengakses database agar rumus mudah digunakan ulang dan diuji.
"""

"""Rumus murni estimasi volume lava MODIS Band 21."""

import os
from dataclasses import dataclass


COLD_HEAT_DENSITY = float(os.getenv("COLD_HEAT_DENSITY", "150000000"))
HOT_HEAT_DENSITY = float(os.getenv("HOT_HEAT_DENSITY", "350000000"))


@dataclass(frozen=True)
class LavaEstimate:
    effusion_cold: float
    effusion_hot: float
    heat_flux_cold: float
    heat_flux_hot: float
    volume_cold: float
    volume_hot: float


def calculate_lava_estimate(sum_b21, delta_seconds):
    """Menghasilkan estimasi cold dan hot untuk satu interval pengamatan."""
    radiance = float(sum_b21)
    duration = max(0, int(delta_seconds))
    effusion_cold = max(0.0, 0.450 * radiance - 0.127)
    effusion_hot = max(0.0, 0.164 * radiance - 0.045)

    return LavaEstimate(
        effusion_cold=effusion_cold,
        effusion_hot=effusion_hot,
        heat_flux_cold=effusion_cold * COLD_HEAT_DENSITY,
        heat_flux_hot=effusion_hot * HOT_HEAT_DENSITY,
        volume_cold=effusion_cold * duration,
        volume_hot=effusion_hot * duration,
    )
