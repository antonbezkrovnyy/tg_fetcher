# TZ: Tests for SourceInfoMapper

## Business Goal
Increase unit test coverage by validating mapping logic from Telethon entities to SourceInfo and sender display name resolution without relying on real Telethon instances.

## Functional Requirements
- Cover `extract_source_info` for Channel (with/without username, megagroup true/false), Chat (megagroup true/false), and User (full name, username-only, and no names).
- Cover `get_sender_name` branches for: None, User (name parts, username-only, fallback), Channel/Chat (with/without title), and unknown object.
- Use lightweight stubs via monkeypatch to avoid constructing real Telethon objects.
- Keep assertions strict on fields: id, title, url, and type (must be one of: channel|supergroup|chat|group|unknown).

## Technical Decisions
- Patch `src.services.mappers.source_mapper.Channel/Chat/User` with simple stub classes inside tests to satisfy `isinstance` checks.
- Do not modify production logic except minor lint/docstring if needed.
- Run full test suite; no external services required.

## Test Cases
1. Channel with username (not megagroup):
   - id = @username, url = https://t.me/username, type = channel, title preserved
2. Channel without username (megagroup):
   - id = channel_<id>, url = https://t.me/c/<id>, type = supergroup
3. Chat regular (not megagroup):
   - id = chat_<id>, url = https://t.me/c/<id>, type = chat
4. Chat group (megagroup):
   - type = group
5. User with first+last and username:
   - title = "First Last", id = @username, url = https://t.me/username, type = chat
6. User without names and without username:
   - title = User_<id>, id = user_<id>, url = "" (empty)
7. get_sender_name(None) -> "Unknown"
8. get_sender_name(User only username) -> "@username"
9. get_sender_name(Channel without title) -> "Channel_<id>"
10. get_sender_name(unknown object) -> "Unknown"

## Implementation Plan
1. Create tests/unit/test_source_mapper.py with fixtures and monkeypatching.
2. Run full pytest and ensure all new tests pass.
3. Review coverage delta and identify next high-ROI targets.

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
