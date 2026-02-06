# Changelog

## [Unreleased]

### Fixed
- Fix Langfuse tracing not appearing in dashboard by migrating to SDK v3 singleton pattern (#5)

### Added
- Add ty type checker as dev dependency with `make typecheck` target (#6)
- Add `prune_branches` Claude command for cleaning up local git branches (#6)
- Add secret scanning with gitleaks pre-commit hook (#6)

### Fixed
- Fix `create_graph()` return type annotation (`StateGraph` → `CompiledStateGraph`) (#6)
- Fix Langfuse tracing not appearing in dashboard by migrating to SDK v3 singleton pattern (#5)

### Added
- Add v0-stage-1 simple chatbot with LangGraph, Mistral AI, and Langfuse observability (#5)
- Add streaming CLI chat interface with session/user ID tracing (#5)
- Add LangGraph Platform deployment config (`langgraph.json`) (#5)
- Add Makefile with `chat`, `dev`, and `test-smoke` targets (#5)
- Add pydantic-settings config module for environment variable management (#5)
- Add custom equality and hashability to `Modifier`, `Location`, `Item`, and `Menu` models (#3)
- Add quantity-based comparison operators (`<`, `<=`, `>`, `>=`) to `Item` for same-configuration items (#3)
- Add `__add__` method to `Item` to combine quantities of same-configuration items (#3)
- Add `Location` model for restaurant location data (id, name, address, city, state, zip, country) (#2)
- Add `Menu.from_json_file()` class method to load menu from JSON file path (#2)
- Add `Menu.from_dict()` class method to load menu from dictionary (#2)
- Add `REGULAR` size option to `Size` enum (#2)

### Changed
- Configure `pyproject.toml` for src-layout with setuptools build system (#5)
- Update `Menu` model with flattened metadata fields (menu_id, menu_name, menu_version, location) (#2)
- Reorganize menu data structure to `menus/mcdonalds/breakfast-menu/` (#2)
