# Changelog

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
