# Heatmap Dubai backend. Requires Docker + a .env (cp .env.example .env).
.PHONY: up down logs seed test refresh

# Build and start db -> loader (seeds once) -> api
up:
	docker compose up -d --build

# Stop containers (data volume kept). Use `docker compose down -v` to wipe the db.
down:
	docker compose down

# Follow db/api/loader logs
logs:
	docker compose logs -f --tail=100

# Re-run the idempotent loader against the seeded db (reads ./web/data)
seed:
	docker compose run --rm --build loader

# Unit + integration tests, run in a one-off container on the compose network.
# Isolation: the destructive loader test uses a throwaway DB "<POSTGRES_DB>_test"
# (TEST_DATABASE_URL), created before and dropped after. The read-only endpoint
# tests use the seeded DATABASE_URL db, which is never truncated.
test:
	docker compose up -d --wait db
	docker compose exec -T db sh -c 'psql -U "$$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$${POSTGRES_DB}_test\"" -c "CREATE DATABASE \"$${POSTGRES_DB}_test\""'
	docker compose run --rm --no-deps --build \
	  -v $(CURDIR)/api/tests:/srv/tests:ro -v $(CURDIR)/sql:/sql:ro \
	  -e SCHEMA_PATH=/sql/01_schema.sql -e COMMUNITIES_GEOJSON=/data/communities.geojson -e PYTHONDONTWRITEBYTECODE=1 \
	  api sh -c 'TEST_DATABASE_URL="$${DATABASE_URL}_test" python -m pytest -p no:cacheprovider tests -q'; \
	rc=$$?; \
	docker compose exec -T db sh -c 'psql -U "$$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$${POSTGRES_DB}_test\""'; \
	exit $$rc

# Re-pull from DDA (needs creds in .env; STG or PROD per ENVIRONMENT), rewrite
# web/data/*.json, then reload the db.
refresh:
	python3 scripts/export_web_data.py
	$(MAKE) seed
