# Changelog

## [0.5.0](https://github.com/seanreed1111/mcdonalds-drive-thru-bot/pull/8) - 2026-02-13

### Added
- Add Langfuse evaluation blog post drafts (v1 and v2) documenting the full eval pipeline (#8)
- Add Substack-friendly version of the eval blog with code/table screenshot images (#8)
- Add `convert_to_substack.py` script for converting markdown to Substack format (code/tables to PNG) (#8)
- Add `/convert_to_substack` Claude command for one-step blog conversion (#8)
- Add meme assets and generation script for the eval blog (#8)
- Add Langfuse Python SDK documentation outline (#8)
- Add LangGraph testing implementation plan (#8)
- Add evaluation blog planning notes and prompt optimization research (#8)
- Add Imgflip Meme API documentation to CLAUDE.md (#8)

### Changed
- Reorganize tutorials into `docs/tutorials/` directory (#8)
- Rename and consolidate planning docs for Langfuse evaluation and state diagrams (#8)

## [0.4.0](https://github.com/seanreed1111/mcdonalds-drive-thru-bot/pull/7) - 2026-02-11

### Added
- Add `RetryPolicy` to orchestrator LLM node with exponential backoff (5 attempts, 1s–30s, jitter) (#7)
- Add `docs/retries-rate-limits.md` documenting retry strategy for the orchestrator (#7)

### Changed
- Reorganize docs: flatten `planning-docs/thoughts/target-implementation/` into `docs/` and `planning-docs/thoughts/` (#7)
- Remove completed Langfuse evaluation plan (#7)

## [0.3.0](https://github.com/seanreed1111/mcdonalds-drive-thru-bot/pull/6) - 2026-02-11

### Added
- Add Langfuse evaluation dataset seeding script with 25 single-turn test cases (#6)
- Add experiment runner with deterministic evaluators for order correctness, tool call accuracy, and hallucination detection (#6)
- Add `eval-seed` and `eval` Makefile targets for evaluation workflow (#6)
- Add evaluations tutorial documentation (#6)

### Changed
- Reorganize blog docs into topic-based subdirectories (#6)
- Update CLAUDE.md with markdown file date conventions (#6)

## [0.2.0](https://github.com/seanreed1111/mcdonalds-drive-thru-bot/compare/ebd21e9...ce85e76) - 2026-02-10

### Added
- Add `reasoning` key to DriveThruState with `operator.add` reducer for LLM decision tracing (#3)
- Add architecture documentation (#5)

### Changed
- Implement phase 1 drive-thru orchestrator with LangGraph, Mistral, and Langfuse tracing (#2)
- Update Langfuse v3 CallbackHandler integration and prompt management (#4)

## [0.1.0](https://github.com/seanreed1111/mcdonalds-drive-thru-bot/compare/4659e60...ebd21e9) - 2026-02-06

### Added
- Add LangGraph orchestrator with Mistral LLM and tool-calling workflow (#5)
- Add Langfuse prompt management and tracing integration (#4)
- Add Pydantic v2 data models for Menu, Item, Modifier, Order with custom equality and arithmetic (#3)
- Add Menu model with JSON loading and Location support (#2)
- Add ty type checker and fix type errors (#6)
- Add two-bot interview graph with Langfuse prompt management (#7)
- Add uv workspace structure with orchestrator package (#1)
