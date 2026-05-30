#!/usr/bin/env bash
set -euo pipefail

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGDATABASE="${PGDATABASE:-postgres}"

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required. On macOS: brew install postgresql@16"
  exit 1
fi

if ! command -v pg_isready >/dev/null 2>&1; then
  echo "pg_isready is required. On macOS: brew install postgresql@16"
  exit 1
fi

if ! command -v createdb >/dev/null 2>&1; then
  echo "createdb is required. On macOS: brew install postgresql@16"
  exit 1
fi

if ! pg_isready -h "$PGHOST" -p "$PGPORT" >/dev/null 2>&1; then
  echo "Postgres is not accepting connections at $PGHOST:$PGPORT."
  echo "On macOS: brew services start postgresql@16"
  exit 1
fi

psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'debugra') THEN
    CREATE ROLE debugra LOGIN PASSWORD 'debugra';
  ELSE
    ALTER ROLE debugra LOGIN PASSWORD 'debugra';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lms') THEN
    CREATE ROLE lms LOGIN PASSWORD 'lms';
  ELSE
    ALTER ROLE lms LOGIN PASSWORD 'lms';
  END IF;

  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'shop') THEN
    CREATE ROLE shop LOGIN PASSWORD 'shop';
  ELSE
    ALTER ROLE shop LOGIN PASSWORD 'shop';
  END IF;
END
$$;
SQL

for db in debugra lms shop; do
  owner="$db"
  exists="$(psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -Atqc "SELECT 1 FROM pg_database WHERE datname = '$db'")"
  if [[ "$exists" != "1" ]]; then
    createdb -h "$PGHOST" -p "$PGPORT" -O "$owner" "$db"
  fi
  psql -h "$PGHOST" -p "$PGPORT" -d "$PGDATABASE" -v ON_ERROR_STOP=1 -c "ALTER DATABASE $db OWNER TO $owner;" >/dev/null
done

echo "Native Postgres databases are ready at $PGHOST:$PGPORT."
