"""Entrypoint worker backend untuk Docker dan Railway."""

from update_modis import worker_loop


if __name__ == "__main__":
    worker_loop()
