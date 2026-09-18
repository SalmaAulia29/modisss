import { useEffect, useMemo, useRef, useState } from "react";
import Plotly from "plotly.js-gl3d-dist-min";

const PLOT_CONFIG = {
  responsive: true,
  displaylogo: false,
  scrollZoom: true,
  modeBarButtonsToRemove: ["toImage", "sendDataToCloud"],
};

const PLOT_HEIGHT = 700;

const number = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });

const DEM_COLORSCALE = [
  [0.0, "#173a4b"],
  [0.2, "#2f6f6a"],
  [0.4, "#6aa84f"],
  [0.6, "#d9c27a"],
  [0.8, "#b06a3b"],
  [1.0, "#7a2e1d"],
];

function formatDateTime(value) {
  if (!value) return "—";
  const raw = String(value);
  const normalized = raw.includes("T") ? raw : raw.replace(" ", "T");
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
}

function formatNumber(value, digits = 2) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? number.format(numeric) : "—";
}

function computeDelaunayEdges(points) {
  const count = points.length;
  if (count < 2) return [];
  if (count === 2) return [[0, 1]];

  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  points.forEach((point) => {
    minX = Math.min(minX, point.x);
    maxX = Math.max(maxX, point.x);
    minY = Math.min(minY, point.y);
    maxY = Math.max(maxY, point.y);
  });
  const extent = Math.max(maxX - minX, maxY - minY) || 1;
  const midX = (minX + maxX) / 2 - minX;
  const midY = (minY + maxY) / 2 - minY;

  const vertices = [
    { x: midX - 20 * extent, y: midY - extent },
    { x: midX, y: midY + 20 * extent },
    { x: midX + 20 * extent, y: midY - extent },
  ];
  points.forEach((point) => vertices.push({ x: point.x - minX, y: point.y - minY }));

  const orientation = (a, b, c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);

  const inCircumcircle = (a, b, c, d) => {
    const adx = a.x - d.x;
    const ady = a.y - d.y;
    const bdx = b.x - d.x;
    const bdy = b.y - d.y;
    const cdx = c.x - d.x;
    const cdy = c.y - d.y;
    const ap = adx * adx + ady * ady;
    const bp = bdx * bdx + bdy * bdy;
    const cp = cdx * cdx + cdy * cdy;
    const determinant =
      adx * (bdy * cp - bp * cdy) - bdx * (ady * cp - ap * cdy) + cdx * (ady * bp - ap * bdy);
    const ccw = orientation(a, b, c);
    return ccw !== 0 && determinant * ccw > 0;
  };

  let triangles = [[0, 1, 2]];

  for (let vertexIndex = 3; vertexIndex < vertices.length; vertexIndex += 1) {
    const point = vertices[vertexIndex];
    const badTriangles = [];
    triangles.forEach((triangle, index) => {
      if (inCircumcircle(vertices[triangle[0]], vertices[triangle[1]], vertices[triangle[2]], point)) {
        badTriangles.push(index);
      }
    });

    const edgeCounts = new Map();
    badTriangles.forEach((index) => {
      const triangle = triangles[index];
      [[triangle[0], triangle[1]], [triangle[1], triangle[2]], [triangle[2], triangle[0]]].forEach(
        ([u, v]) => {
          const key = u < v ? `${u}|${v}` : `${v}|${u}`;
          edgeCounts.set(key, (edgeCounts.get(key) || 0) + 1);
        },
      );
    });

    const removed = new Set(badTriangles);
    triangles = triangles.filter((_, index) => !removed.has(index));

    edgeCounts.forEach((edgeCount, key) => {
      if (edgeCount !== 1) return;
      const [u, v] = key.split("|").map(Number);
      triangles.push([u, v, vertexIndex]);
    });
  }

  const edgeSet = new Set();
  triangles.forEach((triangle) => {
    if (triangle.some((vertex) => vertex < 3)) return;
    for (let edge = 0; edge < 3; edge += 1) {
      const u = triangle[edge] - 3;
      const v = triangle[(edge + 1) % 3] - 3;
      const key = u < v ? `${u}|${v}` : `${v}|${u}`;
      edgeSet.add(key);
    }
  });

  return [...edgeSet].map((key) => key.split("|").map(Number));
}

function buildFigure(payload) {
  const zmin = Number(payload.zmin) || 0;
  const zmax = Number(payload.zmax) || 0;
  const zRange = Math.max(1, zmax - zmin);
  const offset = Number(payload.offset) || Math.max(5, zRange * 0.015);
  const traces = [];

  traces.push({
    type: "surface",
    name: "Surface DEM",
    x: payload.lon,
    y: payload.lat,
    z: payload.elevation,
    cmin: zmin,
    cmax: zmax,
    colorscale: DEM_COLORSCALE,
    showscale: true,
    colorbar: {
      title: { text: "Elevasi (m)", side: "right" },
      thickness: 12,
      len: 0.5,
      x: 0.99,
      tickfont: { size: 9 },
    },
    hovertemplate:
      "Longitude: %{x:.5f}<br>Latitude: %{y:.5f}<br>Elevasi: %{z:.0f} m<extra>DEM</extra>",
    showlegend: false,
    lighting: { ambient: 0.65, diffuse: 0.85, specular: 0.05, roughness: 0.9 },
    lightposition: { x: 1000, y: 1000, z: 2000 },
  });

  if (payload.bounds) {
    const baseZ = zmin - zRange * 0.08;
    const bounds = payload.bounds;
    traces.push({
      type: "scatter3d",
      mode: "lines",
      name: "Batas extent DEM",
      x: [bounds.min_lon, bounds.max_lon, bounds.max_lon, bounds.min_lon, bounds.min_lon],
      y: [bounds.min_lat, bounds.min_lat, bounds.max_lat, bounds.max_lat, bounds.min_lat],
      z: [baseZ, baseZ, baseZ, baseZ, baseZ],
      line: { color: "#64748b", width: 4, dash: "dot" },
      hoverinfo: "skip",
    });
  }

  const hotspots = payload.hotspots || [];
  const inside = hotspots.filter(
    (hotspot) => hotspot.elevation !== null && hotspot.elevation !== undefined,
  );

  if (inside.length) {
    const temperatures = inside.map((hotspot) =>
      Number.isFinite(Number(hotspot.temp)) ? Number(hotspot.temp) : null,
    );
    const validTemperatures = temperatures.filter((value) => value !== null);
    const temperatureMin = validTemperatures.length ? Math.min(...validTemperatures) : 0;
    const temperatureMax = validTemperatures.length ? Math.max(...validTemperatures) : 1;

    traces.push({
      type: "scatter3d",
      mode: "markers",
      name: `Hotspot MODIS (${inside.length})`,
      x: inside.map((hotspot) => hotspot.longitude),
      y: inside.map((hotspot) => hotspot.latitude),
      z: inside.map((hotspot) => Number(hotspot.elevation) + offset),
      customdata: inside.map((hotspot) => [
        hotspot.volcano_name,
        formatDateTime(hotspot.datetime),
        Number(hotspot.elevation),
        Number.isFinite(Number(hotspot.temp)) ? formatNumber(hotspot.temp) : "—",
        Number.isFinite(Number(hotspot.nti)) ? formatNumber(hotspot.nti, 4) : "—",
      ]),
      marker: {
        size: 8,
        color: temperatures,
        cmin: temperatureMin,
        cmax: temperatureMax,
        colorscale: "Hot",
        opacity: 1.0,
        line: { color: "#ffffff", width: 1.5 },
        colorbar: {
          title: { text: "Temp (K)", side: "right" },
          thickness: 10,
          len: 0.38,
          x: 1.1,
          tickfont: { size: 9 },
        },
      },
      hovertemplate:
        "<b>Gunung: %{customdata[0]}</b>" +
        "<br>Waktu: %{customdata[1]}" +
        "<br>Longitude: %{x:.5f}" +
        "<br>Latitude: %{y:.5f}" +
        "<br>Elevasi: %{customdata[2]:.0f} m" +
        "<br>Temperature: %{customdata[3]} K" +
        "<br>NTI: %{customdata[4]}" +
        "<extra></extra>",
    });
  }

  const pointCoordinates = inside.map((hotspot) => ({
    x: Number(hotspot.longitude),
    y: Number(hotspot.latitude),
  }));
  const edges = computeDelaunayEdges(pointCoordinates);
  if (edges.length) {
    const networkX = [];
    const networkY = [];
    const networkZ = [];
    edges.forEach(([start, end]) => {
      networkX.push(inside[start].longitude, inside[end].longitude, null);
      networkY.push(inside[start].latitude, inside[end].latitude, null);
      networkZ.push(
        Number(inside[start].elevation) + offset,
        Number(inside[end].elevation) + offset,
        null,
      );
    });
    traces.push({
      type: "scatter3d",
      mode: "lines",
      name: "Jaringan triangulasi hotspot",
      x: networkX,
      y: networkY,
      z: networkZ,
      line: { color: "#ffffff", width: 1.3 },
      hoverinfo: "skip",
    });
  }

  const polygon = Array.isArray(payload.polygon) ? payload.polygon : [];
  if (polygon.length === 1) {
    const point = polygon[0];
    traces.push({
      type: "scatter3d",
      mode: "markers",
      name: "Titik hotspot",
      x: [point.longitude],
      y: [point.latitude],
      z: [Number(point.elevation) + offset],
      marker: { size: 7, color: "#d62828", opacity: 0.9 },
      hoverinfo: "skip",
    });
  } else if (polygon.length >= 2) {
    const polygonZ = polygon.map((point) => Number(point.elevation) + offset);
    const polygonX = polygon.map((point) => point.longitude);
    const polygonY = polygon.map((point) => point.latitude);
    const closed = polygon.length >= 3;
    traces.push({
      type: "scatter3d",
      mode: "lines",
      name: "Batas Convex Hull",
      x: closed ? [...polygonX, polygonX[0]] : polygonX,
      y: closed ? [...polygonY, polygonY[0]] : polygonY,
      z: closed ? [...polygonZ, polygonZ[0]] : polygonZ,
      line: { color: "#d62828", width: 2.5, dash: closed ? "dash" : "solid" },
      hoverinfo: "skip",
      showlegend: closed,
    });
  }

  const layout = {
    autosize: true,
    height: PLOT_HEIGHT,
    margin: { l: 0, r: 0, t: 8, b: 0 },
    paper_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, system-ui, sans-serif", size: 11, color: "#617287" },
    showlegend: true,
    legend: { orientation: "h", x: 0, y: 1.08, font: { size: 10 } },
    scene: {
      aspectmode: "manual",
      aspectratio: { x: 1.4, y: 1.4, z: 0.6 },
      xaxis: {
        title: { text: "Longitude" },
        backgroundcolor: "rgba(0,0,0,0)",
        gridcolor: "#e2e8f0",
        zerolinecolor: "#cbd5e1",
      },
      yaxis: {
        title: { text: "Latitude" },
        backgroundcolor: "rgba(0,0,0,0)",
        gridcolor: "#e2e8f0",
        zerolinecolor: "#cbd5e1",
      },
      zaxis: {
        title: { text: "Elevasi (m)" },
        backgroundcolor: "rgba(0,0,0,0)",
        gridcolor: "#e2e8f0",
        zerolinecolor: "#cbd5e1",
      },
      camera: { eye: { x: 1.5, y: -1.5, z: 1.25 } },
    },
  };

  return { data: traces, layout };
}

export default function DemHotspot3D({ volcano, filters }) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const containerRef = useRef(null);
  const figure = useMemo(() => (state.data ? buildFigure(state.data) : null), [state.data]);

  useEffect(() => {
    if (!volcano?.id) return undefined;
    const controller = new AbortController();
    const params = new URLSearchParams();
    if (filters?.startDate) params.set("start", filters.startDate);
    if (filters?.endDate) params.set("end", filters.endDate);

    setState({ data: null, error: "", loading: true });
    fetch(`/api/dem/${volcano.id}?${params.toString()}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    })
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || `Backend merespons HTTP ${response.status}`);
        return payload;
      })
      .then((payload) => setState({ data: payload, error: "", loading: false }))
      .catch((error) => {
        if (error.name === "AbortError") return;
        setState({ data: null, error: error.message || "Gagal memuat peta 3D", loading: false });
      });

    return () => controller.abort();
  }, [volcano?.id, filters?.startDate, filters?.endDate]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || !figure) return undefined;
    Plotly.react(node, figure.data, figure.layout, PLOT_CONFIG);
    return () => {
      try {
        Plotly.purge(node);
      } catch {
        /* plot sudah dibersihkan */
      }
    };
  }, [figure]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node || typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(() => {
      try {
        Plotly.Plots.resize(node);
      } catch {
        /* node belum siap */
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [figure]);

  const data = state.data;

  return (
    <section className="mt-10 scroll-mt-6">
      <div className="mb-3 flex items-start gap-3">
        <span className="mt-0.5 font-mono text-[10px] text-cyan">01</span>
        <div>
          <h2 className="text-base font-semibold text-slate-950">3D DEM &amp; Hotspot</h2>
          <p className="mt-1 text-xs text-muted">Visualisasi topografi 3D dan sebaran hotspot MODIS</p>
        </div>
      </div>

      {data && (
        <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
          <span
            className="inline-block h-2 w-2 rounded-full bg-emerald-600"
            aria-hidden="true"
          />
          {data.volcano}
        </p>
      )}

      <article className="surface overflow-hidden">
        {state.loading && (
          <div className="grid place-items-center text-sm text-muted" style={{ height: PLOT_HEIGHT }}>
            <span className="mr-3 h-4 w-4 animate-spin rounded-full border-2 border-cyan border-t-transparent" />
            Memuat peta 3D DEM &amp; hotspot…
          </div>
        )}

        {!state.loading && state.error && (
          <div className="grid h-[320px] place-items-center px-6 text-center">
            <div>
              <p className="text-sm font-semibold text-danger">Peta 3D tidak dapat dimuat</p>
              <p className="mt-2 text-xs text-muted">{state.error}</p>
              <p className="mt-3 text-[11px] text-muted">
                Dashboard dan grafik lain tetap dapat digunakan.
              </p>
            </div>
          </div>
        )}

        {!state.loading && !state.error && data && data.hotspot_inside_count === 0 && (
          <div className="border-b border-line bg-amber/5 px-5 py-3 text-[11px] text-amber">
            Tidak ada hotspot pada periode ini yang berada di dalam extent DEM. Surface DEM tetap ditampilkan.
          </div>
        )}

        {!state.loading && !state.error && figure && (
          <div ref={containerRef} className="w-full" style={{ height: PLOT_HEIGHT }} />
        )}
      </article>
    </section>
  );
}
