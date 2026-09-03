"""Konfigurasi koneksi MySQL untuk backend dan worker."""

import os
import mysql.connector


def get_connection():
    """Membuka koneksi memakai konfigurasi environment/Docker."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "modis"),
        password=os.getenv("DB_PASSWORD", "modis_password"),
        database=os.getenv("DB_NAME", "db_modis_pvmbg"),
        connection_timeout=10,
    )
