# MODIS Volcano Monitor

Dashboard Flask untuk memantau collector data MODIS, data terbaru per gunung, jumlah baris baru, respons HTTP, serta riwayat kegagalan. MySQL, web, dan worker berjalan sebagai container terpisah.

## Menjalankan

```bash
docker compose up --build -d
docker compose ps
```

Buka `http://localhost:5050`. Dashboard diperbarui otomatis setiap 30 detik. Status JSON tersedia di `http://localhost:5050/api/status` dan health check di `/health`.

Halaman estimasi volume lava tersedia di `http://localhost:5050/lava-volume`.

Database dapat dibuka melalui Adminer di `http://localhost:8081` dengan server `db`, pengguna dan password sesuai `.env`, serta database `db_modis_pvmbg`.

Pantau log collector:

```bash
docker compose logs -f worker
```

Ubah password, interval, port, tanggal awal, atau URL sumber di `.env`. Untuk produksi, wajib ganti seluruh password bawaan.

## Menjalankan satu kali

```bash
docker compose run --rm worker python update_modis.py
```

MySQL disimpan pada volume `modis_db`, sehingga data tetap ada saat container direstart.

Pada database/volume baru, image dari `Dockerfile.mysql` menjalankan
`db_modis_pvmbg_railway.sql` untuk membuat struktur sekaligus mengisi snapshot data.
Entrypoint MySQL hanya menjalankan dump ini ketika direktori data masih kosong.

## Railway

Import `docker-compose.yml` ke project Railway. Railway membuat setiap entri Compose
sebagai service terpisah. Pastikan service `db` memakai `Dockerfile.mysql` dan mempunyai
volume pada `/var/lib/mysql`. Snapshot awal akan masuk otomatis pada deployment database
pertama. Set variabel aplikasi `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, dan
`DB_NAME` memakai reference variables dari service MySQL. Generate domain publik hanya
untuk service `web`; service database dan worker tidak memerlukan domain publik.
