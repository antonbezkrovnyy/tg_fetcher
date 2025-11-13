# C2 — Container Diagram: Fetcher app and external containers

Shows the high-level containers (runtime processes/services) and how they communicate.

```mermaid
flowchart LR
  subgraph APP[python-tg Application]
    FSVC["FetcherService\nFacade"]
    DI["DI Container\n(src/di/container.py)"]
    RUN["FetchRunner\nCoordinator"]
    UC1["Use-Case: FetchChat"]
    UC2["Use-Case: FetchDateRange"]
    GATE["TelegramGateway\n(Adapter)"]
    SESS["SessionManager\n(Telethon auth/session)"]
    REPO["MessageRepository\n(filesystem)"]
    FIN["FinalizationOrchestrator\n(Result finalizer)"]
    PROG["ProgressService\n(events+metrics)"]
    PTRK["ProgressTracker\n(persisted progress)"]
    PREP["MessagePreprocessor\n(NLP/links/merge)"]
    MAP["SourceInfoMapper"]
    DRP["DateRangeProcessor"]
    STRAT["StrategyFactory"]
    MEXT["MessageExtractor\n(gateway-backed)"]
  end

  TG["Telegram API\n(Telethon)"]
  REDIS["Redis\n(events)"]
  PROM["Prometheus\n(metrics)"]
  FS["Filesystem\n(data/)"]

  FSVC -->|uses| RUN
  FSVC -->|asks for| DI
  RUN -->|per chat| UC1
  UC1 -->|per date range| UC2
  UC1 --> MAP
  UC1 --> GATE
  UC2 --> DRP
  UC2 --> MEXT
  UC2 --> PREP
  UC2 --> REPO
  UC2 --> FIN
  PROG -.-> UC2
  PROG -.-> DRP
  PTRK -.-> UC2

  DI --> SESS
  DI --> REPO
  DI --> PROG
  DI --> PTRK
  DI --> PREP
  DI --> MAP
  DI --> DRP
  DI --> GATE
  DI --> STRAT
  DI --> MEXT

  SESS --> TG
  PROG --> REDIS
  PROG --> PROM
  REPO --> FS
```

Notes:
- FetcherService remains a thin entry point: it delegates to FetchRunner and pulls dependencies from the DI container.
- Use-cases encapsulate domain workflows; adapters (Gateway, Repository) isolate IO.
- Observability is centralized via ProgressService (Redis events + Prometheus metrics).
