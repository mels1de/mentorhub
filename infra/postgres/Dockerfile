# No official image ships both pgvector and PostGIS, so add PostGIS to the pgvector one.
# The extensions are only installed here; the first Alembic migration enables them.
FROM pgvector/pgvector:0.8.7-pg17-trixie

RUN apt-get update \
    && apt-get install -y --no-install-recommends "postgresql-${PG_MAJOR}-postgis-3" \
    && rm -rf /var/lib/apt/lists/*
