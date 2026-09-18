"""Pembacaan DEM GeoTIFF untuk peta 3D.

Modul ini bertanggung jawab untuk:
- menemukan file DEM yang memang tersedia di project;
- membaca raster dengan rasterio dan melakukan downsampling untuk browser;
- mengubah koordinat grid ke EPSG:4326 bila CRS DEM berbeda;
- mengambil nilai elevasi DEM pada koordinat hotspot (lon/lat);
- membentuk Convex Hull dari titik hotspot.

Import rasterio dilakukan secara lazy agar kegagalan modul ini tidak ikut
menjatuhkan seluruh API. Pemanggil cukup menangkap ``DemError``.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path

# Ukuran maksimum sisi grid yang dikirim ke Plotly (target 100-200).
MAX_GRID_DIMENSION = 200

# Kandidat nama file DEM per gunung (nama pendek tanpa awalan "Gunung").
DEM_FILENAMES = {
    "ibu": (
        "DEM_Gunung_Ibu_FINAL_REAL_10km.tif",
        "Gunung_Ibu_FINAL_8km.tif",
    ),
    "lewotolok": (
        "Gunung_Lewotolok_FINAL_SESUAI_PEMBIMBING.tif",
        "DEM_Gunung_Lewotolok_FINAL.tif",
    ),
}


class DemError(Exception):
    """Kesalahan yang bisa ditampilkan dengan aman ke pengguna."""


def _normalize_name(name):
    cleaned = str(name or "").strip().lower()
    for prefix in ("gunung ", "gn. ", "gn "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned.replace("_", " ").replace("-", " ").strip()


def _candidate_directories():
    backend_dir = Path(__file__).resolve().parent
    directories = []
    env_dir = os.getenv("DEM_DIR")
    if env_dir:
        directories.append(Path(env_dir))
    directories.extend(
        [
            backend_dir / "data" / "dem",
            backend_dir.parent / "data" / "dem",
            backend_dir.parent,
        ]
    )
    return directories


def find_dem_path(volcano_name):
    """Cari file DEM untuk gunung tertentu di seluruh direktori kandidat."""
    normalized = _normalize_name(volcano_name)
    preferred = DEM_FILENAMES.get(normalized, ())
    for directory in _candidate_directories():
        if not directory.is_dir():
            continue
        for filename in preferred:
            candidate = directory / filename
            if candidate.is_file():
                return candidate

    # Fallback: cocokkan nama file yang mengandung seluruh token nama gunung.
    tokens = [token for token in normalized.split() if token]
    if tokens:
        for directory in _candidate_directories():
            if not directory.is_dir():
                continue
            for candidate in sorted(directory.glob("*.tif")):
                if all(token in _normalize_name(candidate.stem) for token in tokens):
                    return candidate
    return None


def available_dem_files():
    """Daftar file .tif yang terlihat di direktori kandidat (untuk pesan error)."""
    seen = set()
    files = []
    for directory in _candidate_directories():
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.glob("*.tif")):
            if candidate.name not in seen:
                seen.add(candidate.name)
                files.append(candidate.name)
    return files


def warm_cache():
    """Pra-baca DEM yang tersedia agar request pertama tidak lambat.

    Dipanggil dari thread latar saat backend mulai. Aman jika beberapa proses
    memanggil bersamaan karena hasilnya di-cache dengan ``lru_cache``.
    """
    loaded = 0
    for directory in _candidate_directories():
        if not directory.is_dir():
            continue
        found = False
        for candidate in sorted(directory.glob("*.tif")):
            try:
                load_dem_grid(str(candidate))
                loaded += 1
                found = True
            except Exception:  # noqa: BLE001 - warm-up tidak boleh menjatuhkan app
                continue
        if found:
            break
    return loaded


@lru_cache(maxsize=8)
def load_dem_grid(dem_path_str, max_dimension=MAX_GRID_DIMENSION):
    """Baca DEM, downsample, dan siapkan grid lon/lat/elevasi untuk Plotly.

    Hasil di-cache memakai ``lru_cache`` sehingga file tidak dibaca ulang setiap
    kali filter dashboard berubah.
    """
    try:
        import numpy as np
        import rasterio
        from affine import Affine
        from rasterio.enums import Resampling
        from rasterio.warp import transform as warp_transform
    except ImportError as exc:  # pragma: no cover - tergantung environment
        raise DemError("rasterio belum terpasang di backend") from exc

    path = Path(dem_path_str)
    if not path.is_file():
        raise DemError(f"File DEM tidak ditemukan: {path.name}")

    with rasterio.open(path) as source:
        if source.crs is None:
            raise DemError(f"DEM {path.name} tidak memiliki informasi CRS")
        if source.count < 1:
            raise DemError(f"DEM {path.name} tidak memiliki band elevasi")

        width, height = source.width, source.height
        source_crs = source.crs.to_string()
        nodata = source.nodata
        # Yakin bahwa raster berorientasi north-up agar grid rapi.
        transform = source.transform
        scale = min(1.0, float(max_dimension) / max(width, height))
        out_width = max(2, int(round(width * scale)))
        out_height = max(2, int(round(height * scale)))

        data = source.read(
            1,
            out_shape=(out_height, out_width),
            resampling=Resampling.bilinear,
            masked=True,
        )
        data = np.ma.filled(data.astype("float64"), np.nan)

        down_transform = transform * Affine.scale(width / out_width, height / out_height)
        cols = np.arange(out_width)
        rows = np.arange(out_height)
        x_native = down_transform.c + (cols + 0.5) * down_transform.a
        y_native = down_transform.f + (rows + 0.5) * down_transform.e
        xx, yy = np.meshgrid(x_native, y_native)

        if source_crs.upper() != "EPSG:4326":
            xs, ys = warp_transform(
                source_crs, "EPSG:4326", xx.ravel().tolist(), yy.ravel().tolist()
            )
            xx = np.asarray(xs, dtype="float64").reshape(out_height, out_width)
            yy = np.asarray(ys, dtype="float64").reshape(out_height, out_width)
            lon = [[round(float(value), 8) for value in row] for row in xx]
            lat = [[round(float(value), 8) for value in row] for row in yy]
        else:
            lon = [round(float(value), 8) for value in x_native]
            lat = [round(float(value), 8) for value in y_native]

        finite = np.isfinite(data)
        if finite.any():
            zmin = float(data[finite].min())
            zmax = float(data[finite].max())
        else:
            zmin = zmax = 0.0

        elevation = [
            [None if not finite[row, col] else round(float(data[row, col]), 2) for col in range(out_width)]
            for row in range(out_height)
        ]

        bounds = {
            "min_lon": float(np.min(xx)),
            "max_lon": float(np.max(xx)),
            "min_lat": float(np.min(yy)),
            "max_lat": float(np.max(yy)),
        }

        return {
            "filename": path.name,
            "crs": source_crs,
            "bounds": bounds,
            "shape": [out_height, out_width],
            "source_shape": [height, width],
            "downsampled": bool(scale < 1.0),
            "nodata": nodata,
            "lon": lon,
            "lat": lat,
            "elevation": elevation,
            "zmin": zmin,
            "zmax": zmax,
            "offset": max(5.0, (zmax - zmin) * 0.015),
        }


def sample_elevations(dem_path_str, points):
    """Ambil elevasi DEM untuk titik (longitude, latitude) EPSG:4326.

    Titik di luar extent DEM atau bertemu nilai nodata menghasilkan ``None``.
    """
    try:
        import rasterio
        from rasterio.warp import transform as warp_transform
    except ImportError as exc:  # pragma: no cover - tergantung environment
        raise DemError("rasterio belum terpasang di backend") from exc

    path = Path(dem_path_str)
    if not path.is_file():
        raise DemError(f"File DEM tidak ditemukan: {path.name}")

    longitudes = [float(point["longitude"]) for point in points]
    latitudes = [float(point["latitude"]) for point in points]

    elevations = []
    with rasterio.open(path) as source:
        if source.crs is None:
            raise DemError(f"DEM {path.name} tidak memiliki informasi CRS")
        native_crs = source.crs.to_string()
        if native_crs.upper() != "EPSG:4326":
            xs, ys = warp_transform("EPSG:4326", native_crs, longitudes, latitudes)
        else:
            xs, ys = longitudes, latitudes

        nodata = source.nodata
        for value in source.sample(list(zip(xs, ys))):
            sample = float(value[0]) if value is not None else float("nan")
            if not math.isfinite(sample):
                elevations.append(None)
            elif nodata is not None and math.isclose(sample, float(nodata), rel_tol=1e-9, abs_tol=1e-6):
                elevations.append(None)
            else:
                elevations.append(round(sample, 2))
    return elevations


def convex_hull(points):
    """Convex Hull (Andrew's monotone chain).

    ``points`` adalah iterable pasangan ``(x, y)``. Mengembalikan daftar titik
    hull berurutan berlawanan arah jarum jam tanpa pengulangan titik awal.
    """
    unique = sorted({(round(x, 8), round(y, 8)) for x, y in points})
    if len(unique) <= 2:
        return [list(point) for point in unique]

    def cross(origin, first, second):
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (
            first[1] - origin[1]
        ) * (second[0] - origin[0])

    lower = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return [list(point) for point in (lower[:-1] + upper[:-1])]
