#!/bin/bash
set -e

echo "============================================================================="
echo "Apache Superset Initialization Script"
echo "============================================================================="

echo "Step 1: Waiting for PostgreSQL database to be ready..."
python -c "
import socket, time
for _ in range(30):
    try:
        with socket.create_connection(('postgres', 5432), timeout=1):
            break
    except OSError:
        time.sleep(2)
"

echo "✓ PostgreSQL is ready!"

echo "Step 2: Upgrading Superset database schema..."
superset db upgrade

echo "Step 3: Creating admin user..."
superset fab create-admin \
              --username admin \
              --firstname Admin \
              --lastname User \
              --email admin@superset.com \
              --password admin || true

echo "Step 4: Initializing roles and permissions..."
superset init

echo "============================================================================="
echo "Initialization Complete! Starting Superset webserver..."
echo "============================================================================="

# התיקון כאן: שינינו ל-gthread והוספנו threads
exec gunicorn \
      -w 2 \
      --threads 4 \
      -k gthread \
      --timeout 120 \
      -b  0.0.0.0:8088 \
      --limit-request-line 0 \
      --limit-request-field_size 0 \
      "superset.app:create_app()"