#!/usr/bin/env sh
set -e

# Aguarda o banco de dados ficar disponível (quando DB_HOST estiver definido).
if [ -n "$DB_HOST" ]; then
  echo "Aguardando banco em $DB_HOST:${DB_PORT:-3306}..."
  while ! nc -z "$DB_HOST" "${DB_PORT:-3306}"; do
    sleep 1
  done
  echo "Banco disponível."
fi

echo "Aplicando migrations..."
flask --app run.py db upgrade

# Popula dados de exemplo apenas se solicitado (SEED_ON_START=1).
if [ "$SEED_ON_START" = "1" ]; then
  echo "Executando seed..."
  flask --app run.py seed || true
fi

exec "$@"
