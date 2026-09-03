FROM mysql:8.4

# Diproses otomatis oleh entrypoint MySQL hanya ketika volume /var/lib/mysql kosong.
COPY database/init.sql /docker-entrypoint-initdb.d/01-schema.sql
COPY database/railway_seed.sql /docker-entrypoint-initdb.d/02-seed.sql
