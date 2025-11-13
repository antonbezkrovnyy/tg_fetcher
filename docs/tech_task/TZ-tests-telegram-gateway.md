# TZ: Tests for TelegramGateway

## Business Goal
Improve coverage of Telethon-facing helper logic by testing reactions extraction, forward info parsing, and comment fetching logic without relying on real Telethon.

## Functional Requirements
- extract_reactions:
  - Return [] when reactions attribute is missing or None.
  - When MessageReactions-like object provided, parse results with either `.reaction.emoticon` or `.reaction` as string; use `.count`.
- extract_forward_info:
  - Return None when no forward; otherwise map `from_id.user_id`, `from_name`, and `date` to ForwardInfo.
- extract_comments:
  - Return [] if `source_info.type` != "channel".
  - Return [] when `message.replies` is None or `replies` == 0.
  - For channels with replies present and limit>0, iterate client.iter_messages and build Message entries using `extract_forward_info` and `extract_reactions`.

## Technical Decisions
- Monkeypatch `telegram_gateway.Channel` and `telegram_gateway.MessageReactions` with local stub classes to satisfy `isinstance` checks.
- Provide an async generator stub for `client.iter_messages`.
- Patch gateway instance `extract_reactions` if needed to simplify comment construction in one test.

## Test Cases
1. Reactions: none/missing; reactions with two results (emoticon and str) → produce 2 Reaction entries.
2. Forward info: no forward → None; with forward → fields mapped correctly.
3. Comments: non-channel → []; channel with no replies → []; replies==0 → []; channel happy-path with two comments and limit>0 → returns built Message list.

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
