# Docker

Containerized runtime for octo_sync. A single application image (`octo-sync:latest`) runs in two roles — `api` and `crawler` — next to PostgreSQL, Redis, and a one-shot Alembic migration service.

All commands below are run from the project root (`octo_sync/`).

> **Use the hyphenated `docker-compose` binary here.** The Compose v2 CLI plugin (`docker compose ...`) is not installed in this environment; see [Troubleshooting](#troubleshooting).

## TL;DR

```bash
mkdir -p docker/data/postgresql docker/data/redis docker/data/api docker/data/crawler
docker-compose -f docker/docker-compose.yml build          # first build is long, see Requirements
docker-compose -f docker/docker-compose.yml up -d --no-build
docker-compose -f docker/docker-compose.yml ps -a          # api: Up (healthy), migrate: Exited (0)
curl -s http://localhost:8080/health                       # {"status":"healthy"}
```

> Tip: `alias dc='docker-compose -f docker/docker-compose.yml'` makes the rest of this page short (`dc ps -a`). Every example spells the command out so it can be copy-pasted as is.

## Services

| Service | Image / command | Role | Host port | Restart policy | Health check |
|---|---|---|---|---|---|
| `postgres` | `postgres:15` | Database, PGDATA in `docker/data/postgresql` | — | `unless-stopped` | `pg_isready` |
| `redis` | `redis:7-alpine` (AOF on) | Cache, OTP codes, token blacklist | — | `unless-stopped` | `redis-cli ping` |
| `migrate` | `alembic upgrade head` | One-shot schema migration, then exits | — | `"no"` | none |
| `api` | `python launcher.py api` | HTTP API: `/health`, `/api/*`, `/admin/*` | `${HOST_HTTP_PORT:-8080}` → 8080 | `unless-stopped` | `GET /health` |
| `crawler` | `python launcher.py crawler` | Poll tasks and Camoufox browser | — | `unless-stopped` | disabled |

Startup order is enforced by `depends_on`:

```text
postgres (healthy) ──► migrate (exit 0) ──► api / crawler
redis    (healthy) ──────────────────────► api / crawler
```

`migrate` runs once per `up` and then exits; `restart: "no"` stops Docker from restarting it, and `api`/`crawler` use `condition: service_completed_successfully`, so a failed migration keeps them from starting at all.

## Requirements

- Docker Engine 24+ and Compose v2 (`docker-compose`).
- macOS: Docker Desktop or Colima running (`colima start`).
- Free host port `8080`, or set `HOST_HTTP_PORT`.
- ~6 GB disk: the image is ~4.4 GB, and the first build additionally downloads the Camoufox browser (~1.3 GB) plus Playwright Firefox dependencies.
- No entrypoint wrapper: the image starts the container command directly, so `docker-compose exec` and `docker run ... <cmd>` behave normally.

## First start

1. Start the daemon and confirm the CLI can reach it:

   ```bash
   colima start          # macOS; "already running, ignoring" is a no-op
   docker info >/dev/null 2>&1 && echo "docker OK"
   ```

   The exit code is what matters. `docker info` may print `WARNING: bridge-nf-call-iptables is disabled` (and the ip6 variant) from the Colima VM kernel; it is cosmetic here — container-to-container DNS and published ports work regardless — so it can be ignored.

2. Create the bind-mount directories. They must exist and be writable by uid 1000, otherwise the API cannot write its log file:

   ```bash
   mkdir -p docker/data/postgresql docker/data/redis docker/data/api docker/data/crawler
   ```

3. Build the image:

   ```bash
   docker-compose -f docker/docker-compose.yml build
   ```

   The build ends with `Successfully tagged octo-sync:latest`. It pulls `python:3.13-slim-bookworm`, installs `requirements.txt` into `/opt/venv`, installs Playwright Firefox deps, downloads Camoufox, and finally copies the repo into `/app`.

4. Start the stack (`--no-build` prevents an accidental rebuild):

   ```bash
   docker-compose -f docker/docker-compose.yml up -d --no-build
   ```

   Dependencies start in order: `postgres` → `redis` → `migrate` (exits 0) → `api`. Passing a service name (`... up -d --no-build api`) also starts its dependencies.

5. Validate the stack with the checklist below.

## Verification checklist

| # | What to check | Command | Expected |
|---|---|---|---|
| 1 | Container states | `docker-compose -f docker/docker-compose.yml ps -a` | `api` `Up (healthy)`, `migrate` `Exited (0)`, `postgres`/`redis` `Up (healthy)` |
| 2 | API liveness | `curl -s http://localhost:8080/health` | `{"status":"healthy"}` |
| 3 | Migration state | `docker-compose -f docker/docker-compose.yml run --rm migrate alembic current` | `<revision> (head)`, e.g. `4aede1663e9b (head)` |
| 4 | Schema created | `docker-compose -f docker/docker-compose.yml exec -T postgres psql -U octopus -d octopus -c '\dt'` | table list, no `ERROR` |
| 5 | Reference data seeded | `docker-compose -f docker/docker-compose.yml exec -T postgres psql -U octopus -d octopus -c 'select count(*) from canonical_leagues;'` | a positive count |
| 6 | API application log | `docker-compose -f docker/docker-compose.yml logs --tail 50 api` | startup lines, no traceback |
| 7 | Crawler | `docker-compose -f docker/docker-compose.yml logs --tail 50 crawler` | poll manager / task startup lines |

The `psql` checks assume the default `POSTGRES_USER=octopus` and `POSTGRES_DB=octopus`; adjust if you overrode them.

`ps -a` looks like this (image built after the entrypoint removal):

```text
NAME                   IMAGE              COMMAND                  SERVICE    STATUS                      PORTS
octo-sync-api-1        octo-sync:latest   "python launcher.py …"   api        Up 12 seconds (healthy)     0.0.0.0:8080->8080/tcp
octo-sync-crawler-1    octo-sync:latest   "python launcher.py …"   crawler    Up 12 seconds
octo-sync-migrate-1    octo-sync:latest   "alembic upgrade head"   migrate    Exited (0) 20 seconds ago
octo-sync-postgres-1   postgres:15        "docker-entrypoint.s…"   postgres   Up 25 seconds (healthy)     5432/tcp
octo-sync-redis-1      redis:7-alpine     "docker-entrypoint.s…"   redis      Up 25 seconds (healthy)     6379/tcp
```

If the COMMAND column still shows `/app/docker/entrypo…`, you are running an older image — rebuild it.

To wait for readiness before hitting the API (the healthcheck has a 120 s `start_period` because startup loads config, DB, and league data):

```bash
until curl -fsS http://localhost:8080/health >/dev/null; do sleep 2; done
```

### API surface

- `GET /health` — public, returns `{"status":"healthy"}`.
- `/api/*` — fixtures, matches, leagues, auth, conversations.
- `/admin/*` — models, data, raw-data upload; requires `ADMIN_USERNAME` + `ADMIN_PASSWORD` (HTTP Basic).
- `/docs`, `/redoc`, `/openapi.json` — registered only when `ENV=dev` **and** both `DOCS_USERNAME` / `DOCS_PASSWORD` are set.

## Daily operations

| Goal | Command |
|---|---|
| Start / reconcile | `docker-compose -f docker/docker-compose.yml up -d --no-build` |
| Stop (keep containers) | `docker-compose -f docker/docker-compose.yml stop` |
| Start again | `docker-compose -f docker/docker-compose.yml start` |
| Restart one service | `docker-compose -f docker/docker-compose.yml restart api` |
| Remove containers + network (keeps data) | `docker-compose -f docker/docker-compose.yml down` |
| `down -v` (removes named volumes) | `docker-compose -f docker/docker-compose.yml down -v` — this stack uses no named volumes, so all state under `docker/data/` survives |

`up` also restarts the exited `migrate` container, so migrations are re-applied on every `up`. That is safe: `alembic upgrade head` is a no-op once the DB is at head.

## When to rebuild, when to just restart

The code is copied into the image; only `configs/`, `artifacts/`, `assets/`, and `docker/data/` are bind mounts.

| Changed | Rebuild needed? | Action |
|---|---|---|
| `core/**`, `launcher.py`, `scripts/**`, `alembic/**` | **Yes** | `build` then `up -d --no-build` |
| `requirements.txt` | **Yes** (slow: pip layer) | `build` then `up -d --no-build` |
| New file in `alembic/versions/` | **Yes** — `migrate` has no volume mount | `build` then `up -d --no-build` |
| `configs/config.yml`, keys | No (read-only bind mount) | `restart api`, `restart crawler` |
| `assets/**`, `artifacts/**` | No (bind mounts) | nothing, next task run picks them up |
| `docker/docker-compose.yml` | No (image unchanged) | `up -d` (Compose recreates changed services) |

Rebuild commands:

```bash
docker-compose -f docker/docker-compose.yml build
docker-compose -f docker/docker-compose.yml up -d --no-build
```

## Configuration

`docker-compose.yml` is self-contained: every required variable has a development default, so no env file is needed for a local run.

| Variable | Default | Purpose |
|---|---|---|
| `ENV` | `dev` | `dev` / `prod` / `ml`; controls docs registration |
| `HOST_HTTP_PORT` | `8080` | Host port published for the API |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `octopus` / `123456` / `octopus` | Database credentials |
| `DB_URL` / `ASYNC_DB_URL` | derived from the line above | Built as `postgresql://` and `postgresql+asyncpg://` at `postgres:5432` |
| `REDIS_URL` | `redis://redis:6379/0` | Redis |
| `JWT_SECRET` | `change_me_jwt_secret` | HS256 signing |
| `MATCH_CODE_SALT` / `TEAM_CODE_SALT` / `PLAYER_CODE_SALT` | `change_me_*` | Code generation |
| `CORS_ALLOW_ORIGINS` | `*` | Browser origins |
| `DEEPSEEK_API_KEY` | empty | Passed empty on purpose; chat checks that it exists |

Optional features (task filtering, docs/admin credentials, mail providers, LLM keys) are listed as commented entries in the `x-app-env` anchor. Uncomment and set the ones you need — **only variables listed there reach the containers**.

Overrides can be exported in the shell:

```bash
POSTGRES_PASSWORD=change_me JWT_SECRET=$(openssl rand -hex 32) \
docker-compose -f docker/docker-compose.yml up -d --no-build
```

`POSTGRES_PASSWORD` is embedded into `DB_URL`; URL-encode characters such as `@`, `:`, `/`, `#`. Once the database directory has been initialized, changing `POSTGRES_PASSWORD` or `POSTGRES_USER` no longer applies (see [Reset stack data](#reset-stack-data)).

### `.env` is not read from the project root

Compose resolves its env file from the **project directory**, which for `-f docker/docker-compose.yml` is `docker/`. The repo-root `.env` is therefore ignored — verified: the root `.env` contains a different `JWT_SECRET`, yet the container receives `change_me_jwt_secret`. Options:

```bash
docker-compose --env-file .env -f docker/docker-compose.yml up -d --no-build   # explicit
cp .env docker/.env                                                            # or place it next to the compose file
```

`.env` is also excluded from the image (`.dockerignore`), so the containers only ever see what Compose passes in `x-app-env`.

Sanity-check the resolved configuration before starting:

```bash
docker-compose -f docker/docker-compose.yml config >/dev/null    # validates and renders the model
```

## Data layout and mounts

```text
docker/data/
├── postgresql/    PostgreSQL PGDATA
├── redis/         Redis AOF
├── api/logs/      API file logs (octopus.log)
└── crawler/logs/  crawler file logs (octopus.log)
```

Both `api` and `crawler` mount their data dir at `/app/output`; the logger writes to `output/logs/octopus.log` (relative to `/app`), which is why the file shows up as `docker/data/<role>/logs/octopus.log` on the host.

Mounts coming from the project root:

| Host path | Container path | Mode | Used by |
|---|---|---|---|
| `configs/` | `/app/configs` | read-only | `api`, `crawler` |
| `artifacts/` | `/app/artifacts` | read-only | `api` (model/report reads) |
| `artifacts/` | `/app/artifacts` | read-write | `crawler` (dataset/training output) |
| `assets/` | `/app/assets` | read-write | `crawler` |
| `docker/data/api` | `/app/output` | read-write | `api` |
| `docker/data/crawler` | `/app/output` | read-write | `crawler` |

The containers run as `appuser` (uid/gid 1000). On Linux, make sure the bind-mount directories are owned by that uid:

```bash
sudo chown -R 1000:1000 docker/data/api docker/data/crawler artifacts assets
```

`docker/data/` is git-ignored; the mount points must exist before `up`, otherwise Docker creates them as root and the containers cannot write.

## Logs

```bash
docker-compose -f docker/docker-compose.yml logs -f api
docker-compose -f docker/docker-compose.yml logs -f crawler
docker-compose -f docker/docker-compose.yml logs migrate          # migration output, then it exits
docker-compose -f docker/docker-compose.yml logs --tail 100 postgres
```

File logs (survive restarts and `down`):

```bash
tail -f docker/data/api/logs/octopus.log
tail -f docker/data/crawler/logs/octopus.log
```

The `crawler` healthcheck is disabled on purpose (a long-running browser task is not a simple liveness probe), so verify it with `ps` (`Up …`) plus its logs.

## Migrations

`migrate` runs `alembic upgrade head` before `api`/`crawler` start, configured entirely through `DB_URL` from `x-app-env`. Alembic reads `alembic.ini` from `/app` and injects the URL at runtime (`alembic/env.py`).

Inspect the current state:

```bash
docker-compose -f docker/docker-compose.yml run --rm migrate alembic current
docker-compose -f docker/docker-compose.yml run --rm migrate alembic history --verbose | head -40
```

Run the migration explicitly (same command the service uses):

```bash
docker-compose -f docker/docker-compose.yml run --rm migrate
```

Notes and gotchas:

- `migrate` has **no volume mounts**, so migrations inside the image are the ones from the last build. After adding a file under `alembic/versions/`, rebuild the image, otherwise the old set of migrations runs.
- Keeping `migrate` one-shot (`restart: "no"`) is required: an `always` policy on a container that exits immediately produces a restart loop, and `api`/`crawler` rely on `service_completed_successfully`.
- If `migrate` exits non-zero, `api` and `crawler` never start. Read `logs migrate` — the usual causes are an unreachable database or bad credentials in `DB_URL`.
- Generate new revisions on the **host** (`.venv/bin/alembic revision --autogenerate -m "..."` with `DB_URL` exported), not inside the container: any file created in `/app/alembic` inside the container is lost with it.
- `api` and `crawler` import league reference data (`core/store/postgres/seeds/leagues.sql`) at startup, after migrations and before league mappings load.

## Run one role only

```bash
docker-compose -f docker/docker-compose.yml up -d --no-build api
docker-compose -f docker/docker-compose.yml up -d --no-build crawler
```

Dependencies (`postgres`, `redis`, `migrate`) start automatically, and the other role is left untouched. To stop a single role:

```bash
docker-compose -f docker/docker-compose.yml stop crawler
```

## Ad-hoc commands inside the stack

The image has no entrypoint wrapper, so commands are executed as given:

```bash
# shell in the running API container (uid 1000)
docker-compose -f docker/docker-compose.yml exec api sh

# throwaway container with the same image, env, and mounts
docker-compose -f docker/docker-compose.yml run --rm crawler python -c 'import sys; print(sys.version)'

# database / redis
docker-compose -f docker/docker-compose.yml exec postgres psql -U octopus -d octopus
docker-compose -f docker/docker-compose.yml exec redis redis-cli
```

Build training samples (writes into `artifacts/dataset/training`, mounted read-write for the crawler):

```bash
docker-compose -f docker/docker-compose.yml run --rm crawler \
  python scripts/build_sample.py \
  --league_ids 101 102 103 104 105 100 \
  --min_season 2019 --max_season 2025 \
  --model_type club --sample_format parquet
```

Model training is normally run on the ML server with `./ml.sh`.

## Reset stack data

Stops and removes everything, then drops the local state:

```bash
docker-compose -f docker/docker-compose.yml down
sudo rm -rf docker/data/postgresql docker/data/redis docker/data/api docker/data/crawler
mkdir -p docker/data/postgresql docker/data/redis docker/data/api docker/data/crawler
docker-compose -f docker/docker-compose.yml up -d --no-build
```

The next `up` re-initializes PostgreSQL (role `octopus`, database `octopus`, password `123456` unless overridden), re-runs all migrations, and the launchers re-seed `canonical_leagues`.

`down -v` is not enough for this reset: the state lives in bind mounts, not named volumes. Deleting only `docker/data/api` and `docker/data/crawler` just clears logs.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Cannot connect to the Docker daemon` | Daemon not running: `colima start` (macOS) or start Docker Desktop. |
| `WARNING: bridge-nf-call-iptables is disabled` (and `…ip6tables`) | Cosmetic warning from the Colima/Lima VM kernel printed by `docker info`; networking and published ports are unaffected. |
| `docker: unknown command: docker compose` | Compose CLI plugin is missing — use `docker-compose` (with the hyphen). |
| `ERROR: BuildKit is enabled but the buildx component is missing or broken` | `DOCKER_BUILDKIT` is set but the buildx plugin is absent: unset it (`DOCKER_BUILDKIT=0 docker-compose … build`) or install buildx. |
| `--no-build` fails with a missing image | Build first: `docker-compose -f docker/docker-compose.yml build`. |
| `Bind for 0.0.0.0:8080 failed: port is already allocated` | Another API is running: `HOST_HTTP_PORT=18080 docker-compose -f docker/docker-compose.yml up -d --no-build --force-recreate`. |
| `api` restarting or `(unhealthy)` | `logs api`; if it stops before logging, `ps -a` and `logs migrate`. Startup needs a reachable DB and a valid config. |
| `sqlalchemy.exc.OperationalError … could not translate host name "postgres"` | The container cannot reach the DB (not on the compose network, or DB not started). Inside compose this cannot happen unless `postgres` is down; outside compose there is no wait logic, so start PostgreSQL first. |
| `migrate` exits non-zero | `logs migrate`; typical: wrong `DB_URL` credentials, DB not ready, or a conflicting schema change. |
| `Permission denied` writing `/app/output/logs` | Linux host: `sudo chown -R 1000:1000 docker/data/api docker/data/crawler`. |
| Code changes have no effect | The code lives in the image: rebuild (`build` → `up -d --no-build`). Only `configs/`, `artifacts/`, `assets/`, `docker/data/` are mounted. |
| Root `.env` values are ignored | Compose reads `docker/.env`; use `--env-file .env` or copy it into `docker/`. |
| Migration re-runs on every `up` | Expected: `migrate` is one-shot and `up` restarts exited containers; `alembic upgrade head` is idempotent. |
| First build takes very long | Expected: pip install plus the ~1.3 GB Camoufox download and Playwright Firefox deps. |

## Environment notes

Facts about this workstation, verified while documenting the stack:

- `docker compose` (plugin form) is unavailable — only `docker-compose` (v2.38 standalone) works.
- The `buildx` plugin is missing, so `DOCKER_BUILDKIT=1` fails and builds use the legacy builder. The existing `octo-sync:latest` was produced with BuildKit, so legacy cache cannot be reused: the first `docker-compose build` here rebuilds every layer (apt, pip, Camoufox).
- Once a legacy build has run, only the layers after the invalidated one are rebuilt: changing application code re-runs just `COPY . .`, while changing `requirements.txt` re-runs the full pip install.
- Containers run as `appuser` (uid/gid 1000) and start the container command directly as PID 1, so `docker stop` delivers `SIGTERM` straight to `launcher.py` for a graceful shutdown.
