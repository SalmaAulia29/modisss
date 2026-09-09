import { useCallback, useEffect, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const MODIS_COLUMNS = [
  ["ID", "id"], ["Gunung", "volcano_name"], ["UNIX Time", "UNIX_Time"],
  ["Satelit", "Sat"], ["Datetime", "datetime"], ["Longitude", "Longitude"],
  ["Latitude", "Latitude"], ["B21", "B21"], ["B22", "B22"], ["B6", "B6"],
  ["B31", "B31"], ["B32", "B32"], ["SatZen", "SatZen"], ["SatAzi", "SatAzi"],
  ["SunZen", "SunZen"], ["SunAzi", "SunAzi"], ["Line", "Line"], ["Samp", "Samp"],
  ["NTI", "Nti"], ["Glint", "Glint"], ["Excess", "Excess"], ["Temp", "Temp"],
  ["Err", "Err"], ["Disimpan", "created_at"],
];

const LAVA_COLUMNS = [
  ["Time", "observation_datetime"], ["sigmaB21", "sum_b21"], ["Ecold", "effusion_cold"],
  ["Ehot", "effusion_hot"], ["Qcold", "heat_flux_cold"], ["Qhot", "heat_flux_hot"],
  ["cumEcold [B1]", "cum_e_cold_block1"], ["cumEhot [B1]", "cum_e_hot_block1"],
  ["meanE [B1]", "mean_e_block1"], ["cumQcold [B1]", "cum_q_cold_block1"],
  ["cumQhot [B1]", "cum_q_hot_block1"], ["meanQ [B1]", "mean_q_block1"],
  ["second", "delta_seconds"], ["cumEcold [B3]", "cumulative_cold"],
  ["cumEhot [B3]", "cumulative_hot"], ["meanE [B3]", "mean_e_block3"],
  ["cumQcold [B3]", "cumulative_q_cold"], ["cumQhot [B3]", "cumulative_q_hot"],
  ["meanQ [B3]", "mean_q"],
];

const number = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });
const today = new Date().toISOString().slice(0, 10);

function downloadCsv(filename, columns, rows) {
  const escape = (value) => `"${String(value ?? "").replaceAll("\"", "\"\"")}"`;
  const content = [
    columns.map(([label]) => escape(label)).join(","),
    ...rows.map((row) => columns.map(([, key]) => escape(row[key])).join(",")),
  ].join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function formatValue(value, key) {
  if (value === null || value === undefined || value === "") return "—";
  if (["datetime", "created_at", "observation_datetime"].includes(key)) {
    return new Date(value).toLocaleString("id-ID", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }
  if (typeof value === "number" && Math.abs(value) >= 1e8 && key.includes("heat_flux")) {
    return value.toExponential(2);
  }
  if (typeof value === "number" && !Number.isInteger(value)) return number.format(value);
  return String(value);
}

function recalculateFilteredRows(rows) {
  const indexedRows = rows.map((row, index) => ({ row, index }));
  const groupedRows = new Map();
  indexedRows.forEach((item) => {
    const group = groupedRows.get(item.row.volcano_id) || [];
    group.push(item);
    groupedRows.set(item.row.volcano_id, group);
  });

  const calculatedRows = new Map();
  groupedRows.forEach((group) => {
    group.sort((left, right) => new Date(left.row.observation_datetime) - new Date(right.row.observation_datetime));
    let cumulativeCold = 0;
    let cumulativeHot = 0;
    let cumulativeQCold = 0;
    let cumulativeQHot = 0;
    let block1Cold = 0;
    let block1Hot = 0;
    let block1QCold = 0;
    let block1QHot = 0;
    group.forEach((item, position) => {
      const previous = group[position - 1];
      const seconds = previous
        ? Math.max(0, Math.floor((new Date(item.row.observation_datetime) - new Date(previous.row.observation_datetime)) / 1000))
        : 0;
      const row = item.row;
      block1Cold += Number(row.effusion_cold || 0);
      block1Hot += Number(row.effusion_hot || 0);
      block1QCold += Number(row.heat_flux_cold || 0);
      block1QHot += Number(row.heat_flux_hot || 0);
      if (previous) {
        cumulativeCold += Number(previous.row.effusion_cold || 0) * seconds;
        cumulativeHot += Number(previous.row.effusion_hot || 0) * seconds;
        cumulativeQCold += Number(previous.row.heat_flux_cold || 0) * seconds;
        cumulativeQHot += Number(previous.row.heat_flux_hot || 0) * seconds;
      } else {
        cumulativeCold = block1Cold;
        cumulativeHot = block1Hot;
        cumulativeQCold = block1QCold;
        cumulativeQHot = block1QHot;
      }
      calculatedRows.set(item.index, {
        ...row,
        delta_seconds: seconds,
        cum_e_cold_block1: block1Cold,
        cum_e_hot_block1: block1Hot,
        mean_e_block1: (block1Cold + block1Hot) / 2,
        cum_q_cold_block1: block1QCold,
        cum_q_hot_block1: block1QHot,
        mean_q_block1: (block1QCold + block1QHot) / 2,
        cumulative_cold: cumulativeCold,
        cumulative_hot: cumulativeHot,
        mean_e_block3: (cumulativeCold + cumulativeHot) / 2,
        mean_e: (cumulativeCold + cumulativeHot) / 2,
        cumulative_q_cold: cumulativeQCold,
        cumulative_q_hot: cumulativeQHot,
        mean_q: (cumulativeQCold + cumulativeQHot) / 2,
        envelope: [Math.min(cumulativeCold, cumulativeHot), Math.max(cumulativeCold, cumulativeHot)],
      });
    });
  });

  return rows.map((row, index) => calculatedRows.get(index) || { ...row, delta_seconds: 0 });
}

function statusStyle(status) {
  return {
    success: "border-emerald-500/25 bg-emerald-50 text-emerald-700",
    waiting: "border-cyan/25 bg-cyan/10 text-cyan",
    running: "border-amber/25 bg-amber/10 text-amber",
    failed: "border-danger/25 bg-danger/10 text-danger",
    error: "border-danger/25 bg-danger/10 text-danger",
    no_data: "border-slate-300 bg-slate-100 text-slate-600",
  }[status] || "border-slate-300 bg-slate-100 text-slate-600";
}

function Icon({ name, className = "h-5 w-5" }) {
  const paths = {
    activity: <><path d="M3 12h4l2.5-7 5 14 2.5-7h4" /></>,
    database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></>,
    chart: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2" /></>,
    refresh: <><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    mountain: <><path d="m3 19 6-11 3 5 2-3 7 9H3Z" /><path d="m7.8 10.2 1.2 1.3 1.3-1.1" /></>,
    check: <><path d="m5 12 4 4L19 6" /></>,
    alert: <><path d="M12 9v4M12 17h.01" /><path d="M10.3 3.7 2.6 17a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.7a2 2 0 0 0-3.4 0Z" /></>,
    arrow: <><path d="M5 12h14M14 7l5 5-5 5" /></>,
    download: <><path d="M12 3v12M7 10l5 5 5-5M5 21h14" /></>,
    menu: <><path d="M4 6h16M4 12h16M4 18h16" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  };
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name] || paths.activity}
    </svg>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${statusStyle(status)}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {(status || "belum berjalan").replace("_", " ")}
    </span>
  );
}

function AppShell({ page, children, systemOnline = true }) {
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="min-h-screen">
      {menuOpen && <button type="button" aria-label="Tutup menu" onClick={closeMenu} className="fixed inset-0 z-40 cursor-default bg-slate-950/25 backdrop-blur-[1px]" />}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r border-line bg-white px-5 py-7 shadow-2xl transition-transform duration-200 ${menuOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-center justify-between">
        <a href="/" className="flex items-center gap-3 px-2 text-slate-950">
          <span className="grid h-10 w-10 place-items-center rounded-xl border border-cyan/30 bg-cyan/10 text-cyan"><Icon name="mountain" /></span>
          <span><strong className="block text-sm tracking-wide">MODIS</strong><small className="text-[10px] uppercase tracking-[0.18em] text-muted">Volcano Monitor</small></span>
        </a>
          <button type="button" aria-label="Tutup menu" onClick={closeMenu} className="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-card hover:text-slate-950"><Icon name="close" className="h-5 w-5" /></button>
        </div>
        <nav className="mt-10 space-y-1 text-sm">
          <SideLink active={page === "dashboard"} href="/" icon="activity" onClick={closeMenu}>Dashboard</SideLink>
          <SideLink active={page === "monitoring"} href="/monitoring" icon="clock" onClick={closeMenu}>Monitoring</SideLink>
        </nav>
        <div className="mt-auto rounded-xl border border-line bg-panel p-4">
          <div className="flex items-center gap-2 text-xs text-slate-700"><span className={`h-2 w-2 rounded-full ${systemOnline ? "bg-emerald-500" : "bg-danger"}`} />{systemOnline ? "Sistem terhubung" : "Sistem terganggu"}</div>
          <p className="mt-2 text-[10px] leading-4 text-muted">Collector berjalan terpisah dan tetap aktif saat browser ditutup.</p>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-line bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-9">
          <div className="flex items-center gap-3"><button type="button" aria-label="Buka menu" onClick={() => setMenuOpen(true)} className="grid h-10 w-10 place-items-center rounded-xl border border-line bg-panel text-slate-700 transition-colors hover:border-cyan/40 hover:text-cyan"><Icon name="menu" /></button><a href="/" className="flex items-center gap-2 font-semibold text-slate-950"><span className="text-cyan"><Icon name="mountain" /></span><span className="hidden sm:inline">MODIS Monitor</span><span className="sm:hidden">MODIS</span></a></div>
          <div className="hidden items-center gap-3 text-xs sm:flex"><span className="text-muted">{page === "dashboard" ? "Dashboard" : page === "monitoring" ? "Monitoring" : "Perhitungan Effusion Rate Lava"}</span><span className={`h-2 w-2 rounded-full ${systemOnline ? "bg-emerald-500" : "bg-danger"}`} /></div>
        </header>
        <main className="mx-auto max-w-[1540px] px-4 py-7 sm:px-6 lg:px-9 lg:py-9">
          {children}
          <footer className="mt-12 flex flex-col gap-2 border-t border-line pt-5 text-[10px] uppercase tracking-[0.12em] text-slate-500 sm:flex-row sm:justify-between"><span>MODIS Volcano Monitor</span><span>Data otomatis · Asia/Jakarta</span></footer>
        </main>
      </div>
    </div>
  );
}

function SideLink({ active, href, icon, children, onClick }) {
  return <a href={href} onClick={onClick} className={`flex items-center gap-3 rounded-xl px-3 py-3 transition-colors ${active ? "border border-cyan/20 bg-cyan/10 text-cyan" : "border border-transparent text-muted hover:bg-card hover:text-slate-950"}`}><Icon name={icon} className="h-4 w-4" /><span>{children}</span></a>;
}

function PageHeading({ eyebrow, title, description, generatedAt, refreshing, onRefresh }) {
  return (
    <header className="mb-7 flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-cyan">{eyebrow}</p>
        <h1 className="text-3xl font-semibold tracking-[-0.035em] text-slate-950 md:text-4xl">{title}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p>
      </div>
      <div className="flex items-center gap-3">
        {generatedAt && <span className="hidden text-right text-[10px] uppercase leading-4 tracking-wider text-slate-500 sm:block">Terakhir diperbarui<br /><strong className="font-medium text-slate-700">{formatValue(generatedAt, "datetime")}</strong></span>}
        {onRefresh && <button type="button" onClick={onRefresh} disabled={refreshing} className="inline-flex h-10 items-center gap-2 rounded-xl border border-line bg-panel px-4 text-xs font-semibold text-slate-800 transition-colors hover:border-slate-400 hover:bg-card disabled:opacity-50"><Icon name="refresh" className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />Perbarui</button>}
      </div>
    </header>
  );
}

function Loading() {
  return <div className="surface flex min-h-64 items-center justify-center text-sm text-muted"><span className="mr-3 h-4 w-4 animate-spin rounded-full border-2 border-cyan border-t-transparent" />Menghubungkan ke backend…</div>;
}

function ErrorPanel({ message, retry }) {
  return <div className="rounded-2xl border border-danger/30 bg-danger/10 p-6 text-danger"><div className="flex items-center gap-2 font-semibold"><Icon name="alert" />Data monitoring tidak dapat dimuat</div><p className="mt-2 text-sm opacity-80">{message}</p><button className="mt-4 rounded-lg border border-danger/30 px-4 py-2 text-sm hover:bg-danger/10" onClick={retry}>Coba lagi</button></div>;
}

function useApi(url, initialRefresh = 30) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshSeconds, setRefreshSeconds] = useState(initialRefresh);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const response = await fetch(url, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Backend merespons HTTP ${response.status}`);
      const payload = await response.json();
      setData(payload);
      setRefreshSeconds(payload.settings?.refresh_seconds || initialRefresh);
      setError("");
    } catch (requestError) {
      setError(requestError.message || "Kesalahan jaringan");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [url, initialRefresh]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(load, refreshSeconds * 1000);
    return () => window.clearInterval(timer);
  }, [load, refreshSeconds]);
  return { data, error, loading, refreshing, load };
}

function Countdown({ worker }) {
  const [remaining, setRemaining] = useState(Number(worker?.seconds_remaining || 0));
  useEffect(() => setRemaining(Number(worker?.seconds_remaining || 0)), [worker?.seconds_remaining, worker?.updated_at]);
  useEffect(() => {
    const timer = window.setInterval(() => setRemaining((current) => Math.max(0, current - 1)), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const countdown = worker?.status === "running" ? "berjalan" : remaining <= 0 ? "segera" : [Math.floor(remaining / 3600), Math.floor((remaining % 3600) / 60), remaining % 60].map((item) => String(item).padStart(2, "0")).join(":");
  const healthy = !["error", "failed"].includes(worker?.status);

  return (
    <section className="surface mb-4 overflow-hidden">
      <div className={`h-1 ${healthy ? "bg-cyan" : "bg-danger"}`} />
      <div className="grid md:grid-cols-[1.25fr_1fr_1fr]">
        <div className="flex items-center gap-4 border-b border-line p-5 md:border-b-0 md:border-r">
          <span className={`grid h-11 w-11 place-items-center rounded-xl border ${healthy ? "border-cyan/20 bg-cyan/10 text-cyan" : "border-danger/20 bg-danger/10 text-danger"}`}><Icon name="activity" /></span>
          <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted">Collector service</p><div className="mt-1 flex items-center gap-2"><strong className="text-base text-slate-950">Worker aktif</strong><StatusBadge status={worker?.status} /></div></div>
        </div>
        <div className="border-b border-line p-5 md:border-b-0 md:border-r"><p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-muted"><Icon name="clock" className="h-3.5 w-3.5" />Pengambilan berikutnya</p><strong className="mt-2 block font-mono text-2xl tracking-tight text-slate-950">{countdown}</strong></div>
        <div className="p-5"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted">Siklus terakhir selesai</p><strong className="mt-2 block text-sm font-medium text-slate-800">{formatValue(worker?.last_completed_at, "datetime")}</strong><span className="mt-1 block text-[11px] text-muted">Interval {worker?.interval_minutes || "—"} menit</span></div>
      </div>
    </section>
  );
}

function SectionTitle({ index, title, subtitle, action }) {
  return <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"><div className="flex items-start gap-3">{index && <span className="mt-0.5 font-mono text-[10px] text-cyan">{index}</span>}<div><h2 className="text-base font-semibold text-slate-950">{title}</h2>{subtitle && <p className="mt-1 text-xs text-muted">{subtitle}</p>}</div></div>{action}</div>;
}

function MetricCard({ icon, label, value, tone = "text-slate-950", featured = false }) {
  return <article className={`surface relative overflow-hidden p-5 ${featured ? "sm:col-span-2 lg:col-span-1 lg:row-span-2" : ""}`}><div className="flex items-start justify-between"><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted">{label}</p><span className="text-slate-500"><Icon name={icon} className="h-4 w-4" /></span></div><strong className={`mt-5 block font-mono tracking-tight ${featured ? "text-5xl" : "text-3xl"} ${tone}`}>{number.format(value || 0)}</strong>{featured && <p className="mt-3 max-w-[14rem] text-xs leading-5 text-muted">Total baris observasi yang berhasil tersimpan di database.</p>}</article>;
}

function VolcanoStatus({ volcano }) {
  const inserted = Number(volcano.last_rows_inserted || 0);
  const received = Number(volcano.last_rows_received || 0);
  const hasNewData = inserted > 0;
  return (
    <article className="surface overflow-hidden">
      <div className="flex items-start justify-between border-b border-line p-5"><div className="flex gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-card text-cyan"><Icon name="mountain" /></span><div><h3 className="font-semibold text-slate-950">{volcano.name}</h3><p className="mt-1 text-[11px] text-muted">{number.format(volcano.total_data)} total deteksi</p></div></div><StatusBadge status={volcano.last_status} /></div>
      <div className="grid grid-cols-2 divide-x divide-line border-b border-line"><div className="p-4"><p className="text-[10px] uppercase tracking-wider text-muted">Diterima</p><strong className="mt-1 block font-mono text-xl text-slate-950">{received}</strong></div><div className="p-4"><p className="text-[10px] uppercase tracking-wider text-muted">Baris baru</p><strong className={`mt-1 block font-mono text-xl ${hasNewData ? "text-emerald-700" : "text-slate-700"}`}>{inserted}</strong></div></div>
      <div className="space-y-3 p-5 text-xs"><div className="flex justify-between gap-3"><span className="text-muted">Data terakhir</span><span className="text-right text-slate-700">{formatValue(volcano.last_data, "datetime")}</span></div><div className="flex justify-between gap-3"><span className="text-muted">Terakhir diperiksa</span><span className="text-right text-slate-700">{formatValue(volcano.last_check, "datetime")}</span></div></div>
      <div className={`flex items-center gap-2 border-t px-5 py-3 text-[11px] ${hasNewData ? "border-emerald-300 bg-emerald-50 text-emerald-700" : "border-line bg-slate-50 text-muted"}`}><Icon name={hasNewData ? "check" : "database"} className="h-3.5 w-3.5" />{hasNewData ? `${inserted} data baru masuk pada pengecekan terakhir` : "Belum ada baris baru pada pengecekan terakhir"}</div>
    </article>
  );
}

function DataTable({ columns, rows, empty = "Belum ada data." }) {
  return <div className="surface max-h-[35rem] overflow-auto"><table className="data-table"><thead><tr>{columns.map(([label]) => <th key={label}>{label}</th>)}</tr></thead><tbody>{rows.length ? rows.map((row, rowIndex) => <tr key={row.id ?? rowIndex}>{columns.map(([label, key]) => <td key={`${row.id}-${label}`}>{formatValue(row[key], key)}</td>)}</tr>) : <tr><td className="!py-14 text-center !text-muted" colSpan={columns.length}>{empty}</td></tr>}</tbody></table></div>;
}

function RunsTable({ rows }) {
  return <div className="surface max-h-[31rem] overflow-auto"><table className="data-table"><thead><tr>{["Mulai", "Gunung", "Tanggal Target", "Status", "Diterima", "Baru", "HTTP", "Pesan"].map((heading) => <th key={heading}>{heading}</th>)}</tr></thead><tbody>{rows.map((run) => <tr key={run.id}><td>{formatValue(run.started_at, "datetime")}</td><td className="!font-medium !text-slate-950">{run.volcano_name}</td><td>{run.target_date}</td><td><StatusBadge status={run.status} /></td><td>{run.rows_received}</td><td className={run.rows_inserted > 0 ? "!font-semibold !text-emerald-700" : ""}>{run.rows_inserted}</td><td>{run.http_status || "—"}</td><td className="max-w-xs truncate" title={run.message}>{run.message || "—"}</td></tr>)}</tbody></table></div>;
}

const chartTheme = {
  grid: "#dce4ed",
  text: "#64748b",
  cold: "#087f8c",
  hot: "#a96710",
  mean: "#172033",
  envelope: "#94a3b8",
  tooltip: { backgroundColor: "#ffffff", border: "1px solid #d9e2ec", borderRadius: "10px", color: "#172033", fontSize: "11px", boxShadow: "0 8px 24px rgba(15, 23, 42, 0.1)" },
};

function shortDate(value) {
  if (!value) return "—";
  const normalized = String(value).includes("T") ? value : `${value}T00:00:00`;
  return new Date(normalized).toLocaleDateString("id-ID", { day: "2-digit", month: "short" });
}

function compactNumber(value) {
  return new Intl.NumberFormat("id-ID", { notation: "compact", maximumFractionDigits: 1 }).format(value || 0);
}

function addMeanBestFit(rows) {
  const points = rows.map((row, index) => ({
    x: new Date(row.observation_datetime).getTime(),
    y: Number(row.mean_e),
    index,
  })).filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));
  if (points.length < 2) return rows.map((row) => ({ ...row, mean_e_smooth: null }));

  points.sort((left, right) => left.x - right.x);
  const origin = points[0].x;
  const normalized = points.map((point) => ({ ...point, x: (point.x - origin) / 86400000 }));
  const fitSegment = (segment) => {
    const meanX = segment.reduce((sum, point) => sum + point.x, 0) / segment.length;
    const meanY = segment.reduce((sum, point) => sum + point.y, 0) / segment.length;
    const denominator = segment.reduce((sum, point) => sum + (point.x - meanX) ** 2, 0);
    const slope = denominator
      ? segment.reduce((sum, point) => sum + (point.x - meanX) * (point.y - meanY), 0) / denominator
      : 0;
    const intercept = meanY - slope * meanX;
    return {
      values: segment.map((point) => ({ index: point.index, value: intercept + slope * point.x })),
      error: segment.reduce((sum, point) => sum + (point.y - (intercept + slope * point.x)) ** 2, 0),
    };
  };
  const minimumPhasePoints = Math.max(4, Math.floor(normalized.length / 8));
  let bestFit = null;
  for (let firstBreak = minimumPhasePoints; firstBreak <= normalized.length - minimumPhasePoints * 2; firstBreak += 1) {
    for (let secondBreak = firstBreak + minimumPhasePoints; secondBreak <= normalized.length - minimumPhasePoints; secondBreak += 1) {
      const phases = [normalized.slice(0, firstBreak), normalized.slice(firstBreak, secondBreak), normalized.slice(secondBreak)].map(fitSegment);
      const error = phases.reduce((sum, phase) => sum + phase.error, 0);
      if (!bestFit || error < bestFit.error) bestFit = { error, phases };
    }
  }
  const phaseMaps = (bestFit?.phases || [fitSegment(normalized)]).map((phase) => new Map(phase.values.map((point) => [point.index, point.value])));
  return rows.map((row, index) => ({
    ...row,
    mean_e_smooth: phaseMaps.flatMap((values) => values.has(index) ? [values.get(index)] : []).at(0) ?? null,
    mean_e_phase1: phaseMaps[0]?.get(index) ?? null,
    mean_e_phase2: phaseMaps[1]?.get(index) ?? null,
    mean_e_phase3: phaseMaps[2]?.get(index) ?? null,
  }));
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const validDate = label && !Number.isNaN(new Date(label).getTime());
  const visibleItems = payload.filter((item) => ["envelope", "cumulative_cold", "cumulative_hot", "mean_e", "mean_e_phase1", "mean_e_phase2", "mean_e_phase3"].includes(item.dataKey));
  return (
    <div className="rounded-xl border border-line bg-white p-3 text-xs shadow-lg">
      <p className="mb-2 font-medium text-slate-700">{validDate ? new Date(label).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "Waktu tidak tersedia"}</p>
      {visibleItems.map((item) => {
        const values = (Array.isArray(item.value) ? item.value : [item.value]).map(Number).filter(Number.isFinite);
        if (!values.length || values.some((value) => !Number.isFinite(value))) return null;
        const value = values.length === 2 ? `${number.format(values[0])} - ${number.format(values[1])}` : number.format(values[0]);
        return <p key={item.dataKey} style={{ color: item.color }}>{item.name}: {value}</p>;
      })}
    </div>
  );
}

function ChartPanel({ volcano, rows }) {
  const data = addMeanBestFit((rows || []).filter((row) => Number.isFinite(Number(row.cumulative_cold)) && Number.isFinite(Number(row.cumulative_hot))));
  const downloadUrl = `/charts/energy/${volcano.id}.png?download=1`;

  return (
    <article className="surface overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <div className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-cyan" /><h3 className="text-sm font-semibold text-slate-950">Grafik Estimasi Effusion Rate Lava</h3></div>
          <p className="mt-1 pl-3.5 text-[10px] uppercase tracking-[0.12em] text-muted">{volcano.name} · {data.length} titik data</p>
        </div>
        <a href={downloadUrl} download className="inline-flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-700 transition-colors hover:border-cyan/40 hover:text-cyan" title="Unduh grafik hasil Matplotlib dan Scikit-learn"><Icon name="download" className="h-3.5 w-3.5" />Unduh PNG</a>
      </div>
      <div className="h-[330px] bg-slate-50 px-2 pb-2 pt-5 sm:px-4">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 12, left: 34, bottom: 4 }}>
              <CartesianGrid stroke={chartTheme.grid} strokeDasharray="2 5" vertical={false} />
              <XAxis dataKey="observation_datetime" tickFormatter={shortDate} stroke={chartTheme.grid} tick={{ fill: chartTheme.text, fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={30} label={{ value: "Tanggal pengamatan", position: "insideBottom", offset: -2, fill: chartTheme.text, fontSize: 10 }} />
              <YAxis tickFormatter={compactNumber} stroke={chartTheme.grid} tick={{ fill: chartTheme.text, fontSize: 10 }} tickLine={false} axisLine={false} width={65} label={{ value: "Nilai E kumulatif (m³)", angle: -90, position: "insideLeft", offset: 8, fill: chartTheme.text, fontSize: 10 }} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#94a3b8", strokeDasharray: "3 3" }} />
              <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: "10px", color: chartTheme.text, paddingTop: "12px" }} />
              <Area type="monotone" dataKey="envelope" name="Envelope estimasi E" stroke="none" fill={chartTheme.envelope} fillOpacity={0.22} activeDot={false} />
              <Line type="monotone" dataKey="cumulative_cold" name="Ecold" stroke={chartTheme.cold} strokeWidth={1.6} dot={false} activeDot={{ r: 3 }} />
              <Line type="monotone" dataKey="cumulative_hot" name="Ehot" stroke={chartTheme.hot} strokeWidth={1.6} dot={false} activeDot={{ r: 3 }} />
              <Scatter dataKey="mean_e" name="MeanE" fill={chartTheme.mean} line={false} shape="circle" />
              <Line type="linear" dataKey="mean_e_phase1" name="Regresi Fase 1" stroke={chartTheme.mean} strokeWidth={2.4} dot={false} activeDot={false} connectNulls={false} />
              <Line type="linear" dataKey="mean_e_phase2" name="Regresi Fase 2" stroke="#496a8a" strokeWidth={2.4} dot={false} activeDot={false} connectNulls={false} />
              <Line type="linear" dataKey="mean_e_phase3" name="Regresi Fase 3" stroke="#7c5f37" strokeWidth={2.4} dot={false} activeDot={false} connectNulls={false} />
            </ComposedChart>
          </ResponsiveContainer>
        ) : <div className="grid h-full place-items-center text-xs text-muted">Belum ada data grafik.</div>}
      </div>
    </article>
  );
}

function AnalysisFilters({ volcanoes, values, onChange }) {
  return (
    <section className="surface mb-6 grid gap-4 p-5 md:grid-cols-[1.2fr_1fr_1fr] md:items-end">
      <label className="text-xs font-semibold text-slate-700">
        Pilih gunung
        <select value={values.volcano} onChange={(event) => onChange("volcano", event.target.value)} className="mt-2 h-10 w-full rounded-lg border border-line bg-white px-3 text-sm font-normal text-slate-800 outline-none focus:border-cyan">
          <option value="all">Semua gunung</option>
          {volcanoes.map((volcano) => <option value={String(volcano.id)} key={volcano.id}>{volcano.name}</option>)}
        </select>
      </label>
      <label className="text-xs font-semibold text-slate-700">
        Mulai tanggal
        <input type="date" min="2026-01-01" value={values.startDate} onChange={(event) => onChange("startDate", event.target.value)} className="mt-2 h-10 w-full rounded-lg border border-line bg-white px-3 text-sm font-normal text-slate-800 outline-none focus:border-cyan" />
      </label>
      <label className="text-xs font-semibold text-slate-700">
        Sampai tanggal
        <input type="date" min={values.startDate || "2026-01-01"} value={values.endDate} onChange={(event) => onChange("endDate", event.target.value)} className="mt-2 h-10 w-full rounded-lg border border-line bg-white px-3 text-sm font-normal text-slate-800 outline-none focus:border-cyan" />
      </label>
    </section>
  );
}

function Charts({ volcanoes, chartData, dashboard = false, filters }) {
  const activeFilters = filters || { volcano: "all", startDate: "", endDate: "" };
  const visibleVolcanoes = activeFilters.volcano === "all" ? volcanoes : volcanoes.filter((volcano) => String(volcano.id) === activeFilters.volcano);
  const isAfterStart = (row) => !activeFilters.startDate || String(row.observation_datetime).slice(0, 10) >= activeFilters.startDate;
  const isBeforeEnd = (row) => !activeFilters.endDate || String(row.observation_datetime).slice(0, 10) <= activeFilters.endDate;
  const filteredChartRows = (volcano) => {
    const rows = chartData?.[String(volcano.id)]?.energy?.filter((row) => isAfterStart(row) && isBeforeEnd(row)) || [];
    return recalculateFilteredRows(rows);
  };
  return (
    <section className="mt-10">
      <SectionTitle index={dashboard ? "04" : "02"} title="Grafik Estimasi Effusion Rate Lava" subtitle="Arahkan kursor ke grafik untuk melihat nilai tiap observasi" action={dashboard && <a href="/lava-volume" className="inline-flex items-center gap-2 text-xs font-semibold text-cyan hover:text-slate-950">Lihat perhitungan <Icon name="arrow" className="h-3.5 w-3.5" /></a>} />
      <div className="grid gap-4 xl:grid-cols-2">{visibleVolcanoes.map((volcano) => <ChartPanel volcano={volcano} type="energy" rows={filteredChartRows(volcano)} key={volcano.id} />)}</div>
    </section>
  );
}

function DashboardFilter({ volcanoes, values, onChange, onSubmit }) {
  return (
    <form onSubmit={onSubmit} className="relative z-10 -mt-8 mx-4 grid gap-4 rounded-2xl border border-white/70 bg-white p-4 shadow-[0_18px_45px_rgba(15,23,42,0.13)] sm:mx-8 sm:grid-cols-[1.2fr_1fr_1fr_auto] sm:items-end lg:mx-14 lg:p-5">
      <label className="text-xs font-semibold text-slate-700">
        Gunung
        <select value={values.volcano} onChange={(event) => onChange("volcano", event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-line bg-white px-3 text-sm font-normal text-slate-800 outline-none focus:border-cyan">
          <option value="all">Semua gunung</option>
          {volcanoes.map((volcano) => <option value={String(volcano.id)} key={volcano.id}>{volcano.name}</option>)}
        </select>
      </label>
      <label className="text-xs font-semibold text-slate-700">
        Mulai periode
        <input type="date" min="2026-01-01" max={today} value={values.startDate} onChange={(event) => onChange("startDate", event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-line bg-white px-3 text-sm font-normal text-slate-800 outline-none focus:border-cyan" />
      </label>
      <label className="text-xs font-semibold text-slate-700">
        Sampai
        <input type="date" min={values.startDate || "2026-01-01"} max={today} value={values.endDate} onChange={(event) => onChange("endDate", event.target.value)} className="mt-2 h-11 w-full rounded-xl border border-line bg-white px-3 text-sm font-normal text-slate-800 outline-none focus:border-cyan" />
      </label>
      <button type="submit" className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-cyan px-5 text-xs font-bold text-white transition-colors hover:bg-slate-950"><Icon name="arrow" className="h-4 w-4 rotate-90" />Tampilkan data</button>
    </form>
  );
}

function ActionCard({ icon, title, description, onClick, href, disabled = false }) {
  const content = <><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan/10 text-cyan"><Icon name={icon} className="h-5 w-5" /></span><span className="min-w-0"><strong className="block text-sm text-slate-950">{title}</strong><small className="mt-1 block leading-5 text-muted">{description}</small></span><Icon name="arrow" className="ml-auto h-4 w-4 shrink-0 text-slate-400" /></>;
  if (href) return <a href={href} className="flex items-start gap-3 rounded-xl border border-line bg-white p-4 text-left transition-colors hover:border-cyan/40 hover:bg-cyan/[0.03]">{content}</a>;
  return <button type="button" onClick={onClick} disabled={disabled} className="flex items-start gap-3 rounded-xl border border-line bg-white p-4 text-left transition-colors hover:border-cyan/40 hover:bg-cyan/[0.03] disabled:cursor-not-allowed disabled:opacity-50">{content}</button>;
}

function Dashboard() {
  const { data, error, loading, refreshing, load } = useApi("/api/dashboard");
  const [filters, setFilters] = useState({ volcano: "all", startDate: "2026-01-01", endDate: today });
  const [appliedFilters, setAppliedFilters] = useState(null);
  const [activePanel, setActivePanel] = useState("");
  if (loading && !data) return <AppShell page="dashboard"><Loading /></AppShell>;
  if (error && !data) return <AppShell page="dashboard" systemOnline={false}><ErrorPanel message={error} retry={load} /></AppShell>;
  const online = !["error", "failed"].includes(data.worker?.status);
  const selectedRows = appliedFilters ? data.modis_data.filter((row) => {
    const rowDate = String(row.datetime).slice(0, 10);
    return (appliedFilters.volcano === "all" || String(data.volcanoes.find((volcano) => volcano.name === row.volcano_name)?.id) === appliedFilters.volcano) && rowDate >= appliedFilters.startDate && rowDate <= appliedFilters.endDate;
  }) : [];
  const applyFilters = (event) => {
    event.preventDefault();
    setAppliedFilters(filters);
    setActivePanel("");
  };
  const saveModis = () => downloadCsv(`data-modis-${appliedFilters.startDate}-${appliedFilters.endDate}.csv`, MODIS_COLUMNS, selectedRows);
  const saveCalculations = async () => {
    const response = await fetch("/api/lava-volume");
    const payload = await response.json();
    const rows = (payload.calculations || []).filter((row) => {
      const rowDate = String(row.observation_datetime).slice(0, 10);
      return (appliedFilters.volcano === "all" || String(row.volcano_id) === appliedFilters.volcano) && rowDate >= appliedFilters.startDate && rowDate <= appliedFilters.endDate;
    });
    downloadCsv(`perhitungan-mean-e-${appliedFilters.startDate}-${appliedFilters.endDate}.csv`, LAVA_COLUMNS, recalculateFilteredRows(rows));
  };
  const calculationUrl = appliedFilters ? (() => {
    const params = new URLSearchParams({ start: appliedFilters.startDate, end: appliedFilters.endDate });
    if (appliedFilters.volcano !== "all") params.set("volcano", appliedFilters.volcano);
    return `/lava-volume?${params.toString()}#detail-perhitungan`;
  })() : "/lava-volume";
  return (
    <AppShell page="dashboard" systemOnline={online}>
      <section className="relative overflow-hidden rounded-[1.5rem] bg-[#102d35] px-6 py-10 text-white shadow-[0_20px_50px_rgba(16,45,53,0.2)] sm:px-10 lg:px-14 lg:py-14">
        <div className="relative z-10 max-w-2xl"><p className="mb-3 text-[10px] font-bold uppercase tracking-[0.24em] text-[#8dd6c8]">PVMBG · MODIS monitoring</p><h1 className="max-w-xl text-3xl font-semibold tracking-tight sm:text-5xl">Pantau aktivitas gunung dalam satu layar.</h1><p className="mt-4 max-w-lg text-sm leading-6 text-white/70">Pilih gunung dan periode pengamatan untuk melihat estimasi effusion rate lava dari data MODIS yang masuk.</p></div>
        <div className="pointer-events-none absolute -right-8 -bottom-12 text-[#1b525b]/80 sm:right-8"><Icon name="mountain" className="h-56 w-56 sm:h-72 sm:w-72" /></div>
        <div className="absolute -right-16 -top-20 h-56 w-56 rounded-full border border-white/10" />
      </section>
      <DashboardFilter volcanoes={data.volcanoes} values={filters} onChange={(key, value) => setFilters((current) => ({ ...current, [key]: value }))} onSubmit={applyFilters} />
      {appliedFilters && <>
        <section id="mean-e" className="mt-10 scroll-mt-6"><SectionTitle title="Hasil pengamatan" subtitle={`${appliedFilters.startDate} sampai ${appliedFilters.endDate} · tekan Enter atau Tampilkan data untuk memperbarui`} action={<span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">● Data terhubung</span>} /><Charts volcanoes={data.volcanoes} chartData={data.chart_data} filters={appliedFilters} /></section>
        <section className="mt-10"><SectionTitle title="Akses data" subtitle="Buka data pendukung sesuai kebutuhan analisis" /><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4"><ActionCard icon="database" title="Lihat data MODIS" description={`${selectedRows.length} baris pada periode terpilih`} onClick={() => setActivePanel(activePanel === "modis" ? "" : "modis")} /><ActionCard icon="download" title="Simpan data MODIS" description="Unduh data mentah sebagai CSV" onClick={saveModis} /><ActionCard icon="chart" title="Lihat perhitungan" description="Detail estimasi effusion rate lava" href={calculationUrl} /><ActionCard icon="download" title="Simpan perhitungan" description="Unduh hasil perhitungan sebagai CSV" onClick={saveCalculations} /></div></section>
        {activePanel === "modis" && <section id="data-modis" className="mt-6 scroll-mt-6"><SectionTitle title="Data mentah MODIS" subtitle={`${selectedRows.length} data sesuai filter`} /><DataTable columns={MODIS_COLUMNS} rows={selectedRows} empty="Belum ada data MODIS pada periode ini." /></section>}
      </>}
    </AppShell>
  );
}

function Monitoring() {
  const { data, error, loading, refreshing, load } = useApi("/api/dashboard");
  if (loading && !data) return <AppShell page="monitoring"><Loading /></AppShell>;
  if (error && !data) return <AppShell page="monitoring" systemOnline={false}><ErrorPanel message={error} retry={load} /></AppShell>;
  const online = !["error", "failed"].includes(data.worker?.status);
  return (
    <AppShell page="monitoring" systemOnline={online}>
      <PageHeading eyebrow="Operational monitoring" title="Monitoring data masuk" description="Pantau collector, status tiap gunung, dan riwayat pengambilan data MODIS." generatedAt={data.generated_at} refreshing={refreshing} onRefresh={load} />
      <Countdown worker={data.worker} />
      {data.worker?.last_error && <div className="mb-4 flex gap-3 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger"><Icon name="alert" className="h-5 w-5 shrink-0" /><div><strong>Kesalahan worker</strong><p className="mt-1 opacity-80">{data.worker.last_error}</p></div></div>}
      <section className="mt-8"><SectionTitle title="Ringkasan data masuk" subtitle="Proses pada siklus collector terakhir; Total data MODIS menunjukkan seluruh isi database" /><div className="grid grid-cols-2 gap-3 lg:grid-cols-5"><MetricCard featured icon="database" label="Total data MODIS" value={data.totals.total_data} tone="text-cyan" /><MetricCard icon="activity" label="Total pengambilan" value={data.totals.total_runs} /><MetricCard icon="check" label="Proses berhasil" value={data.totals.success_runs} tone="text-emerald-700" /><MetricCard icon="database" label="Data baru masuk" value={data.totals.inserted} /><MetricCard icon="alert" label="Proses gagal" value={data.totals.failed_runs} tone={data.totals.failed_runs ? "text-danger" : "text-slate-950"} /></div></section>
      <section className="mt-8"><SectionTitle title="Status per gunung" subtitle="Pengecekan terakhir dari collector" /><div className="grid gap-4 xl:grid-cols-2">{data.volcanoes.map((volcano) => <VolcanoStatus volcano={volcano} key={volcano.id} />)}</div></section>
      <section className="mt-10"><SectionTitle title="Riwayat collector" subtitle={`${data.runs.length} proses terbaru · kolom Baru menunjukkan data yang masuk`} /><RunsTable rows={data.runs} /></section>
    </AppShell>
  );
}

function LavaVolume() {
  const { data, error, loading, refreshing, load } = useApi("/api/lava-volume", 60);
  const query = new URLSearchParams(window.location.search);
  const [filters, setFilters] = useState({ volcano: query.get("volcano") || "all", startDate: query.get("start") || "2026-01-01", endDate: query.get("end") || "" });
  useEffect(() => {
    if (data && window.location.hash === "#detail-perhitungan") {
      document.getElementById("detail-perhitungan")?.scrollIntoView({ behavior: "smooth" });
    }
  }, [data]);
  if (loading && !data) return <AppShell page="lava"><Loading /></AppShell>;
  if (error && !data) return <AppShell page="lava" systemOnline={false}><ErrorPanel message={error} retry={load} /></AppShell>;
  const isInPeriod = (row) => {
    const rowDate = String(row.observation_datetime).slice(0, 10);
    return rowDate >= filters.startDate && (!filters.endDate || rowDate <= filters.endDate);
  };
  const filteredCalculations = recalculateFilteredRows(data.calculations.filter((row) => (filters.volcano === "all" || String(row.volcano_id) === filters.volcano) && isInPeriod(row)));
  return (
    <AppShell page="lava">
      <PageHeading eyebrow="Data calculation" title="Detail Perhitungan Effusion Rate Lava" description="Tabel hasil perhitungan estimasi effusion rate lava berdasarkan data MODIS." refreshing={refreshing} onRefresh={load} />
      <section id="detail-perhitungan" className="mt-10 scroll-mt-6"><SectionTitle index="03" title="Detail perhitungan" subtitle={`${filteredCalculations.length} baris sesuai gunung dan periode terpilih`} /><DataTable columns={LAVA_COLUMNS} rows={filteredCalculations} empty="Belum ada hasil perhitungan." /></section>
    </AppShell>
  );
}

export default function App() {
  if (window.location.pathname === "/monitoring") return <Monitoring />;
  if (window.location.pathname === "/lava-volume") return <LavaVolume />;
  return <Dashboard />;
}
