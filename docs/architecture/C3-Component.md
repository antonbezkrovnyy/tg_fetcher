# C3 — Component Diagram: Core flow and responsibilities

Focus: how the application components collaborate to execute a full fetch.

```mermaid
sequenceDiagram
    autonumber
    participant F as FetcherService
    participant C as DI Container
    participant R as FetchRunner
    participant SM as SessionManager
    participant UC1 as FetchChatUseCase
    participant UC2 as FetchDateRangeUseCase
    participant G as TelegramGateway
    participant M as MessageExtractor
    participant P as MessagePreprocessor
    participant D as DateRangeProcessor
    participant Repo as MessageRepository
    participant Fin as FinalizationOrchestrator
    participant Prog as ProgressService
    participant PT as ProgressTracker

    F->>C: provide_strategy(date?)
    C-->>F: Strategy
    F->>C: provide_fetch_runner()
    C-->>F: FetchRunner
    F->>R: run_all(strategy, correlation_id)
    R->>SM: __aenter__ (open session)
    loop for each chat
        R->>UC1: execute(client, chat, strategy, cid, concurrency)
        UC1->>G: get_entity(client, chat)
        UC1->>UC1: source_info = map(entity)
        UC1->>Strategy: get_date_ranges(client, chat)
        par bounded by semaphore
            UC1->>UC2: execute(..., date_from,to, source_info)
            UC2->>D: iterate messages
            loop messages
                D-->>UC2: TelethonMessage
                UC2->>M: extract(client, entity, msg, source)
                M->>G: extract_reactions/comments/forward
                M-->>UC2: Message
                UC2->>P: preprocess(Message)
                P-->>UC2: Message (enriched)
                UC2->>Repo: save(message)
                UC2->>Prog: mark progress / metrics
            end
            UC2->>Fin: finalize(source/date)
            UC2->>PT: persist progress
        and
        end
    end
    R->>SM: __aexit__ (close session)
```

Highlights:
- FetcherService orchestrates only at the top; it does not know message/extraction details.
- FetchRunner owns chat iteration and error handling.
- Use-cases separate chat-level orchestration from date-range processing.
- Extractor uses the gateway, preprocessor enriches, repository persists, services signal progress and finalize results.
