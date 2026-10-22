# Octo Sync

**Live:** <https://example.com>

A football data synchronization and match-outcome prediction system. It scrapes fixtures, results and bookmaker odds from **Fotmob** and **Oddsportal** into PostgreSQL, builds features and trains XGBoost classifiers, and serves fixtures, match details, predictions and LLM chat through FastAPI. The crawler and the API are independent processes.

| Entry point | Command |
|---|---|
| Crawler / API | `python launcher.py {crawler,api}` or `./octo.sh <role> start -d` |
| Dataset / training | `./ml.sh {dataset,model} ...` |
| Maintenance | `./tools.sh` |
| Containers | `docker-compose -f docker/docker-compose.yml ...` |

All commands run from the project root.

## Architecture

```text
Fotmob API JSON                 Oddsportal page hooks / DOM
        │                                │
        └───────────────┬────────────────┘
                        ▼
        Camoufox page pool + interceptors        (core/browser)
                        │
        raw tables (fotmob.*, oddsportal.*)
                        │  parse.* / map.* tasks
        structured tables + cross-site fixture mapping
                        │  build.fotmob.{elo_rating,form_cache,prediction}
        artifacts/dataset/{training,prediction}
                        │  scripts/train.py (XGBoost + BayesSearchCV)
        artifacts/models, artifacts/reports
                        │
        FastAPI (api role): /health, /api/v1/*, /admin/*, WebSocket chat
```

## Layout

```text
launcher.py                process entry point: {crawler,api}
octo.sh  ml.sh  tools.sh   lifecycle / dataset+training / maintenance wrappers
configs/config.yml         business configuration
alembic/                   migrations
core/
  browser/                 Camoufox page pool, interceptors, site addons
  tasks/                   poll tasks: sync / parse / map / build / scan
  scheduler/               registry, executor, poll and cron managers
  store/                   PostgreSQL (models, DAO, seeds) and Redis
  services/                league, match, model, auth, ML, email, chat
  server/http/             FastAPI app, controllers, schemas
  chat/ config/ logger/ types/ utils/
scripts/                   build_sample / train / eval / translate_names / backfill_match_venues
docker/                    Dockerfile, compose stack, runbook
artifacts/ assets/ output/logs/    generated, git-ignored
```

## Data sources

| Site | Capture method | Tasks |
|---|---|---|
| `fotmob` | Camoufox intercepts API JSON responses | `sync.fotmob.*`, `parse.fotmob.*`, `build.fotmob.{elo_rating,form_cache,prediction}` |
| `oddsportal` | Page JS hook (`JSON.parse` tracer addon) or DOM parsing | `sync.oddsportal.*`, `parse.oddsportal.*`, `map.oddsportal.fixture` |

Task names follow `{action}.{site}.{entity}` and are registered with `@TaskRegistry.poll(...)` under `core/tasks/sync/{site}/`. `TASK_INCLUDE` / `TASK_EXCLUDE` (regex on task names) partition poll tasks across nodes.

## Quick start

Python 3.13, PostgreSQL 15, Redis 7.

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

docker run -d --name octo-postgres -p 5432:5432 \
  -e POSTGRES_USER=octopus -e POSTGRES_PASSWORD=123456 -e POSTGRES_DB=octopus postgres:15
docker run -d --name octo-redis -p 6379:6379 redis:7-alpine

cp .env.example .env        # set DB_URL, ASYNC_DB_URL, REDIS_URL, HTTP_HOST/PORT, JWT_SECRET, *_SALT
alembic upgrade head        # creates tables; the database and role must already exist
python -m camoufox fetch    # crawler browser, not needed by the API

./octo.sh crawler start -d  # logs -> output/logs/octo-crawler.log
./octo.sh api start -d      # logs -> output/logs/octo-api.log

curl -s "http://127.0.0.1:${HTTP_PORT:-8000}/health"   # {"status":"healthy"}
```

`./octo.sh <crawler|api> [monitor] start|stop [-d]`; without `-d` the process stays in the foreground. On a headless Linux server run the crawler with `OCTO_ENABLE_XVFB=1`.

## Configuration

| Variable | Purpose |
|---|---|
| `ENV` | `dev` / `prod` / `ml` (Swagger docs are registered only in `dev`) |
| `DB_URL` / `ASYNC_DB_URL` | sync and asyncpg connection URLs |
| `REDIS_URL` | cache, OTP codes, JWT blacklist |
| `HTTP_HOST` / `HTTP_PORT` | uvicorn bind address and port (`0.0.0.0` to expose) |
| `JWT_SECRET` | HS256 signing key |
| `MATCH_CODE_SALT` / `TEAM_CODE_SALT` / `PLAYER_CODE_SALT` | public code generation |

Optional: `TASK_INCLUDE` / `TASK_EXCLUDE`, `CORS_ALLOW_ORIGINS`, `DOCS_USERNAME` / `DOCS_PASSWORD`, `ADMIN_USERNAME` / `ADMIN_PASSWORD`, `TURNSTILE_SECRET`, one mail provider (`BREVO_API_KEY`, `MAILJET_API_KEY` + `MAILJET_API_SECRET`, or `RESEND_API_KEY`), `EMAIL_WHITELIST` (comma-separated addresses exempt from OTP limits), and LLM keys (`GEMINI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY`).

`configs/config.yml` holds `logger`, `task_thread_pool`, `browser`, `database`, `resource` (artifact roots), `training` (`winball_club` / `winball_national`) and `llm`. Keep real secrets out of the repository.

## Machine learning

```bash
./ml.sh dataset -t club start -d                    # -t national for national teams
./ml.sh model -t club -f <dataset>.csv start -d     # -b enables class balancing
./ml.sh model list
./ml.sh model -t club -v <version> eval
```

`-f` is a dataset file in `artifacts/dataset/training/`. Models and reports land in `artifacts/models` and `artifacts/reports`; the underlying scripts are `scripts/{build_sample,train,eval}.py`.

## Docker

```bash
mkdir -p docker/data/{postgresql,redis,api,crawler}
docker-compose -f docker/docker-compose.yml build
docker-compose -f docker/docker-compose.yml up -d --no-build
curl -s "http://localhost:${HOST_HTTP_PORT:-8080}/health"
```

State stays in `docker/data/`, code is baked into the image. See [docker/README.md](docker/README.md).
