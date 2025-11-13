# TZ: Refactoring Plan (FetcherService & Related Components)

## 1. Goals
- Reduce cyclomatic complexity (remove flake8 C901 warnings) in `FetcherService.fetch_single_chat` and `_process_date_range`.
- Improve extensibility for adding new preprocessing steps and fetch modes (delta, streaming) without inflating main service methods.
- Isolate side-effects (events, metrics, file IO) from pure data transformations for better unit testing.
- Establish clear layering boundaries: Orchestration vs. Helpers vs. Pure transformations.

## 2. Current Pain Points
- Large monolithic `_process_date_range` with mixed concerns (skip logic, fetch loop, preprocessing, metrics, events, persistence).
- Harder to test individual behaviors (e.g., merge heuristics) without invoking full fetch cycle.
- Retry / backoff logic interleaved with core business logic.
- Progress gauge update scattered across method instead of a single abstraction.

## 3. Target Architecture
```
FetcherService
  ├── _process_date_range()  # Linear orchestration only
  │     ├── _maybe_skip_existing()
  │     ├── _fetch_messages_loop()
  │     ├── _preprocess_collection()
  │     ├── _persist_artifacts()
  │     └── _publish_final_events()
  ├── _fetch_single_chat()  # Delegates to strategy date ranges
  └── Helpers (private)
        _maybe_skip_existing()
        _publish_skip_and_reset()
        _update_progress_gauge()
        _fetch_messages_loop()
        _preprocess_collection()
          ├── _merge_short_messages()
          ├── _classify_messages()
          └── _detect_language()
        _persist_artifacts()
        _compute_file_checksum()
```

## 4. Incremental Steps
1. Introduce helper skeleton functions with existing code blocks copied verbatim (no logic change). Add docstrings + type hints.
2. Replace inline blocks in `_process_date_range` sequentially: skip logic → fetch loop → preprocessing → persistence → final publish.
3. Centralize gauge updates inside `_update_progress_gauge(chat, date, value, reset=False)`.
4. Move merge/classify/lang code under `_preprocess_collection` and split into pure functions returning updated collection.
5. Extract retry/backoff into a decorator or dedicated wrapper (`retry_fetch(fn, config)`), apply to network-sensitive parts.
6. Add minimal unit tests for pure helpers (merge, classify, language detection, skip logic decision) to validate isolation.
7. Rename or adjust any remaining large inline comments to concise docstrings.
8. Re-run flake8/mypy; ensure C901 cleared. If complexity persists, further split fetch loop.

## 5. Pure vs Side-Effect Boundary
- Pure: merge, classify, language detect, token estimate, link normalization.
- Side-effects: event publish, progress gauge update, file IO, network fetch via Telethon.
- Strategy: keep pure functions in a `src/services/preprocess.py` (optional future move) if growth continues.

## 6. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Hidden coupling between helpers and service state | Pass explicit parameters (no implicit use of self except config/logger). |
| Regression in skip behavior | Preserve existing tests / add checksum match test before refactor completion. |
| Increased call stack complexity | Keep naming short and cohesive; limit helper depth to 1 level. |
| Premature abstraction | Start with minimal extraction; avoid moving to separate modules until stable. |

## 7. Acceptance Criteria
- No flake8 C901 warnings for target methods.
- `_process_date_range` fits within ~80 lines and contains only orchestration (function calls + high-level logging).
- Unit tests (at least 5) cover: merge thresholds, language detection edge case, classification rule, idempotent skip decision, checksum computation.
- Mypy clean; no increase in uncovered branches for critical paths.
- README/TZ updated to reference new helper structure if materially changed.

## 7.1 Pre-Implementation Checklist Alignment
- Libraries/Tools: Pydantic v2 already in use; black/isort/flake8/mypy configured; pytest planned for helper tests.
- Architecture: Repository + Service + Strategy patterns preserved; Single Responsibility improved by helper extraction; Dependency Inversion respected.
- Workflow Rules: This TZ serves as pre-code spec; incremental extraction, no behavior changes first; decisions logged in TZ; batch questions resolved.
- TZ Compliance: No DB changes; Observability unaffected; data schema unchanged; progress tracking unchanged; error handling preserved.
- Project Structure: No new packages beyond docs; helpers remain in `FetcherService` initially; optional move to `services/preprocess.py` later.
- Dependencies: No new runtime deps; tests may add dev-only packages if needed (kept in requirements-dev.txt).
- Observability: Keep structured logging and correlation IDs; metrics/gauges updates centralized but unchanged semantically.
- Code Quality: All new helpers with type hints + Google-style docstrings; specific exceptions; no hardcoded secrets.
- Testing Strategy: Unit tests for helpers (merge/classify/lang/skip decision/checksum); fixtures via conftest.py when added; aim for >80% on new code.
- Git & Docs: console.log continues for terminal commands; conventional commits; README kept minimal; TZ files updated.

## 8. Out of Scope (Future)
- Async parallelization of fetching across chats.
- Streaming partial persistence during fetch loop.
- ML-based message classification.
- Pluggable rate-limit adaptive controller.

## 9. Timeline (Rough)
- Day 1: Helper extraction (skip + fetch loop + preprocess). Basic unit tests scaffold.
- Day 2: Retry/backoff decorator refactor + gauge centralization.
- Day 3: Final cleanup, docs update, complexity verification, acceptance sign-off.

## 10. Status
- [ ] In Progress
- [ ] Implemented
- [ ] Tested

## 11. Notes
Initial extraction will keep all current logging statements unchanged inside helpers to avoid altering observability signals; consolidation/formatting can occur after functional parity confirmed.
