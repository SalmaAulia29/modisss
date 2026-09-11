"""Rumus estimasi laju, heat flux, dan volume lava.

Modul ini tidak mengakses database agar rumus mudah digunakan ulang dan diuji.
"""

"""Rumus murni estimasi volume lava MODIS Band 21."""

from dataclasses import dataclass


COLD_HEAT_DENSITY_FORMULA = 2600 * (1150 * 200 + 350000 * 0.45)
HOT_HEAT_DENSITY_FORMULA = 2600 * (1150 * 350 + 350000 * 0.45)
COLD_HEAT_DENSITY = COLD_HEAT_DENSITY_FORMULA
HOT_HEAT_DENSITY = HOT_HEAT_DENSITY_FORMULA


@dataclass(frozen=True)
class LavaEstimate:
    effusion_cold: float
    effusion_hot: float
    heat_flux_cold: float
    heat_flux_hot: float
    volume_cold: float
    volume_hot: float


def calculate_lava_estimate(sum_b21, delta_seconds, previous_effusion=None):
    """Hitung nilai observasi dan integrasi memakai nilai baris sebelumnya."""
    radiance = float(sum_b21)
    duration = max(0, int(delta_seconds))
    effusion_cold = 0.450 * radiance - 0.127
    effusion_hot = 0.164 * radiance - 0.045
    heat_flux_cold = effusion_cold * COLD_HEAT_DENSITY
    heat_flux_hot = effusion_hot * HOT_HEAT_DENSITY
    previous_cold, previous_hot = previous_effusion or (0.0, 0.0)

    return LavaEstimate(
        effusion_cold=effusion_cold,
        effusion_hot=effusion_hot,
        heat_flux_cold=heat_flux_cold,
        heat_flux_hot=heat_flux_hot,
        volume_cold=previous_cold * duration,
        volume_hot=previous_hot * duration,
    )
