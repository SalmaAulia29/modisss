import time
from pathlib import Path

from connect_db import get_connection
from schema import ensure_schema

DUMP_FILE = Path(__file__).with_name("db_modis_pvmbg_railway.sql")

def bootstrap_database(retries=12, delay=5):
    """Isi database kosong satu kali; aman dipanggil web dan worker bersamaan."""
    last_error = None
    for attempt in range(retries):
        try:
            with get_connection() as db:
                cursor = db.cursor()
                cursor.execute("SELECT GET_LOCK('modis_database_bootstrap', 60)")
                if cursor.fetchone()[0] != 1:
                    raise RuntimeError("Tidak berhasil memperoleh bootstrap lock")
                try:
                    cursor.execute("""SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_schema=DATABASE() AND table_name='volcanoes'""")
                    if cursor.fetchone()[0] == 0:
                        script = DUMP_FILE.read_text(encoding="utf-8")
                        statement = []
                        for line in script.splitlines():
                            if not line.strip() or line.lstrip().startswith("--"):
                                continue
                            statement.append(line)
                            if line.rstrip().endswith(";"):
                                cursor.execute("\n".join(statement))
                                if cursor.with_rows:
                                    cursor.fetchall()
                                statement = []
                        db.commit()
                        print("[BOOTSTRAP] Struktur dan snapshot database berhasil dimuat.", flush=True)
                    else:
                        print("[BOOTSTRAP] Database sudah berisi tabel; seed dilewati.", flush=True)
                finally:
                    cursor.execute("SELECT RELEASE_LOCK('modis_database_bootstrap')")
                    cursor.fetchone()
                    cursor.close()
            ensure_schema()
            return
        except Exception as exc:
            last_error = exc
            print(f"[BOOTSTRAP] Percobaan {attempt + 1}/{retries} gagal: {exc!r}", flush=True)
            time.sleep(delay)
    raise RuntimeError(f"Bootstrap database gagal: {last_error}")

if __name__ == "__main__":
    bootstrap_database()
