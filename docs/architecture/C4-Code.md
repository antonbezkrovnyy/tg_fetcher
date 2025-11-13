# C4 — Code/Classes: Key contracts and collaborators

A minimal code-level view of protocols and classes and their relationships.

```mermaid
classDiagram
  direction LR

  class FetcherService {
    +__init__(config)
    +run() async
    +fetch_single_chat(chat, date?) async
    -_create_strategy(date?)
  }

  class Container {
    +initialize_runtime()
    +provide_strategy(date?) StrategyProtocol
    +provide_fetch_runner() FetchRunner
    +provide_fetch_chat_use_case()
    +provide_fetch_date_range_use_case()
    +provide_session_manager()
    +provide_progress_service()
  }

  class FetchRunner {
    +run_all(strategy, correlation_id) async
    +run_single(strategy, chat_identifier, correlation_id) async
    -_safe_execute(...)
  }

  class FetchRunnerDeps {
    +config: FetcherConfig
    +session_manager: SessionManager
    +chat_use_case: FetchChatUseCase
  }

  class StrategyProtocol {
    +get_strategy_name() str
    +get_date_ranges(client, chat) AsyncIterator~tuple(date,date)~
  }

  class TelegramGatewayProtocol {
    +extract_reactions(msg) list~Reaction~
    +extract_comments(client, entity, msg, source, *, limit) list~Message~
    +extract_forward_info(msg) ForwardInfo?
  }

  class TelegramGateway
  TelegramGateway ..|> TelegramGatewayProtocol

  class FetchChatUseCase {
    +execute(client, chat, strategy, correlation_id, concurrency?) async int
  }

  class FetchChatDeps {
    +config: FetcherConfig
    +telegram_gateway: TelegramGatewayProtocol
    +source_mapper: SourceInfoMapper
    +date_range_use_case: FetchDateRangeUseCase
  }

  class FetchDateRangeUseCase {
    +execute(client, entity, source, strategy, date_from, date_to, correlation_id) async int
  }

  class FetchDateRangeDeps {
    +config: FetcherConfig
    +repository: MessageRepository
    +preprocessor: MessagePreprocessor
    +source_mapper: SourceInfoMapper
    +date_range_processor: DateRangeProcessor
    +progress_service: ProgressService
    +progress_tracker: ProgressTracker
    +finalization_orchestrator: FinalizationOrchestrator
    +extract_message_data: (client, entity, msg, source) -> Message
  }

  class MessageExtractor {
    +extract(client, entity, msg, source) async Message
  }

  class DateRangeProcessor {
    +iterate(...)
    +set_strategy_name(name)
  }

  class ProgressService
  class ProgressTracker
  class MessagePreprocessor
  class MessageRepository
  class FinalizationOrchestrator

  FetcherService --> Container
  FetcherService --> FetchRunner
  Container o--> FetchRunner
  Container o--> FetchChatUseCase
  Container o--> FetchDateRangeUseCase
  Container o--> MessageExtractor
  FetchRunner --> FetchChatUseCase
  FetchChatUseCase --> FetchDateRangeUseCase
  FetchChatUseCase --> TelegramGatewayProtocol
  FetchDateRangeUseCase --> DateRangeProcessor
  FetchDateRangeUseCase --> MessageExtractor
  FetchDateRangeUseCase --> MessagePreprocessor
  FetchDateRangeUseCase --> MessageRepository
  FetchDateRangeUseCase --> ProgressService
  FetchDateRangeUseCase --> ProgressTracker
  FetchDateRangeUseCase --> FinalizationOrchestrator
```

Notes:
- Structural typing (protocols) keeps use-cases independent from concrete adapters.
- DI container centralizes composition; side-effects are in `initialize_runtime()`.
- FetcherService is a thin facade; orchestration lives in Runner + Use-cases.
