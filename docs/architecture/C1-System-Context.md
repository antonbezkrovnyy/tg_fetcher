# C1 — System Context: Telegram Fetcher

This diagram shows the fetcher in its environment and who/what it interacts with.

```mermaid
flowchart LR
  %% People
  U["Operator / DevOps"]

  %% System under design
  S["Telegram Fetcher\n(python-tg)"]

  %% External systems
  TG["Telegram API\n(Telethon)"]
  FS["Filesystem\n(data/ JSON outputs)"]
  REDIS["Redis\n(Events bus)"]
  PROM["Prometheus / Grafana\n(Metrics)"]
  ANA["tg_analyzer\n(offline processing)"]
  WEB["tg_web\n(frontend + API)"]

  U -->|configure/run| S
  S -->|fetch messages| TG
  S -->|write outputs| FS
  S -->|publish progress/events| REDIS
  S -->|export metrics| PROM
  ANA -->|read inputs| FS
  WEB -->|serve data/visualize| FS
```

Key points:
- Operator triggers fetches locally or in containerized environments.
- Telethon is the client SDK used against the Telegram API.
- Outputs (messages with enrichments) are persisted as JSON files under `data/`.
- Progress/events are optionally sent to Redis; metrics to Prometheus.
- Downstream systems (tg_analyzer, tg_web) consume produced data.