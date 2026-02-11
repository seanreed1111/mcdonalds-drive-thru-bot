# ADR-010: `pydantic-settings` with `.env` and Singleton Caching

**Status:** Accepted

[Back to ADR Index](./adr.md)

---

## Context

The application has configuration values that vary by environment: API keys, model selection, file paths, log levels, and Langfuse credentials. These need to be loaded from environment variables and/or a `.env` file, validated at startup, and accessible throughout the codebase.

**Options considered:**
1. **`os.environ` directly** — Read env vars where needed, no validation
2. **`python-dotenv` + dataclass** — Load `.env`, parse into a dataclass
3. **`pydantic-settings`** — Type-validated settings from env vars with `.env` support built in

## Decision

Use `pydantic-settings` (`BaseSettings`) with automatic `.env` file loading and a `@lru_cache` singleton accessor.

```python
# config.py

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required (no default — will error if missing)
    mistral_api_key: str

    # Optional with defaults
    mistral_model: str = "mistral-small-latest"
    mistral_temperature: float = 0.0
    menu_json_path: str = str(PROJECT_ROOT / "menus/.../breakfast-v2.json")
    log_level: str = "DEBUG"

    # Optional — empty string means disabled
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

### Key design choices

**`extra="ignore"`** — The `.env` file contains variables used by multiple tools (Langfuse SDK reads its own env vars, LangGraph Studio reads `LANGCHAIN_*` vars, etc.). Without `extra="ignore"`, pydantic-settings would raise a `ValidationError` on any env var not defined in the `Settings` class.

**`PROJECT_ROOT` from file path** — Calculated as `Path(__file__).resolve().parents[3]` (3 levels up: `config.py` -> `orchestrator/` -> `orchestrator/` -> `src/` -> root). This ensures the `.env` path and default `menu_json_path` resolve correctly regardless of the working directory.

**Optional Langfuse via empty strings** — Rather than using `Optional[str]` with `None`, Langfuse keys default to empty strings. The consuming code checks `if not settings.langfuse_public_key` which is truthy for both `""` and `None`. This simplifies the `.env` file — users can leave lines blank rather than commenting them out.

**Why `os.environ` was rejected:**
- No type validation — `os.environ["MISTRAL_TEMPERATURE"]` returns a string, not a float
- No clear schema of what config exists
- No default values or `.env` file loading

**Why `python-dotenv` + dataclass was rejected:**
- Manual `.env` loading and type coercion
- `pydantic-settings` provides this out of the box with validation

## Consequences

**Benefits:**
- Type validation at startup: a misconfigured `MISTRAL_TEMPERATURE=not-a-number` fails immediately with a clear error
- Single source of truth for all configuration in one class
- Singleton via `@lru_cache` — settings are parsed once, reused everywhere
- `.env` file is loaded automatically — no explicit `load_dotenv()` calls
- `extra="ignore"` allows the `.env` to serve multiple tools without conflict

**Tradeoffs:**
- `@lru_cache` means settings cannot be changed at runtime (acceptable for a CLI app)
- `PROJECT_ROOT` via `parents[3]` is fragile if the file moves to a different depth
- `pydantic-settings` is an extra dependency beyond `pydantic` (though lightweight)

---

[Back to ADR Index](./adr.md)
