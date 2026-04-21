# apm-php-bench

Benchmark four PHP runtime/instrumentation variants under the same load profile and compare their telemetry and response time behavior.

## What this repo does

This stack runs:

- A Slim PHP app in 4 variants:
  - `uninstrumented` (uninstrumented)
  - `apm-php-9-alpha` ([solarwinds/apm](https://packagist.org/packages/solarwinds/apm) + [solarwinds/apm_ext](https://packagist.org/packages/solarwinds/apm_ext) + [swotel collector](https://github.com/solarwinds/solarwinds-otel-collector-releases))
  - `otel` (OpenTelemetry PHP auto-instrumentation)
  - `apm-8` (Current GA Solarwinds APM PHP library)
- A Locust load generator that continuously hits all 4 variants.
- Three collectors:
  - `otel-collector-locust` for Locust OTLP metrics export
  - `otel-collector-apm-php-9-alpha` for [solarwinds/apm](https://packagist.org/packages/solarwinds/apm) telemetry export
  - `otel-collector-otel` for OpenTelemetry PHP telemetry export

The default benchmark target route is `/complex`, which intentionally creates spans and emits app-side metrics/logs to stress instrumentation overhead.

## Architecture

| Component              | Service name                                         | Purpose                                                                                                                                                                                                                          | Host port |
|------------------------|------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| Slim baseline          | `nginx-uninstrumented` -> `php-fpm-uninstrumented`   | No APM instrumentation                                                                                                                                                                                                           | `8000`    |
| Slim + apm-php-9-alpha | `nginx-apm-php-9-alpha` -> `php-fpm-apm-php-9-alpha` | [solarwinds/apm](https://packagist.org/packages/solarwinds/apm) + [solarwinds/apm_ext](https://packagist.org/packages/solarwinds/apm_ext) + [swotel collector](https://github.com/solarwinds/solarwinds-otel-collector-releases) | `8001`    |
| Slim + otel            | `nginx-otel` -> `php-fpm-otel`                       | OpenTelemetry PHP auto-instrumentation exporting OTLP telemetry                                                                                                                                                                  | `8002`    |
| Slim + apm-8           | `nginx-apm-8` -> `php-fpm-apm-8`                     | Current GA Solarwinds APM PHP library                                                                                                                                                                                            | `8003`    |
| Load generator         | `apm-php-bench-locust`                               | Headless Locust workload + custom OTLP metric                                                                                                                                                                                    | n/a       |
| Collector (Locust)     | `otel-collector-locust`                              | Forwards telemetry from Locust to backend                                                                                                                                                                                        | n/a       |
| Collector (alpha)      | `otel-collector-apm-php-9-alpha`                     | Forwards telemetry from APM PHP alpha to backend                                                                                                                                                                                 | n/a       |
| Collector (otel)       | `otel-collector-otel`                                | Forwards telemetry from OpenTelemetry PHP app to backend                                                                                                                                                                         | n/a       |

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Valid collector/token values for your backend

## Configuration

A template exists at `.env.dev`:

```dotenv
OTEL_COLLECTOR=<otel-collector>
OTEL_TOKEN=<token>
SW_APM_COLLECTOR=<apm-collector>
SW_APM_TOKEN=<token>
```

Use either of these options:

1. Run Compose directly with the template file
2. Copy `.env.dev` to `.env` and edit values

```zsh
cp .env.dev .env
```

## Quick start

```zsh
docker compose --env-file .env.dev up --build
```

If you use `.env`, you can omit `--env-file`:

```zsh
docker compose up --build
```

Stop and clean up:

```zsh
docker compose down
```

## Sanity checks

After startup, verify health endpoints:

```zsh
curl -fsS http://localhost:8000/healthcheck
curl -fsS http://localhost:8001/healthcheck
curl -fsS http://localhost:8002/healthcheck
curl -fsS http://localhost:8003/healthcheck
```

Expected response:

```text
Yay healthy
```

## Benchmark behavior

Locust starts in headless mode with:

- 8 users
- spawn rate 5
- host `http://0.0.0.0:8000` (individual tasks call service DNS names directly)

Tasks in `locust-app/locustfile.py` call:

- `http://nginx-uninstrumented/complex` as `uninstrumented`
- `http://nginx-apm-php-9-alpha/complex` as `9.0.0-alpha`
- `http://nginx-otel/complex` as `otel`
- `http://nginx-apm-8/complex` as `8.13.0`

Locust also publishes a custom histogram metric:

- metric name: `apm.php.benchmark.response.time`
- attribute key: `benchmark.app.kind`

## Slim app routes

Available routes in `slim-app/index.php`:

- `/healthcheck` - liveness check
- `/request` - outbound call to `example.com`
- `/metrics` - app counters + histogram, includes `sleep(1)` for stable response-time profile
- `/logs` - emits logs via Monolog OTel handler
- `/sdk` - manual SDK span + outbound call
- `/complex` - benchmark-heavy path (creates many manual spans and records metrics)

## Project structure

```text
.
├── docker-compose.yaml
├── otel-collector-config.yaml
├── swotel-collector-config.yaml
├── locust-app/
│   ├── Dockerfile
│   ├── locustfile.py
│   └── requirements.txt
└── slim-app/
    ├── Dockerfile-uninstrumented
    ├── Dockerfile-apm-php-9-alpha
    ├── Dockerfile-otel
    ├── Dockerfile-apm-8
    ├── composer-uninstrumented.json
    ├── composer-apm-php-9-alpha.json
    ├── composer-otel.json
    ├── index.php
    └── nginx-*.conf
```

## Troubleshooting

- Containers exit early: inspect logs with `docker compose logs --tail=200 <service>`.
- Health check fails: ensure `php-fpm-*` services built successfully and Nginx depends_on conditions are met.
- No telemetry in backend: verify `.env(.dev)` token/collector values and collector service connectivity.

## License

Licensed under Apache 2.0. See [LICENSE](./LICENSE).
