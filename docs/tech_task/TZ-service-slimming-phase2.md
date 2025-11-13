# TZ: Service slimming — phase 2 (facade + mapper)

## Goal
Reduce FetcherService size and improve SOLID/Hexagonal by extracting a progress facade and a source info mapper without changing behavior.

## Scope
- Introduce ProgressService to wrap metrics updates and event publishing (best-effort, DRY).
- Introduce SourceInfoMapper to convert Telethon entities into SourceInfo and map sender display names.
- Wire FetcherService to use these components; remove duplicate helpers.

## Non-goals
- No change to event payload structure, repository contracts, or strategy logic.

## Interfaces
- ProgressService:
  - reset_gauge(chat: str, date: str) -> None
  - set_progress(chat: str, date: str, value: int) -> None
  - publish_stage(chat: str, date: str, stage: str) -> None
  - publish_skipped(chat: str, date: str, reason: str, checksum_expected: str|None, checksum_actual: str|None) -> None
  - publish_complete(chat: str, date: str, message_count: int, file_path: str, duration_seconds: float) -> None
- SourceInfoMapper:
  - extract_source_info(entity: Any, chat_identifier: str) -> SourceInfo
  - get_sender_name(sender: Any) -> str

## Steps
1. Implement ProgressService.
2. Implement SourceInfoMapper.
3. Update FetcherService to use them; remove old helpers.
4. flake8/mypy; log commands.

## Status
- [ ] In Progress
- [ ] Implemented
- [ ] Tested
