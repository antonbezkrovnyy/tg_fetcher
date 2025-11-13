# TZ: Tests for message_extractor

## Business Goal
Raise coverage of `src/services/extractors/message_extractor.py` by testing both functional helpers and the DI-based MessageExtractor service without real Telethon.

## Functional Requirements
- extract_reactions: [] when missing/None; parse results with `.reaction.emoticon` and string; swallow errors.
- extract_comments: [] for non-channel/missing replies/replies==0; iterate async comments for channels; swallow errors.
- extract_forward_info: None when missing; otherwise map from_id.user_id, from_name, date.
- MessageExtractor.extract: delegates to gateway to build Message with reactions/comments/forward info and base fields from message.

## Technical Decisions
- Monkeypatch within module: set `Channel` and `telethon.tl.types.MessageReactions` to local stubs to satisfy isinstance.
- Provide ClientStub.iter_messages that returns async generator.
- For service, create a stub implementing TelegramGatewayProtocol methods used by MessageExtractor.

## Test Cases
1. extract_reactions: none/missing; two reactions (emoticon + str) → list of Reaction pairs.
2. extract_forward_info: None; proper mapping.
3. extract_comments: non-channel and edge cases → []; happy path returns 2 comments.
4. MessageExtractor.extract: returns Message assembled from gateway outputs.

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
