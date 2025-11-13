# TZ: Move heuristics to preprocessor

## Business Goal
Slim down FetcherService and centralize enrichment (links, tokens, classification, language) for better testability and maintainability.

## Functional Requirements
- Extract and normalize links from message text.
- Estimate token count heuristically.
- Classify message type (question|answer|code|log|spam|service|other).
- Detect language (ru|en|other) via simple heuristic.
- Merge short consecutive messages based on config policy.
- Respect feature flags in FetcherConfig to enable/disable each enrichment.

## Technical Decisions
- Implement enrichment in `src/services/preprocess/message_preprocessor.py` with pure strategy functions in `src/services/preprocess/strategies.py`.
- FetcherService delegates enrichment via `self.preprocessor.enrich()` and merging via `self.preprocessor.maybe_merge_short()`.
- Remove redundant heuristics from FetcherService to reduce responsibilities.

## Implementation Plan
1. Instantiate MessagePreprocessor in FetcherService with config flags and strategy delegates.
2. Call `preprocessor.enrich()` on every Message produced by `_extract_message_data`.
3. Use `preprocessor.maybe_merge_short(prev, curr)` instead of in-service merge logic.
4. Delete redundant helpers from FetcherService.
5. Run lint/type checks and update docs/console.log.

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
