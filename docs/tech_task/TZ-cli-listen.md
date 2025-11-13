# TZ: CLI subcommand `listen`

## Business Goal
Provide a simple way to run a long-lived worker that listens to Redis commands queue and triggers fetch jobs. Align with DI container and existing configuration.

## Functional Requirements
- New CLI subcommand: `tg-fetch listen`.
- Optional flags:
  - `--worker-id` (default: SERVICE_NAME)
  - `--queue` (override COMMANDS_QUEUE)
  - `--timeout` (override COMMANDS_BLPOP_TIMEOUT)
- Uses DI container to create `CommandSubscriber` and start `.listen()`.
- Graceful shutdown on Ctrl+C with `disconnect()`.

## Technical Decisions
- Extend `src/main.py` parser and `_load_config` to accept overrides when `command == 'listen'`.
- In `_run_command`, for `listen`:
  - Initialize logging and `Container(config)`
  - `initialize_runtime()`; `subscriber = container.provide_command_subscriber(worker_id=args.worker_id)`
  - `subscriber.connect()`; `await subscriber.listen()`; handle `KeyboardInterrupt` and ensure `disconnect()` in `finally`.

## Implementation Plan
1. Update `src/main.py`: parser, `_load_config`, and `_run_command` branch for 'listen'.
2. Run flake8/mypy/pytest.
3. Update docs/console.log with commands.
4. Add README section with quick usage; reference in CONFIGURATION.md.

## Status
- [x] In Progress
- [x] Implemented
- [x] Tested
