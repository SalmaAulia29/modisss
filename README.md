# MODIS Volcano Monitor

Aplikasi monitoring MODIS dengan arsitektur terpisah:

- `frontend/`: React, Vite, Tailwind CSS, dan Nginx.
- `backend/`: Flask API, worker collector, Matplotlib, dan Scikit-learn.
- `database/`: image MySQL, skema, dan snapshot data awal.

## Menjalankan lokal

```bash
docker compose up --build -d --remove-orphans
docker compose ps
```

Buka layanan berikut:

- Dashboard React: `http://localhost:5050`
- Adminer: `http://localhost:8081`
- Health check backend melalui frontend: `http://localhost:5050/health`

Frontend meneruskan request `/api`, `/charts`, dan `/health` ke backend. Worker tetap
berjalan ketika browser ditutup dan menyimpan hasil pengambilan ke MySQL sesuai
`FETCH_INTERVAL_MINUTES`.

Pantau worker:

```bash
docker compose logs -f worker
```

Jalankan collector satu kali:

```bash
docker compose run --rm worker python update_modis.py
```

## Development tanpa Docker

Jalankan Flask pada port 5000, kemudian jalankan Vite pada port 5173. Konfigurasi Vite
otomatis meneruskan request API ke Flask.

```bash
cd backend
python -m pip install -r requirements.txt
flask --app app run --port 5000
```

```bash
cd frontend
npm install
npm run dev
```

## Railway

Buat tiga service dari repository yang sama:

1. **backend** memakai Dockerfile `backend/Dockerfile`.
2. **worker** memakai Dockerfile `backend/Dockerfile` dengan Start Command
   `python worker.py`.
3. **frontend** memakai Dockerfile `frontend/Dockerfile` dan menjadi satu-satunya
   service yang diberi public domain.

Backend dan worker memakai reference variables dari service MySQL:

```text
DB_HOST=mysql.railway.internal
DB_PORT=3306
DB_NAME=railway
DB_USER=root
DB_PASSWORD=<reference MYSQLPASSWORD>
FETCH_INTERVAL_MINUTES=2
TZ=Asia/Jakarta
```

Frontend membutuhkan runtime variable berikut. Sesuaikan `backend` dengan nama service
backend di Railway:

```text
BACKEND_URL=http://backend.railway.internal:5000
```

Jangan membuat variable `PORT` secara manual pada frontend; Railway menyediakannya
otomatis. Backend memakai port internal tetap `5000` (`BACKEND_PORT` hanya diperlukan
jika memang ingin diganti). Snapshot `database/railway_seed.sql` dipakai hanya jika
database masih kosong; database yang sudah berisi tabel tidak akan ditimpa.
