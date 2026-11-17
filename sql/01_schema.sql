-- Dubai bus backend schema (PostgreSQL 16)

CREATE TABLE IF NOT EXISTS dim_stop (
    stop_sk   serial PRIMARY KEY,
    stop_id   integer NOT NULL UNIQUE,
    stop_name text,
    lat       double precision,
    lon       double precision
);
CREATE INDEX IF NOT EXISTS idx_dim_stop_latlon ON dim_stop (lat, lon);

CREATE TABLE IF NOT EXISTS dim_community (
    community_sk   serial PRIMARY KEY,
    community_num  integer NOT NULL UNIQUE,
    community_name text
);

CREATE TABLE IF NOT EXISTS dim_route (
    route_sk   serial PRIMARY KEY,
    route_name text NOT NULL UNIQUE,
    route_type text,
    stop_count integer NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fact_coverage (
    coverage_sk           serial PRIMARY KEY,
    community_num         integer NOT NULL UNIQUE
                          REFERENCES dim_community (community_num),
    population            integer NOT NULL DEFAULT 0,
    accessible_population integer NOT NULL DEFAULT 0,
    geographic_coverage   double precision NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fact_passengers_monthly (
    passenger_sk bigserial PRIMARY KEY,
    stop_id      integer NOT NULL REFERENCES dim_stop (stop_id),
    month        text NOT NULL CHECK (month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),  -- 'YYYY-MM'
    direction    text NOT NULL CHECK (direction IN ('in', 'out')),
    count        integer NOT NULL DEFAULT 0,
    placeholder  boolean NOT NULL DEFAULT false,
    UNIQUE (stop_id, month, direction)
);
CREATE INDEX IF NOT EXISTS idx_fpm_month ON fact_passengers_monthly (month);
