$ErrorActionPreference='Stop'
$ppt=New-Object -ComObject PowerPoint.Application
$path=(Resolve-Path 'hotspot_modis.pptx').Path
$p=$ppt.Presentations.Open($path)
function Add-Text($slide,$text,[single]$left,[single]$top,[single]$width,[single]$height,[int]$size,[int]$rgb){
  $s=$slide.Shapes.AddTextbox(1,$left,$top,$width,$height)
  $s.TextFrame.TextRange.Text=$text
  $s.TextFrame.TextRange.Font.Name='Aptos'
  $s.TextFrame.TextRange.Font.Size=$size
  $s.TextFrame.TextRange.Font.Color.RGB=$rgb
  return $s
}
$navy=3484944; $teal=10194446; $ink=2826511; $muted=7561553

# Background: replace long narrative with concise points.
$s=$p.Slides.Item(3)
foreach($shape in $s.Shapes){
  if($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1 -and $shape.TextFrame.TextRange.Text -like '*Gunung Ibu dan Gunung Lewotolok merupakan*'){
    $shape.TextFrame.TextRange.Text="• Erupsi efusif dapat mengeluarkan lava secara terus-menerus.`r• Volume lava tidak praktis diukur langsung dan pemantauan lapangan memiliki keterbatasan.`r• Volume/laju lava berkaitan dengan perkembangan aktivitas dan potensi bahaya.`r• Karena itu diperlukan estimasi berkala dari data penginderaan jauh.`r• Sistem ini memanfaatkan hotspot MODIS untuk mengestimasi effusion rate dan volume lava pada Gunung Ibu dan Gunung Lewotolok."
    $shape.TextFrame.TextRange.Font.Size=16
  }
}

# Tools: add clear role rationale.
$s=$p.Slides.Item(4)
Add-Text $s 'Mengapa tools ini?  Python mengotomatisasi scraping dan kalkulasi; Flask menghubungkan data ke web; MySQL menjaga riwayat data; React menampilkan hasil secara mudah; Docker menjaga layanan konsisten.' 75 475 825 36 11 $muted | Out-Null

# Data source and Harris attribution.
$s=$p.Slides.Item(5)
Add-Text $s 'Sumber data web: MPODVolc (MODIS Volcano Monitoring) — modis.higp.hawaii.edu. Collector melakukan request berkala, memvalidasi format, lalu memfilter koordinat sesuai area masing-masing gunung.' 75 450 810 42 11 $muted | Out-Null
$s=$p.Slides.Item(7)
Add-Text $s 'Metode: pendekatan Andrew J. L. Harris. Radiance termal MODIS dikonversi menjadi estimasi effusion rate; kemudian dikalikan selang waktu untuk membentuk estimasi volume lava kumulatif.' 75 445 810 34 11 $muted | Out-Null
Add-Text $s 'Harris, A. J. L. & Ripepe, M. (2007). Regional earthquake as a trigger for enhanced volcanic activity: Evidence from MODIS thermal data.' 75 488 810 20 8 $muted | Out-Null

# Visual evidence slides inserted before the thank-you slide.
$dash=(Join-Path (Get-Location) 'dashboard-ppt.png')
$calc=(Join-Path (Get-Location) 'perhitungan-ppt.png')
$chart=(Join-Path (Get-Location) 'thermal-chart-ppt.png')
$s=$p.Slides.Add(14,12)
Add-Text $s 'IMPLEMENTASI WEB' 55 34 300 18 10 $teal | Out-Null
$t=Add-Text $s 'Dashboard pemantauan yang telah dibangun' 55 62 820 34 25 $navy; $t.TextFrame.TextRange.Font.Bold=-1
Add-Text $s 'Pengguna memilih gunung dan periode pengamatan untuk melihat hasil estimasi dari data MODIS.' 55 108 820 20 11 $muted | Out-Null
Add-Text $s 'Dashboard menyediakan:' 75 175 300 22 16 $navy | Out-Null
Add-Text $s '• Pemilihan gunung dan periode`r• Grafik estimasi effusion rate/volume`r• Data MODIS dan detail perhitungan`r• Unduh data CSV' 75 215 360 140 15 $ink | Out-Null
Add-Text $s 'Tampilan dashboard aktual telah diuji pada layanan lokal; gunakan screenshot dashboard-ppt.png sebagai visual saat menambahkannya manual di PowerPoint.' 75 425 770 32 10 $muted | Out-Null

$s=$p.Slides.Add(15,12)
Add-Text $s 'IMPLEMENTASI WEB' 55 34 300 18 10 $teal | Out-Null
$t=Add-Text $s 'Tabel perhitungan dan grafik hasil olahan' 55 62 820 34 25 $navy; $t.TextFrame.TextRange.Font.Bold=-1
Add-Text $s 'Output sistem dapat ditelusuri dalam bentuk detail perhitungan dan grafik termal.' 55 108 820 20 11 $muted | Out-Null
Add-Text $s 'Data mentah MODIS' 75 185 300 25 17 $teal | Out-Null
Add-Text $s '→ Filter area gunung`r→ Tabel observasi' 75 230 300 60 14 $ink | Out-Null
Add-Text $s 'Perhitungan Harris' 360 185 300 25 17 $orange | Out-Null
Add-Text $s '→ Effusion rate`r→ Volume kumulatif' 360 230 300 60 14 $ink | Out-Null
Add-Text $s 'Grafik monitoring' 650 185 300 25 17 $navy | Out-Null
Add-Text $s '→ Tren aktivitas`r→ Interpretasi perubahan' 650 230 300 60 14 $ink | Out-Null
Add-Text $s 'Screenshot aktual tabel dan grafik tersedia sebagai perhitungan-ppt.png dan thermal-chart-ppt.png untuk dimasukkan bila diperlukan.' 75 475 810 22 10 $muted | Out-Null

$s=$p.Slides.Add(16,12)
Add-Text $s 'REFERENSI' 55 34 300 18 10 $teal | Out-Null
$t=Add-Text $s 'Referensi data dan metode' 55 62 820 34 25 $navy; $t.TextFrame.TextRange.Font.Bold=-1
Add-Text $s '1. MODIS Volcano Monitoring (MPODVolc). University of Hawaii at Manoa. https://modis.higp.hawaii.edu/' 75 170 800 36 15 $ink | Out-Null
Add-Text $s '2. Harris, A. J. L. & Ripepe, M. (2007). Regional earthquake as a trigger for enhanced volcanic activity: Evidence from MODIS thermal data.' 75 255 800 50 15 $ink | Out-Null
Add-Text $s '3. Data hotspot MODIS Gunung Ibu dan Gunung Lewotolok yang dikumpulkan dan difilter oleh sistem.' 75 365 800 36 15 $ink | Out-Null
Add-Text $s 'Lengkapi volume/nomor halaman jurnal Harris sesuai format sitasi instansi sebelum presentasi final.' 75 475 800 28 11 $muted | Out-Null

$p.Save()
$p.Close()
$ppt.Quit()
