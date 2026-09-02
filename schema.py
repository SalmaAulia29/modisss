"""Migrasi skema idempoten untuk database baru maupun database yang sudah berjalan."""

from connect_db import get_connection


MIGRATIONS = (
    """
    CREATE TABLE IF NOT EXISTS worker_state (
        id TINYINT PRIMARY KEY,
        status VARCHAR(20) NOT NULL DEFAULT 'idle',
        interval_minutes INT NOT NULL DEFAULT 60,
        last_started_at DATETIME NULL,
        last_completed_at DATETIME NULL,
        next_run_at DATETIME NULL,
        last_error TEXT NULL,
        worker VARCHAR(100) NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """,
    """
    INSERT IGNORE INTO worker_state (id, status, interval_minutes)
    VALUES (1, 'idle', 60)
    """,
)


def ensure_schema():
    """Terapkan seluruh perubahan skema tanpa menghapus data yang sudah ada."""
    with get_connection() as connection:
        cursor = connection.cursor()
        for statement in MIGRATIONS:
            cursor.execute(statement)
        connection.commit()
        cursor.close()
