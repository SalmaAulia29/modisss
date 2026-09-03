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
  ["ID", "id"], ["Gunung", "volcano_name"], ["Datetime", "observation_datetime"],
  ["Pixel", "pixel_count"], ["ΣB21", "sum_b21"], ["MAX B21", "max_b21"],
  ["Δt (detik)", "delta_seconds"], ["E cold (m³/s)", "effusion_cold"],
  ["E hot (m³/s)", "effusion_hot"], ["Heat cold (W)", "heat_flux_cold"],
  ["Heat hot (W)", "heat_flux_hot"], ["Volume cold (m³)", "volume_cold"],
  ["Volume hot (m³)", "volume_hot"], ["Kumulatif cold (m³)", "cumulative_cold"],
  ["Kumulatif hot (m³)", "cumulative_hot"],
];

const number = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });

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
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
      <aside className="hidden border-r border-line bg-white lg:flex lg:min-h-screen lg:flex-col lg:px-5 lg:py-7">
        <a href="/" className="flex items-center gap-3 px-2 text-slate-950">
          <span className="grid h-10 w-10 place-items-center rounded-xl border border-cyan/30 bg-cyan/10 text-cyan"><Icon name="mountain" /></span>
          <span><strong className="block text-sm tracking-wide">MODIS</strong><small className="text-[10px] uppercase tracking-[0.18em] text-muted">Volcano Monitor</small></span>
        </a>
        <nav className="mt-10 space-y-1 text-sm">
          <SideLink active={page === "dashboard"} href="/" icon="activity">Monitoring</SideLink>
          <SideLink active={page === "lava"} href="/lava-volume" icon="chart">Analisis Lava</SideLink>
        </nav>
        <div className="mt-8 border-t border-line pt-6">
          <p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">Akses cepat</p>
          <div className="mt-3 space-y-1 text-xs text-muted">
            <a className="block rounded-lg px-3 py-2 hover:bg-card hover:text-slate-950" href="/#volcanoes">Status gunung</a>
            <a className="block rounded-lg px-3 py-2 hover:bg-card hover:text-slate-950" href="/#data-modis">Data MODIS</a>
            <a className="block rounded-lg px-3 py-2 hover:bg-card hover:text-slate-950" href="/#history">Riwayat collector</a>
          </div>
        </div>
        <div className="mt-auto rounded-xl border border-line bg-panel p-4">
          <div className="flex items-center gap-2 text-xs text-slate-700"><span className={`h-2 w-2 rounded-full ${systemOnline ? "bg-emerald-500" : "bg-danger"}`} />{systemOnline ? "Sistem terhubung" : "Sistem terganggu"}</div>
          <p className="mt-2 text-[10px] leading-4 text-muted">Collector berjalan terpisah dan tetap aktif saat browser ditutup.</p>
        </div>
      </aside>

      <div className="min-w-0">
        <header className="flex h-16 items-center justify-between border-b border-line bg-white px-4 lg:hidden">
          <a href="/" className="flex items-center gap-2 font-semibold text-slate-950"><span className="text-cyan"><Icon name="mountain" /></span>MODIS Monitor</a>
          <div className="flex gap-1 rounded-lg border border-line bg-panel p-1 text-xs"><a className={`rounded-md px-3 py-1.5 ${page === "dashboard" ? "bg-card text-slate-950" : "text-muted"}`} href="/">Monitor</a><a className={`rounded-md px-3 py-1.5 ${page === "lava" ? "bg-card text-slate-950" : "text-muted"}`} href="/lava-volume">Lava</a></div>
        </header>
        <main className="mx-auto max-w-[1540px] px-4 py-7 sm:px-6 lg:px-9 lg:py-9">
          {children}
          <footer className="mt-12 flex flex-col gap-2 border-t border-line pt-5 text-[10px] uppercase tracking-[0.12em] text-slate-500 sm:flex-row sm:justify-between"><span>MODIS Volcano Monitor</span><span>Data otomatis · Asia/Jakarta</span></footer>
        </main>
      </div>
    </div>
  );
}

function SideLink({ active, href, icon, children }) {
  return <a href={href} className={`flex items-center gap-3 rounded-xl px-3 py-3 transition-colors ${active ? "border border-cyan/20 bg-cyan/10 text-cyan" : "border border-transparent text-muted hover:bg-card hover:text-slate-950"}`}><Icon name={icon} className="h-4 w-4" /><span>{children}</span></a>;
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

function ChartPanel({ volcano, type, rows }) {
  const isVolume = type === "daily";
  const data = rows || [];
  const downloadUrl = isVolume
    ? `/charts/daily-volume/${volcano.id}.png?download=1`
    : `/charts/energy/${volcano.id}.png?download=1`;

  return (
    <article className="surface overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <div className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-cyan" /><h3 className="text-sm font-semibold text-slate-950">{isVolume ? "Volume lava harian" : "Mean Energy"}</h3></div>
          <p className="mt-1 pl-3.5 text-[10px] uppercase tracking-[0.12em] text-muted">{volcano.name} · {data.length} titik data</p>
        </div>
        <a href={downloadUrl} download className="inline-flex items-center gap-2 rounded-lg border border-line bg-card px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-700 transition-colors hover:border-cyan/40 hover:text-cyan" title="Unduh grafik hasil Matplotlib dan Scikit-learn"><Icon name="download" className="h-3.5 w-3.5" />Unduh PNG</a>
      </div>
      <div className="h-[330px] bg-slate-50 px-2 pb-2 pt-5 sm:px-4">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 5, right: 12, left: 0, bottom: 4 }}>
              <CartesianGrid stroke={chartTheme.grid} strokeDasharray="2 5" vertical={false} />
              <XAxis dataKey={isVolume ? "observation_date" : "observation_datetime"} tickFormatter={shortDate} stroke={chartTheme.grid} tick={{ fill: chartTheme.text, fontSize: 10 }} tickLine={false} axisLine={false} minTickGap={30} />
              <YAxis tickFormatter={compactNumber} stroke={chartTheme.grid} tick={{ fill: chartTheme.text, fontSize: 10 }} tickLine={false} axisLine={false} width={48} />
              <Tooltip contentStyle={chartTheme.tooltip} cursor={{ stroke: "#94a3b8", strokeDasharray: "3 3" }} labelFormatter={(label) => new Date(label).toLocaleString("id-ID", isVolume ? { dateStyle: "long" } : { dateStyle: "medium", timeStyle: "short" })} formatter={(value, name) => [Array.isArray(value) ? `${number.format(value[0])} – ${number.format(value[1])}` : number.format(value), name]} />
              <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: "10px", color: chartTheme.text, paddingTop: "12px" }} />
              {isVolume ? (
                <>
                  <Area type="monotone" dataKey="volume_cold" name="Cold (m³)" stroke={chartTheme.cold} fill={chartTheme.cold} fillOpacity={0.08} strokeWidth={2} dot={false} activeDot={{ r: 4, fill: chartTheme.cold, stroke: "#ffffff", strokeWidth: 2 }} />
                  <Area type="monotone" dataKey="volume_hot" name="Hot (m³)" stroke={chartTheme.hot} fill={chartTheme.hot} fillOpacity={0.06} strokeWidth={2} dot={false} activeDot={{ r: 4, fill: chartTheme.hot, stroke: "#ffffff", strokeWidth: 2 }} />
                </>
              ) : (
                <>
                  <Area type="monotone" dataKey="envelope" name="Rentang E" stroke="none" fill={chartTheme.cold} fillOpacity={0.08} activeDot={false} />
                  <Line type="monotone" dataKey="effusion_cold" name="Ecold" stroke={chartTheme.cold} strokeWidth={1.6} dot={false} activeDot={{ r: 3 }} />
                  <Line type="monotone" dataKey="effusion_hot" name="Ehot" stroke={chartTheme.hot} strokeWidth={1.6} dot={false} activeDot={{ r: 3 }} />
                  <Scatter dataKey="mean_e" name="MeanE" fill={chartTheme.mean} line={false} shape="circle" />
                </>
              )}
            </ComposedChart>
          </ResponsiveContainer>
        ) : <div className="grid h-full place-items-center text-xs text-muted">Belum ada data grafik.</div>}
      </div>
    </article>
  );
}

function Charts({ volcanoes, chartData, dashboard = false }) {
  return (
    <section className="mt-10">
      <SectionTitle index={dashboard ? "04" : "02"} title="Analisis visual interaktif" subtitle="Arahkan kursor ke grafik untuk melihat nilai tiap observasi" action={dashboard && <a href="/lava-volume" className="inline-flex items-center gap-2 text-xs font-semibold text-cyan hover:text-slate-950">Lihat perhitungan lengkap <Icon name="arrow" className="h-3.5 w-3.5" /></a>} />
      <div className="grid gap-4 xl:grid-cols-2">{volcanoes.map((volcano) => <div className="grid gap-4" key={volcano.id}><ChartPanel volcano={volcano} type="daily" rows={chartData?.[String(volcano.id)]?.daily} /><ChartPanel volcano={volcano} type="energy" rows={chartData?.[String(volcano.id)]?.energy} /></div>)}</div>
    </section>
  );
}

function Dashboard() {
  const { data, error, loading, refreshing, load } = useApi("/api/dashboard");
  if (loading && !data) return <AppShell page="dashboard"><Loading /></AppShell>;
  if (error && !data) return <AppShell page="dashboard" systemOnline={false}><ErrorPanel message={error} retry={load} /></AppShell>;
  const online = !["error", "failed"].includes(data.worker?.status);
  return (
    <AppShell page="dashboard" systemOnline={online}>
      <PageHeading eyebrow="Operational dashboard" title="Monitoring pengambilan data" description="Pastikan collector terhubung, pengecekan berlangsung, dan observasi MODIS baru tersimpan ke database." generatedAt={data.generated_at} refreshing={refreshing} onRefresh={load} />
      <Countdown worker={data.worker} />
      {data.worker?.last_error && <div className="mb-4 flex gap-3 rounded-xl border border-danger/30 bg-danger/10 p-4 text-sm text-danger"><Icon name="alert" className="h-5 w-5 shrink-0" /><div><strong>Kesalahan worker</strong><p className="mt-1 opacity-80">{data.worker.last_error}</p></div></div>}

      <section className="mt-6">
        <SectionTitle index="01" title="Ringkasan database" subtitle="Angka langsung dari proses collector dan tabel MODIS" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5 lg:grid-rows-2"><MetricCard featured icon="database" label="Total data MODIS" value={data.totals.total_data} tone="text-cyan" /><MetricCard icon="activity" label="Total pengambilan" value={data.totals.total_runs} /><MetricCard icon="check" label="Proses berhasil" value={data.totals.success_runs} tone="text-emerald-700" /><MetricCard icon="database" label="Baris baru" value={data.totals.inserted} /><MetricCard icon="alert" label="Proses gagal" value={data.totals.failed_runs} tone={data.totals.failed_runs ? "text-danger" : "text-slate-950"} /></div>
      </section>

      <section id="volcanoes" className="mt-10 scroll-mt-6">
        <SectionTitle index="02" title="Status per gunung" subtitle="Hasil pengecekan terbaru dan jumlah data yang benar-benar masuk" />
        <div className="grid gap-4 xl:grid-cols-2">{data.volcanoes.map((volcano) => <VolcanoStatus volcano={volcano} key={volcano.id} />)}</div>
      </section>

      <section id="history" className="mt-10 scroll-mt-6">
        <SectionTitle index="03" title="Riwayat collector" subtitle={`${data.runs.length} proses terbaru · kolom Baru menunjukkan data yang masuk ke database`} />
        <RunsTable rows={data.runs} />
      </section>

      <Charts volcanoes={data.volcanoes} chartData={data.chart_data} dashboard />

      <section id="data-modis" className="mt-10 scroll-mt-6">
        <SectionTitle index="05" title="Data mentah MODIS" subtitle={`${data.modis_data.length} data terbaru · ID ditampilkan dari kecil ke besar`} />
        <DataTable columns={MODIS_COLUMNS} rows={data.modis_data} empty="Belum ada data MODIS tersimpan." />
      </section>
    </AppShell>
  );
}

function LavaVolume() {
  const { data, error, loading, refreshing, load } = useApi("/api/lava-volume", 60);
  if (loading && !data) return <AppShell page="lava"><Loading /></AppShell>;
  if (error && !data) return <AppShell page="lava" systemOnline={false}><ErrorPanel message={error} retry={load} /></AppShell>;
  return (
    <AppShell page="lava">
      <PageHeading eyebrow="Thermal analysis" title="Estimasi volume lava" description="Hasil integrasi laju volume berdasarkan radiansi termal MODIS Band 21." refreshing={refreshing} onRefresh={load} />
      <section>
        <SectionTitle index="01" title="Volume kumulatif" subtitle="Rentang estimasi cold dan hot untuk setiap gunung" />
        <div className="grid gap-4 md:grid-cols-2">{data.summary.map((item) => <article className="surface overflow-hidden" key={item.id}><div className="flex items-center justify-between border-b border-line p-5"><div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-lg bg-card text-cyan"><Icon name="mountain" className="h-4 w-4" /></span><div><h3 className="font-semibold text-slate-950">{item.name}</h3><p className="text-[11px] text-muted">{item.observations} observasi</p></div></div></div><div className="grid grid-cols-2 divide-x divide-line"><div className="p-5"><p className="text-[10px] uppercase tracking-wider text-muted">Cold</p><strong className="mt-2 block font-mono text-xl text-cyan">{number.format(item.cumulative_cold)}</strong><span className="text-[10px] text-muted">m³ kumulatif</span></div><div className="p-5"><p className="text-[10px] uppercase tracking-wider text-muted">Hot</p><strong className="mt-2 block font-mono text-xl text-amber">{number.format(item.cumulative_hot)}</strong><span className="text-[10px] text-muted">m³ kumulatif</span></div></div></article>)}</div>
      </section>
      <section className="surface mt-5 p-5 text-sm leading-7 text-slate-700"><div className="flex items-center gap-2 text-slate-950"><Icon name="chart" className="h-4 w-4 text-cyan" /><h2 className="font-semibold">Metode perhitungan</h2></div><p className="mt-3">ΣB21 dan MAX(B21) dihitung untuk setiap gunung pada waktu pengamatan yang sama.</p><div className="my-3 grid gap-2 font-mono text-xs text-cyan sm:grid-cols-2"><code className="rounded-lg border border-line bg-ink px-3 py-2">Ecold = max(0; 0,450 × ΣB21 − 0,127)</code><code className="rounded-lg border border-line bg-ink px-3 py-2">Ehot = max(0; 0,164 × ΣB21 − 0,045)</code></div><p>Heat flux = E × densitas panas · Volume interval = E × Δt · Volume kumulatif = Σ volume interval.</p><p className="mt-2 text-xs text-muted">Densitas cold {number.format(data.constants.cold_heat_density)} J/m³ · hot {number.format(data.constants.hot_heat_density)} J/m³. Observasi pertama memakai Δt = 0.</p></section>
      <Charts volcanoes={data.summary} chartData={data.chart_data} />
      <section className="mt-10"><SectionTitle index="03" title="Detail perhitungan" subtitle="Urutan observasi terbaru" /><DataTable columns={LAVA_COLUMNS} rows={data.calculations} empty="Belum ada hasil perhitungan." /></section>
    </AppShell>
  );
}

export default function App() {
  return window.location.pathname === "/lava-volume" ? <LavaVolume /> : <Dashboard />;
}
