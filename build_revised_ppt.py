"""Revisi PPT hotspot_modis.pptx -> struktur 19 slide sesuai rekomendasi.

Alur: Identitas -> Latar -> Tujuan & Output -> Data -> Tools -> Arsitektur ->
Web Scraping -> Metode Harris -> Contoh Perhitungan -> Alur Sistem -> Database
-> Implementasi Dashboard -> Hasil Sistem -> Pengujian -> Kendala ->
Pengembangan Selanjutnya -> Kesimpulan -> Referensi -> Terima Kasih.
"""

from pathlib import Path
from copy import deepcopy
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

root = Path.cwd()
prs = Presentation(root / 'hotspot_modis.pptx')

NAVY = RGBColor(16, 45, 53)
TEAL = RGBColor(14, 142, 155)
INK = RGBColor(23, 32, 51)
MUTED = RGBColor(92, 107, 122)
PALE = RGBColor(242, 248, 249)
WHITE = RGBColor(255, 255, 255)
ORANGE = RGBColor(239, 125, 55)
RED = RGBColor(204, 60, 53)
BGRAY = RGBColor(224, 233, 236)

LOGO_DIR = root / 'ppt_assets' / 'logos'
LOGO_ASPECT = {'python': 3.54, 'docker': 1.39, 'react': 1.0, 'mysql': 1.0, 'flask': 1.0}

def I(x):
    return Inches(x)

def box(s, x, y, w, h, c, round=False):
    q = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if round else MSO_SHAPE.RECTANGLE,
                           I(x), I(y), I(w), I(h))
    q.fill.solid(); q.fill.fore_color.rgb = c; q.line.fill.background()
    q.shadow.inherit = False
    return q

def txt(s, t, x, y, w, h, z=16, c=INK, b=False, a=PP_ALIGN.LEFT):
    q = s.shapes.add_textbox(I(x), I(y), I(w), I(h))
    f = q.text_frame; f.clear(); f.word_wrap = True
    f.margin_left = f.margin_right = f.margin_top = f.margin_bottom = Pt(0)
    p = f.paragraphs[0]; p.alignment = a
    r = p.add_run(); r.text = t
    r.font.name = 'Aptos'; r.font.size = Pt(z); r.font.bold = b; r.font.color.rgb = c
    return q

def bullets(s, x, y, w, h, lines, z=11, c=INK, gap=6):
    b = s.shapes.add_textbox(I(x), I(y), I(w), I(h))
    f = b.text_frame; f.clear(); f.word_wrap = True
    f.margin_left = f.margin_right = f.margin_top = f.margin_bottom = Pt(0)
    for i, line in enumerate(lines):
        p = f.paragraphs[0] if i == 0 else f.add_paragraph()
        p.space_after = Pt(gap)
        r = p.add_run(); r.text = '• ' + line
        r.font.name = 'Aptos'; r.font.size = Pt(z); r.font.color.rgb = c
    return b

def card(s, x, y, w, h, tag, title, body, color=TEAL):
    box(s, x, y, w, h, PALE, True)
    box(s, x, y, .07, h, color, True)
    txt(s, tag, x + .22, y + .16, w - .35, .2, 9, color, True)
    txt(s, title, x + .22, y + .48, w - .35, .38, 13.5, INK, True)
    txt(s, body, x + .22, y + .95, w - .35, h - 1.1, 10, MUTED)

def arrow(s, x, y):
    q = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, I(x), I(y), I(.32), I(.25))
    q.fill.solid(); q.fill.fore_color.rgb = TEAL; q.line.fill.background(); q.shadow.inherit = False

def varrow(s, x, y):
    q = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, I(x), I(y), I(.24), I(.22))
    q.fill.solid(); q.fill.fore_color.rgb = TEAL; q.line.fill.background(); q.shadow.inherit = False

def logo(s, name, cx, cy, tile=.62):
    aspect = LOGO_ASPECT[name]
    if aspect >= 1:
        w = tile * .86; h = w / aspect
    else:
        h = tile * .86; w = h * aspect
    x = cx + (tile - w) / 2
    y = cy + (tile - h) / 2
    s.shapes.add_picture(str(LOGO_DIR / (name + '.png')), I(x), I(y), width=I(w))

# ----------------------------------------------------------------------------
# Helpers header/template
# ----------------------------------------------------------------------------
def set_el_text(el, text):
    body = el.find(qn('p:txBody'))
    if body is None:
        return
    for p in body.findall(qn('a:p'))[1:]:
        body.remove(p)
    p0 = body.findall(qn('a:p'))[0]
    for r in p0.findall(qn('a:r'))[1:]:
        p0.remove(r)
    t = p0.find('.//' + qn('a:t'))
    if t is not None:
        t.text = text

def keep_el(slide, sh):
    w = sh.width / 914400; h = sh.height / 914400; y = sh.top / 914400
    if sh.has_text_frame and sh.text_frame.text.strip():
        return y < 2.15 or y > 6.8
    if sh.shape_type == 13 and w > 10:
        return True
    if sh.shape_type == 1 and h < 0.5 and w > 10:
        return True
    return False

def clear_content(slide):
    for sh in list(slide.shapes):
        if not keep_el(slide, sh):
            slide.shapes._spTree.remove(sh._element)

def grab_header(slide):
    els = {}
    for sh in slide.shapes:
        w = sh.width / 914400; h = sh.height / 914400; y = sh.top / 914400
        t = sh.text_frame.text.strip() if sh.has_text_frame else ''
        if sh.shape_type == 13 and w > 10 and sh.height / 914400 >= 5:
            els['bg'] = sh._element
        elif sh.shape_type == 1 and h < 0.5 and w > 10:
            els['band'] = sh._element
        elif sh.has_text_frame:
            if t == 'MODIS VOLCANO MONITOR':
                els['foot'] = sh._element
            elif t.isdigit() and y > 6.5:
                els['num'] = sh._element
            elif y < 0.8:
                els['label'] = sh._element
            elif 0.8 <= y < 1.6:
                els['title'] = sh._element
            elif 1.6 <= y < 2.15:
                els['sub'] = sh._element
    return {k: deepcopy(v) for k, v in els.items()}

def clone_header(donor, slide, label, title, sub, num):
    order = ['bg', 'band', 'foot', 'num', 'label', 'title', 'sub']
    for k in order:
        if k in donor:
            el = deepcopy(donor[k])
            if k == 'label':
                set_el_text(el, label)
            elif k == 'title':
                set_el_text(el, title)
            elif k == 'sub':
                set_el_text(el, sub)
            elif k == 'num' and num is not None:
                set_el_text(el, num)
            slide.shapes._spTree.append(el)

def set_header_text(slide, label, title, sub):
    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text.strip()
        y = sh.top / 914400
        if y < 0.8 and t[:2].isdigit() and len(t) > 2 and not t.isdigit():
            set_el_text(sh._element, label)
        elif 0.8 <= y < 1.6 and len(t) > 6 and not t[:2].isdigit():
            if title:
                set_el_text(sh._element, title)
        elif 1.6 <= y < 2.15 and sub:
            set_el_text(sh._element, sub)

def retag(slide, label):
    for sh in slide.shapes:
        if sh.has_text_frame:
            t = sh.text_frame.text.strip()
            y = sh.top / 914400
            if y < 0.8 and len(t) > 3 and t[:2].isdigit() and not t.isdigit():
                set_el_text(sh._element, label)
                return

def set_page_number(slide, num):
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip().isdigit() and sh.top / 914400 > 6.5:
            set_el_text(sh._element, num)
            return

# ----------------------------------------------------------------------------
# Ambil objek slide awal & donor header
# ----------------------------------------------------------------------------
slides = list(prs.slides)
S0, S1, S2, S3, S4, S5, S6, S7 = slides[0:8]
S8, S9, S10, S11, S12, S13, S14, S15, S16 = slides[8:17]
donor = grab_header(S3)          # S3 = slide 03 TOOLS (template header)
blank = prs.slide_layouts[6]

# ============================================================================
# 02  LATAR BELAKANG (S2) - tetap dari revisi sebelumnya
# ============================================================================
s = S2
clear_content(s)
set_header_text(s, '02  LATAR BELAKANG', 'Mengapa sistem ini dibuat?', None)
items = [
    ('01  FENOMENA', 'Erupsi efusif', 'Sebagian gunung api Indonesia (mis. Gunung Ibu dan Lewotolok) mengeluarkan lava secara terus-menerus.', ORANGE),
    ('02  TANTANGAN', 'Sulit diukur langsung', 'Lava tidak dapat diukur dengan cara sederhana; observasi lapangan berisiko dan sulit.', RED),
    ('03  KEBUTUHAN', 'Estimasi berkala', 'Dibutuhkan tools penginderaan jauh untuk mengestimasi volume dari waktu ke waktu.', TEAL),
    ('04  KONTRIBUSI', 'Kajian potensi bahaya', 'Perkembangan volume lava menjadi dasar mengestimasi potensi bahaya gunung api.', NAVY),
]
for i, it in enumerate(items):
    x = .72 + i * 3.03
    card(s, x, 2.35, 2.85, 2.25, *it)
    if i < 3:
        arrow(s, x + 2.85, 3.35)
bullets(s, .72, 4.95, 11.9, .9, [
    'Semakin besar dan semakin lama lava keluar, semakin tinggi potensi bahayanya.',
    'Pengukuran langsung tidak praktis, sehingga estimasi dilakukan dari data jarak jauh.',
    'Sistem ini mengestimasi volume lava pada gunung yang sedang mengeluarkan lava.',
], z=13, gap=4)
box(s, .72, 5.95, 11.89, .72, NAVY, True)
txt(s, 'Kontribusi: mengetahui perkembangan volume lava dari waktu ke waktu  →  dasar estimasi potensi bahaya gunung api.',
    1.05, 6.18, 11.3, .3, 14, WHITE, True, PP_ALIGN.CENTER)

# ============================================================================
# 05  TOOLS & TEKNOLOGI (S3) - logo + alasan (revisi sebelumnya)
# ============================================================================
s = S3
clear_content(s)
set_header_text(s, '05  TOOLS & TEKNOLOGI', 'Teknologi yang digunakan',
                'Setiap tools punya peran khusus; dipilih agar proses otomatis, dapat ditelusuri, dan mudah disajikan.')
tools = [
    ('python', 'Python', 'Collector & kalkulasi', 'Worker otomatis mengambil data MODIS dan menghitung indikator lava.',
     'otomatis dan kaya pustaka pemrosesan data.', TEAL),
    ('flask', 'Flask', 'API backend', 'Menyajikan data hasil olahan menjadi REST API untuk frontend.',
     'ringan dan cepat membuat API.', ORANGE),
    ('mysql', 'MySQL', 'Database', 'Menyimpan observasi, status worker, dan hasil perhitungan.',
     'riwayat data stabil dan mudah di-query.', NAVY),
    ('react', 'React + Vite', 'Dashboard', 'Menampilkan filter, tabel, grafik, dan ekspor CSV.',
     'UI interaktif untuk monitoring.', TEAL),
    ('docker', 'Docker', 'Deployment', 'Menjalankan backend, worker, dan frontend dalam wadah terpisah.',
     'lingkungan konsisten dan mudah dipindah.', ORANGE),
]
for i, (icon, name, role, desc, why, color) in enumerate(tools):
    x = .72 + i * 2.5; w = 2.28
    box(s, x, 2.2, w, 3.1, PALE, True)
    box(s, x, 2.2, w, .08, color, True)
    tile = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, I(x + .24), I(2.42), I(.62), I(.62))
    tile.fill.solid(); tile.fill.fore_color.rgb = WHITE; tile.line.color.rgb = BGRAY; tile.line.width = Pt(1)
    tile.shadow.inherit = False
    logo(s, icon, x + .24, 2.42)
    txt(s, name, x + .24, 3.18, w - .4, .3, 13, INK, True)
    txt(s, role, x + .24, 3.52, w - .4, .25, 9, color, True)
    txt(s, desc, x + .24, 3.85, w - .4, 1.0, 9.5, MUTED)
    txt(s, 'Dipilih: ' + why, x + .24, 4.98, w - .4, .6, 8.5, MUTED)
box(s, .72, 5.6, 11.89, .6, NAVY, True)
txt(s, 'MPODVolc  →  Python (web scraping)  →  MySQL  →  Flask API  →  React dashboard',
    1.0, 5.77, 11.3, .3, 15, WHITE, True, PP_ALIGN.CENTER)
txt(s, 'Alasan pemilihan: tiap tahap otomatis, tersimpan, dan dapat ditelusuri; Docker menjaga seluruh layanan tetap konsisten.',
    .72, 6.38, 11.89, .3, 10.5, MUTED)

# ============================================================================
# 04  DATA YANG DIGUNAKAN (S4) - hanya data, scraping dipindah ke slide tersendiri
# ============================================================================
s = S4
clear_content(s)
set_header_text(s, '04  DATA YANG DIGUNAKAN', 'MODIS & MPODVolc sebagai sumber data',
                'Data hotspot MODIS difilter per area gunung dan disimpan untuk pengolahan.')

box(s, .72, 2.25, 7.05, 3.9, PALE, True)
box(s, .72, 2.25, 7.05, .4, NAVY, True)
txt(s, 'modis.higp.hawaii.edu   |   MPODVolc — MODIS Volcano Monitoring', 1.0, 2.36, 6.5, .18, 10, WHITE, True)
txt(s, 'Sumber data: MPODVolc (University of Hawaii)', 1.0, 2.85, 6.4, .3, 14, INK, True)
txt(s, 'Data hotspot hasil observasi satelit MODIS (Terra/Aqua), tersedia publik dan dapat diminta berdasarkan area serta rentang tanggal.',
    1.0, 3.3, 6.5, .6, 10.5, MUTED)
txt(s, '26 kolom atribut: UNIX_Time & datetime, satelit, longitude/latitude, B21, B22, B6, B31/B32, geometri pengamatan (Sat/Sun Zen/Azi), NTI, glint, temperatur, dan indikator termal.',
    1.0, 4.05, 6.5, .7, 10, MUTED)
txt(s, 'Area pengamatan:', 1.0, 5.2, 4, .25, 10, INK, True)
for i, nm in enumerate(['Gunung Ibu', 'Gunung Lewotolok']):
    ch = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, I(1.0 + i * 2.8), I(5.55), I(2.35), I(.5))
    ch.fill.solid(); ch.fill.fore_color.rgb = WHITE; ch.line.color.rgb = TEAL; ch.line.width = Pt(1)
    ch.shadow.inherit = False
    tf = ch.text_frame; tf.clear(); tf.margin_left = tf.margin_top = tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = nm; r.font.name = 'Aptos'; r.font.size = Pt(11); r.font.bold = True; r.font.color.rgb = TEAL

box(s, 8.05, 2.25, 4.56, 3.9, PALE, True)
box(s, 8.05, 2.25, 4.56, .4, NAVY, True)
txt(s, 'KOLOM KUNCI UNTUK PERHITUNGAN', 8.3, 2.36, 4.1, .18, 9, WHITE, True)
bullets(s, 8.3, 2.9, 4.1, 2.6, [
    'B21 — radiance termal (input utama metode Harris)',
    'Waktu observasi (UNIX_Time / datetime)',
    'Koordinat untuk filter area gunung',
    'Satelit & geometri pengamatan',
    'NTI dan temperatur sebagai pendukung',
], z=10, gap=7)
txt(s, 'Metode Harris hanya membutuhkan Σ B21 dan selisih waktu antarobservasi.',
    8.3, 5.55, 4.1, .55, 9, MUTED)

box(s, .72, 6.35, 11.89, .6, NAVY, True)
txt(s, 'Data difilter menggunakan batas longitude dan latitude masing-masing area sebelum disimpan.',
    1.0, 6.52, 11.3, .3, 12, WHITE, True, PP_ALIGN.CENTER)

# ============================================================================
# 08  METODE ESTIMASI HARRIS (S6) - tetap dari revisi sebelumnya
# ============================================================================
s = S6
clear_content(s)
set_header_text(s, '08  METODE ESTIMASI', 'Metode Harris untuk estimasi volume lava',
                'Radiance termal MODIS dikonversi menjadi effusion rate, lalu diintegrasikan menjadi volume lava.')
box(s, .72, 2.2, 11.89, .6, NAVY, True)
txt(s, 'Radiance B21 (R)   →   Effusion rate (E)   →   Volume interval (V = E × Δt)   →   Volume kumulatif',
    1.0, 2.36, 11.3, .3, 14, WHITE, True, PP_ALIGN.CENTER)
cards_h = [
    ('INPUT', 'Hotspot MODIS', 'Radiance termal B21 (R = Σ B21) dan waktu observasi.', TEAL),
    ('PROSES', 'Kalibrasi Harris', 'Hubungan empiris radiance dan effusion rate pada kasus cold dan hot.', ORANGE),
    ('OUTPUT', 'Volume lava', 'Effusion rate dikalikan selang waktu (V = E × Δt) lalu dikumulatifkan.', RED),
]
for i, (tag, ttl, bd, c) in enumerate(cards_h):
    card(s, .72 + i * 4.19, 3.05, 3.52, 1.55, tag, ttl, bd, c)
formulas = [('Ecold = 0.450 × R − 0.127', TEAL), ('Ehot = 0.164 × R − 0.045', ORANGE), ('V = E × Δt', NAVY)]
for i, (f, c) in enumerate(formulas):
    q = box(s, .72 + i * 4.19, 4.95, 3.52, .62, BGRAY, True)
    q.line.color.rgb = c; q.line.width = Pt(1.2)
    txt(s, f, .72 + i * 4.19, 5.14, 3.52, .3, 14, INK, True, PP_ALIGN.CENTER)
box(s, .72, 5.7, 11.89, 1.28, PALE, True)
box(s, .72, 5.7, .07, 1.28, NAVY, True)
txt(s, 'Mengapa Band 21?', 1.0, 5.82, 6, .3, 13, NAVY, True)
bullets(s, 1.0, 6.12, 11.3, .72, [
    'Band inframerah-tengah (MIR ~3,96 µm) yang didesain khusus untuk deteksi titik panas.',
    'Tidak jenuh pada suhu sangat tinggi, sehingga tetap terbaca saat mengukur lava yang panas.',
    'Radiasi MIR sebanding dengan fluks panas → dasar hubungan empiris Harris menjadi effusion rate.',
], z=10, gap=3)
txt(s, 'Referensi: Harris, A. J. L. & Ripepe, M. (2007). Regional earthquakes as a trigger for enhanced volcanic activity: Evidence from MODIS thermal data.',
    1.0, 6.82, 11.3, .2, 8.5, MUTED)

# ============================================================================
# 10  ALUR SISTEM (S8) - tetap dari revisi sebelumnya
# ============================================================================
s = S8
clear_content(s)
set_header_text(s, '10  ALUR SISTEM', 'Dari data web menjadi informasi lava',
                'Setiap tahap dapat ditelusuri dari sumber hingga halaman web yang sudah jadi.')
flow = [
    ('01', 'MPODVolc', 'Sumber data hotspot MODIS'),
    ('02', 'Web scraping', 'Request otomatis per tanggal dan area'),
    ('03', 'Filter', 'Koordinat dalam batas area gunung'),
    ('04', 'MySQL', 'Penyimpanan data observasi'),
    ('05', 'Harris', 'Estimasi E, V, dan kumulatif'),
    ('06', 'Dashboard', 'Grafik, tabel, detail, ekspor CSV'),
]
for i, (n, ttl, bd) in enumerate(flow):
    y = 2.2 + i * .78
    box(s, .72, y, 5.7, .64, PALE, True)
    box(s, .72, y, .07, .64, NAVY if i % 2 else TEAL, True)
    txt(s, n, .92, y + .08, .5, .3, 13, TEAL if i % 2 == 0 else NAVY, True)
    txt(s, ttl, 1.45, y + .05, 1.9, .28, 11.5, INK, True)
    txt(s, bd, 3.35, y + .08, 3.0, .3, 9, MUTED)
    if i < 5:
        varrow(s, 1.12, y + .6)
box(s, 6.72, 2.2, 5.9, 4.45, PALE, True)
box(s, 6.72, 2.2, 5.9, .42, NAVY, True)
txt(s, 'VISUAL — HALAMAN WEB SUDAH JADI', 6.98, 2.3, 5.3, .2, 10, WHITE, True)
im = s.shapes.add_picture(str(root / 'dashboard-ppt.png'), I(7.62), I(2.75), width=I(4.1))
imh = im.height / 914400
txt(s, 'Halaman dashboard: pilih gunung & periode, lalu lihat hasil estimasi.', 6.98, 2.75 + imh + .12, 5.35, .25, 9.5, MUTED)

# ============================================================================
# 12  IMPLEMENTASI DASHBOARD (S13)
# ============================================================================
s = S13
clear_content(s)
set_header_text(s, '12  IMPLEMENTASI DASHBOARD', 'Dashboard pemantauan yang telah dibangun',
                'Pengguna memilih gunung dan periode pengamatan untuk melihat hasil estimasi dari data MODIS.')
bullets(s, .72, 2.35, 5.7, 3.2, [
    'Pemilihan gunung dan periode pengamatan',
    'Grafik estimasi effusion rate dan volume lava',
    'Tabel data MODIS dan detail perhitungan',
    'Unduh hasil dalam format CSV',
], z=12.5, gap=14)
txt(s, 'Status worker dan monitor collection juga tersedia pada halaman terpisah.', .72, 5.6, 5.7, .5, 10.5, MUTED)
im2 = s.shapes.add_picture(str(root / 'dashboard-ppt.png'), I(7.55), I(2.2), width=I(4.7))
imh2 = im2.height / 914400
txt(s, 'Tampilan aplikasi yang berjalan di browser.', 7.55, 2.2 + imh2 + .1, 4.7, .25, 9.5, MUTED)

# ============================================================================
# 13  HASIL SISTEM (S14)
# ============================================================================
s = S14
clear_content(s)
set_header_text(s, '13  HASIL SISTEM', 'Output sistem: tabel perhitungan dan grafik',
                'Hasil olahan dapat ditelusuri dari data mentah hingga estimasi volume lava.')
im3 = s.shapes.add_picture(str(root / 'perhitungan-ppt.png'), I(.72), I(2.2), width=I(5.3))
imh3 = im3.height / 914400
txt(s, 'Tabel detail perhitungan observasi.', .72, 2.2 + imh3 + .1, 5.3, .25, 9.5, MUTED)
im4 = s.shapes.add_picture(str(root / 'thermal-chart-ppt.png'), I(6.55), I(2.25), width=I(3.2))
imh4 = im4.height / 914400
txt(s, 'Grafik termal hasil olahan.', 6.55, 2.25 + imh4 + .1, 3.2, .25, 9.5, MUTED)
bullets(s, 10.15, 2.6, 2.55, 3.4, [
    'Detail: B21, effusion rate cold/hot, heat flux, Δt',
    'Volume kumulatif dan MeanE',
    'Grafik: Ecold, Ehot, MeanE',
    'Tren melalui linear fitting',
    'Unduh sebagai PNG / CSV',
], z=10.5, gap=10)

# ============================================================================
# 15  KENDALA (S11) - retag label
# ============================================================================
retag(S11, '15  KENDALA')

# ============================================================================
# 16  PENGEMBANGAN SELANJUTNYA (S12) - + mockup peta hotspot
# ============================================================================
s = S12
clear_content(s)
set_header_text(s, '16  PENGEMBANGAN SELANJUTNYA', 'Penyempurnaan yang akan dilakukan', None)
bullets(s, .72, 2.5, 7.0, 3.6, [
    'Integrasi peta persebaran hotspot dari koordinat MODIS ke website.',
    'Penanganan kendala koneksi ke server MODIS (retry / backfill data).',
    'Memperbaiki linear fitting pada grafik agar sesuai seluruh data.',
    'Pengujian dan penyempurnaan dashboard.',
], z=12.5, gap=18)
box(s, 8.1, 2.5, 4.5, 3.7, PALE, True)
box(s, 8.1, 2.5, 4.5, .42, NAVY, True)
txt(s, 'PETA HOTSPOT — RENCANA', 8.35, 2.6, 4.0, .2, 10, WHITE, True)
txt(s, 'PETA GUNUNG IBU', 8.4, 3.1, 3.9, .25, 11, INK, True, PP_ALIGN.CENTER)
for px, py in [(9.3, 3.7), (10.0, 3.55), (10.9, 3.8), (10.4, 4.2)]:
    d = s.shapes.add_shape(MSO_SHAPE.OVAL, I(px), I(py), I(.24), I(.24))
    d.fill.solid(); d.fill.fore_color.rgb = RED; d.line.fill.background(); d.shadow.inherit = False
txt(s, 'Persebaran hotspot berdasarkan koordinat MODIS (mockup) — akan ditambahkan sebagai peta interaktif.',
    8.35, 5.6, 4.0, .8, 9.5, MUTED)
txt(s, 'Selanjauh ini peta belum masuk output utama, dijadwalkan setelah dashboard stabil.',
    0.72, 6.35, 7.0, .4, 10, MUTED)

# ============================================================================
# 18  REFERENSI (S15) - retag label
# ============================================================================
retag(S15, '18  REFERENSI')

# ============================================================================
# SLIDE BARU yang ditambahkan
# ============================================================================
# 03  TUJUAN & OUTPUT
s = prs.slides.add_slide(blank)
clone_header(donor, s, '03  TUJUAN & OUTPUT', 'Tujuan dan output yang ingin dicapai',
             'Sistem mengubah data hotspot menjadi informasi estimasi lava yang mudah dipantau.', '03')
goals = [
    ('1', 'KUMPULKAN', 'Pengambilan data otomatis', 'Mengambil hotspot MODIS dari MPODVolc secara berkala tanpa akses ke lapangan.', TEAL),
    ('2', 'HITUNG', 'Estimasi indikator lava', 'Menghitung effusion rate, heat flux, dan volume lava kumulatif.', ORANGE),
    ('3', 'SAJIKAN', 'Visualisasi hasil', 'Dashboard interaktif: filter, grafik, tabel, dan ekspor CSV.', NAVY),
]
for i, (n, tag, ttl, bd, c) in enumerate(goals):
    y = 2.2 + i * 1.53
    box(s, .72, y, 6.05, 1.38, PALE, True)
    box(s, .72, y, .07, 1.38, c, True)
    txt(s, n, .95, y + .12, .5, .4, 20, c, True)
    txt(s, tag, 1.55, y + .1, 2.5, .22, 9, c, True)
    txt(s, ttl, 1.55, y + .36, 5.0, .32, 14, INK, True)
    txt(s, bd, 1.55, y + .78, 4.95, .5, 10, MUTED)
box(s, 7.05, 2.2, 5.56, 5.1, PALE, True)
box(s, 7.05, 2.2, 5.56, .42, NAVY, True)
txt(s, 'OUTPUT SISTEM', 7.3, 2.3, 4.0, .2, 10, WHITE, True)
bullets(s, 7.35, 2.9, 4.95, 3.5, [
    'Dashboard web pemantauan',
    'Grafik effusion rate & volume lava',
    'Tabel data MODIS & detail perhitungan',
    'Ekspor hasil CSV',
    'Peta hotspot (pengembangan)',
], z=12.5, gap=13)

# 06  ARSITEKTUR SISTEM
s = prs.slides.add_slide(blank)
clone_header(donor, s, '06  ARSITEKTUR SISTEM', 'Arsitektur sistem secara menyeluruh',
             'Alur dua arah: pengambilan data otomatis (worker) dan penyajian ke pengguna (dashboard).', None)
arch = [
    ('MPODVolc', 'sumber data hotspot MODIS', NAVY, 3.0),
    ('Python Collector', 'web scraping otomatis', TEAL, 3.0),
    ('MySQL', 'penyimpanan data & riwayat', NAVY, 3.0),
]
for i, (nm, dsc, c, w) in enumerate(arch):
    y = 2.0 + i * .9
    b = box(s, 5.17, y, w, .56, c, True)
    tf = b.text_frame; tf.clear(); tf.margin_left = tf.margin_top = tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = nm; r.font.name = 'Aptos'; r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = WHITE
    txt(s, dsc, 5.17, y + .58, w, .22, 8.5, MUTED, False, PP_ALIGN.CENTER)
    if i < 2:
        varrow(s, 6.23, y + .58)
# layer perhitungan & api
yb = 4.7
for j, (nm, dsc, c, x) in enumerate([('Perhitungan Harris', 'effusion rate & volume', TEAL, 1.0),
                                      ('Flask REST API', 'data untuk dashboard', ORANGE, 7.0)]):
    b = box(s, x, yb, 5.3, .56, c, True)
    tf = b.text_frame; tf.clear(); tf.margin_left = tf.margin_top = tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = nm; r.font.name = 'Aptos'; r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = WHITE
    txt(s, dsc, x, yb + .58, 5.3, .22, 8.5, MUTED, False, PP_ALIGN.CENTER)
varrow(s, 6.6, 4.12)
b = box(s, 5.17, 5.55, 3.0, .56, NAVY, True)
tf = b.text_frame; tf.clear(); tf.margin_left = tf.margin_top = tf.margin_bottom = Pt(0)
p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
r = p.add_run(); r.text = 'React Dashboard'; r.font.name = 'Aptos'; r.font.size = Pt(13); r.font.bold = True; r.font.color.rgb = WHITE
txt(s, 'filter, tabel, grafik, ekspor CSV', 5.17, 6.13, 3.0, .22, 8.5, MUTED, False, PP_ALIGN.CENTER)
varrow(s, 6.6, 5.26)
outs = [('Grafik', TEAL), ('Tabel', NAVY), ('Ekspor CSV', TEAL), ('Peta (pengembangan)', ORANGE)]
for i, (nm, c) in enumerate(outs):
    x = .72 + i * 3.03
    ch = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, I(x), I(6.5), I(2.65), I(.5))
    ch.fill.solid(); ch.fill.fore_color.rgb = c; ch.line.fill.background(); ch.shadow.inherit = False
    tf = ch.text_frame; tf.clear(); tf.margin_left = tf.margin_top = tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = nm; r.font.name = 'Aptos'; r.font.size = Pt(11); r.font.bold = True; r.font.color.rgb = WHITE

# 07  PROSES WEB SCRAPING
s = prs.slides.add_slide(blank)
clone_header(donor, s, '07  PROSES WEB SCRAPING', 'Mengambil data hotspot secara otomatis',
             'Worker Python menjadwalkan request, memvalidasi, dan menyimpan data tanpa akses manual ke lapangan.', None)
steps = [
    ('1', 'Jadwal & request', 'Worker membaca tanggal yang perlu diambil lalu meminta data ke MPODVolc tiap interval.', TEAL),
    ('2', 'Validasi format', 'Format respons dicek; data dengan gunung, waktu, satelit, koordinat yang sama tidak disimpan ulang.', ORANGE),
    ('3', 'Filter area', 'Hanya hotspot dalam batas koordinat Gunung Ibu dan Lewotolok yang diterima.', NAVY),
    ('4', 'Simpan & catat', 'Data masuk ke MySQL; collection_runs mencatat status success, no_data, atau failed.', RED),
]
for i, (n, ttl, bd, c) in enumerate(steps):
    x = .72 + i * 3.03
    box(s, x, 2.4, 2.85, 2.2, PALE, True)
    box(s, x, 2.4, 2.85, .1, c, True)
    txt(s, n, x + .22, 2.62, .5, .4, 22, c, True)
    txt(s, ttl, x + .65, 2.66, 2.0, .3, 13, INK, True)
    txt(s, bd, x + .22, 3.15, 2.4, 1.3, 9.5, MUTED)
    if i < 3:
        arrow(s, x + 2.85, 3.4)
box(s, .72, 5.35, 11.89, .66, NAVY, True)
txt(s, 'Browser tidak membaca MPODVolc secara langsung — pengambilan dilakukan worker, hasilnya tersimpan di database.',
    1.0, 5.53, 11.3, .3, 12.5, WHITE, True, PP_ALIGN.CENTER)
txt(s, 'Worker berjalan sebagai service terpisah, sehingga proses tetap berjalan walau dashboard ditutup.',
    .72, 6.2, 11.89, .3, 10.5, MUTED)

# 09  CONTOH PERHITUNGAN (data nyata Gunung Ibu 2026-02-13)
s = prs.slides.add_slide(blank)
clone_header(donor, s, '09  CONTOH PERHITUNGAN', 'Contoh perhitungan dengan data nyata',
             'Diambil dari database sistem: observasi Gunung Ibu 13 Februari 2026.', None)
box(s, .72, 2.3, 5.3, 3.6, PALE, True)
box(s, .72, 2.3, .07, 3.6, TEAL, True)
txt(s, 'INPUT — DATA MODIS', .95, 2.45, 4.8, .22, 10, TEAL, True)
bullets(s, .95, 2.85, 4.85, 2.9, [
    'Gunung Ibu, 13 Feb 2026 12:40 UTC',
    'Σ B21 (R) = 1,293 mW·m⁻²·sr⁻¹·μm⁻¹',
    'Δt = 3.024.000 s (± 35 hari)',
], z=11, gap=12)
txt(s, 'Sumber: tabel modis_data / lava_volume_calculations', .95, 5.35, 4.85, .3, 8.5, MUTED)
arrow(s, 6.15, 3.9)
box(s, 6.55, 2.3, 3.3, 3.6, PALE, True)
box(s, 6.55, 2.3, .07, 3.6, ORANGE, True)
txt(s, 'PROSES — KALIBRASI HARRIS', 6.8, 2.45, 2.9, .22, 10, ORANGE, True)
bullets(s, 6.8, 2.9, 2.95, 2.8, [
    'Ecold = 0,450 × 1,293 − 0,127',
    '             = 0,455 m³/s',
    'Ehot = 0,164 × 1,293 − 0,045',
    '            = 0,167 m³/s',
    'Vcold = 0,455 × 3.024.000 s',
    'Vhot = 0,167 × 3.024.000 s',
], z=10, gap=6, c=INK)
arrow(s, 9.98, 3.9)
box(s, 10.4, 2.3, 2.2, 3.6, PALE, True)
box(s, 10.4, 2.3, .07, 3.6, NAVY, True)
txt(s, 'HASIL', 10.65, 2.45, 1.8, .22, 10, NAVY, True)
bullets(s, 10.65, 2.9, 1.9, 2.8, [
    'Vcold ≈ 1,375 × 10⁶ m³',
    'Vhot ≈ 0,505 × 10⁶ m³',
    'Kumulatif cold 1.375.466 m³',
], z=10.5, gap=12, c=INK)
box(s, .72, 6.2, 11.89, .64, NAVY, True)
txt(s, 'Hasil ini sama dengan nilai pada tabel lava_volume_calculations (Gunung Ibu, 2026-02-13) di database.',
    1.0, 6.38, 11.3, .3, 12.5, WHITE, True, PP_ALIGN.CENTER)

# 11  DATABASE
s = prs.slides.add_slide(blank)
clone_header(donor, s, '11  DATABASE', 'Data yang disimpan di MySQL',
             'Dua tabel utama: data mentah hotspot dan hasil perhitungan lava.', None)
tables = [
    ('.72', 'modis_data — data mentah hotspot', NAVY, [
        'UNIX_Time & datetime (waktu observasi)',
        'Sat (Terra/Aqua), Longitude, Latitude',
        'B21 (radiance kunci), B22, B6',
        'B31/B32, geometri pengamatan',
        'NTI, glint, temperatur, metadata worker',
    ]),
    ('6.9', 'lava_volume_calculations — hasil perhitungan', TEAL, [
        'sum B21 & jumlah piksel (pixel count)',
        'Δt (delta detik antarobservasi)',
        'Effusion rate cold / hot',
        'Heat flux cold / hot',
        'Volume interval & volume kumulatif, MeanE/MeanQ',
    ]),
]
for hx, tt, c, rows in tables:
    x = float(hx)
    box(s, x, 2.25, 5.7, 3.4, PALE, True)
    box(s, x, 2.25, 5.7, .42, c, True)
    txt(s, tt, x + .22, 2.34, 5.3, .2, 11, WHITE, True)
    bullets(s, x + .3, 2.95, 5.1, 2.5, rows, z=10.5, gap=8)
box(s, .72, 6.05, 11.89, .6, NAVY, True)
txt(s, 'Tabel pendukung: volcanoes, collection_runs (status tiap pengambilan), dan worker_status.',
    1.0, 6.22, 11.3, .3, 12, WHITE, True, PP_ALIGN.CENTER)
txt(s, 'Skema tabel dibuat melalui init.sql / bootstrap_db.py; data awal disimpan via railway_seed.sql.',
    .72, 6.8, 11.89, .28, 9, MUTED)

# 14  PENGUJIAN
s = prs.slides.add_slide(blank)
clone_header(donor, s, '14  PENGUJIAN', 'Hasil pengujian sistem', None, None)
tests = [
    ('Collector web scraping MODIS', 'Berhasil', TEAL),
    ('Validasi & filter area gunung', 'Berhasil', TEAL),
    ('Simpan ke database (tanpa duplikasi)', 'Berhasil', TEAL),
    ('Perhitungan Harris (E, heat flux, volume)', 'Berhasil', TEAL),
    ('Dashboard & filter gunung/periode', 'Berhasil', TEAL),
    ('Grafik estimasi & tabel detail', 'Berhasil', TEAL),
    ('Ekspor data CSV', 'Berhasil', TEAL),
    ('Peta hotspot', 'Dalam pengembangan', ORANGE),
]
for i, (feat, status, c) in enumerate(tests):
    y = 2.3 + i * .56
    box(s, .72, y, 8.6, .46, PALE, True)
    box(s, .72, y, .06, .46, NAVY, True)
    txt(s, feat, .95, y + .1, 8.2, .28, 11.5, INK)
    ch = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, I(9.5), I(y + .03), I(3.1), I(.4))
    ch.fill.solid(); ch.fill.fore_color.rgb = c; ch.line.fill.background(); ch.shadow.inherit = False
    tf = ch.text_frame; tf.clear(); tf.margin_left = tf.margin_top = tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = status; r.font.name = 'Aptos'; r.font.size = Pt(10.5); r.font.bold = True; r.font.color.rgb = WHITE
txt(s, 'Pengujian dilakukan pada periode pengambilan data 26 Agustus – 2 September 2026 (lihat collection_runs).',
    .72, 6.9, 11.89, .28, 9.5, MUTED)

# 17  KESIMPULAN
s = prs.slides.add_slide(blank)
clone_header(donor, s, '17  KESIMPULAN', 'Kesimpulan', None, None)
concl = [
    ('1', 'Data mentah menjadi informasi', 'Sistem mengubah hotspot MODIS menjadi estimasi effusion rate dan volume lava yang dapat ditelusuri.'),
    ('2', 'Otomatis dan terintegrasi', 'Alur scraping MPODVolc → database → perhitungan Harris → API → dashboard berjalan otomatis.'),
    ('3', 'Memudahkan monitoring', 'Dashboard menampilkan filter, grafik, tabel detail, dan ekspor CSV.'),
    ('4', 'Arah pengembangan', 'Peta hotspot dan penyempurnaan linear fitting pada grafik.'),
]
for i, (n, ttl, bd) in enumerate(concl):
    y = 2.3 + i * 1.05
    box(s, .72, y, 11.89, .9, PALE, True)
    box(s, .72, y, .07, .9, TEAL if i % 2 == 0 else NAVY, True)
    txt(s, n, .95, y + .14, .55, .4, 22, TEAL if i % 2 == 0 else NAVY, True)
    txt(s, ttl, 1.6, y + .1, 4.2, .3, 13, INK, True)
    txt(s, bd, 5.9, y + .12, 6.5, .5, 10.5, MUTED)
box(s, .72, 6.55, 11.89, .5, NAVY, True)
txt(s, 'Sistem siap mendukung pemantauan volume lava pada gunung api yang sedang bererupsi efusif.',
    1.0, 6.68, 11.3, .28, 12, WHITE, True, PP_ALIGN.CENTER)

# ============================================================================
# Hapus slide lama yang tidak dipakai & susun ulang urutan akhir
# ============================================================================
xml = prs.slides._sldIdLst
ids = list(xml)                       # 24 slide setelah penambahan
for idx in (5, 7, 9, 10):             # Analisis, Rumus kumulatif, Timeline, Progress
    xml.remove(ids[idx])
ids = list(xml)                       # 20 slide tersisa
# urutan sisa: 0 C0,1 C1,2 C2,3 C3,4 C4,5 C6,6 C8,7 C11,8 C12,9 C13,10 C14,
#              11 C15,12 C16,13 N1,14 N2,15 N3,16 N4,17 N5,18 N6,19 N7
order = [0, 1, 2, 13, 4, 3, 14, 15, 5, 16, 6, 17, 9, 10, 18, 7, 8, 19, 11, 12]
desired = [ids[i] for i in order]
for el in list(xml):
    xml.remove(el)
for el in desired:
    xml.append(el)

# ----------------------------------------------------------------------------
# Nomor halaman diurutkan ulang
# ----------------------------------------------------------------------------
final = list(prs.slides)
for i in range(1, len(final)):
    try:
        set_page_number(final[i], f'{i:02d}')
    except Exception:
        pass

prs.save(root / 'hotspot_modis.pptx')
print('saved', len(prs.slides), 'slides')