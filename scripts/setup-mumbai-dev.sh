#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Starting Mumbai dev containers (PostGIS:5433, Redis:6380)..."
docker compose -f docker/docker-compose.mumbai-dev.yml up -d

echo "==> Waiting for PostGIS..."
until docker exec rapidpro-mumbai-postgis pg_isready -U temba -d temba_in >/dev/null 2>&1; do
  sleep 1
done

echo "==> Ensuring PostGIS extension..."
docker exec rapidpro-mumbai-postgis psql -U temba -d temba_in -c "CREATE EXTENSION IF NOT EXISTS postgis;"

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "Python 3.11 is required for main-in. Install it first, e.g.:"
  echo "  pyenv install 3.11.11 && pyenv local 3.11.11"
  exit 1
fi

echo "==> Configuring Poetry environment (Python 3.11)..."
poetry env use python3.11
poetry install

echo "==> Installing psycopg binary (if needed)..."
poetry run pip install 'psycopg[binary]' >/dev/null 2>&1 || true

echo "==> Linking dev settings..."
ln -sf settings.py.dev temba/settings.py

echo "==> Running migrations..."
poetry run python manage.py migrate

echo ""
echo "Mumbai dev environment is ready."
echo "Create a superuser:"
echo "  poetry run python manage.py shell -c \"from temba.users.models import User; u=User.objects.create_user('admin@example.com','admin1234',first_name='Admin',last_name='User',is_staff=True,is_superuser=True); u.set_verified(True); print(u.email)\""
echo ""
echo "Start the server (use 8001 if Ireland is on 8000):"
echo "  poetry run python manage.py runserver 8001"
