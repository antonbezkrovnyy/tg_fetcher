# TZ: Tests for Finalization and Postprocess

## Business Goal
Increase coverage for finalization stage: orchestration of artifact saving and completion event publishing; ensure postprocess helpers work and are resilient to repository and filesystem states.

## Functional Requirements
- FinalizationOrchestrator.finalize:
  - Builds threads structure (roots/parent_to_children/depth) from MessageCollection.
  - Publishes stage "postprocess" and then completion event with correct parameters.
  - Calls ResultFinalizer.save_artifacts with summary payload (schema/preproc versions, timestamps, counts, tokens sum, checksum).
- ResultFinalizer.save_artifacts:
  - Delegates to repository methods and returns mapping with file paths.
- ResultEnricher.enrich_single_chat_result:
  - When result has file_path and it exists: set timestamps, token sum, checksum via checksum_fn.
  - Always sets artifact paths via repository get_*_path; paths are str (posix) and JSON-friendly.
  - Swallows exceptions and does not raise.

## Technical Decisions
- Provide lightweight stubs:
  - Repository stub implementing required methods.
  - ProgressService stub recording calls.
  - checksum_fn stub with deterministic return.
- Use tmp_path to simulate existing files for checksum path.

## Test Cases
1. Orchestrator happy path: verify stage publish, save_artifacts payload (including versions), threads structure, and completion call.
2. ResultFinalizer: verify repository methods called and mapping keys returned.
3. ResultEnricher with existing file: timestamps, tokens, checksum set; artifact paths set.
4. ResultEnricher without existing file: only artifact paths set; checksum/timestamps absent.
5. ResultEnricher repository raises: method does not raise (optional).

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
