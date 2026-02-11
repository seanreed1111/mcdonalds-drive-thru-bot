# ADR-009: Langfuse v3 for Observability and Prompt Management

**Status:** Accepted

[Back to ADR Index](./adr.md)

---

## Context

The system needs observability into LLM interactions: what was sent, what was returned, latency, token usage, and session grouping. It also needs a way to manage and version the system prompt without code deployments.

**Options considered:**
1. **LangSmith** — LangChain's native observability platform
2. **Langfuse v3** — Open-source LLM observability with prompt management
3. **Custom logging only** — Log everything with loguru, no external platform
4. **OpenTelemetry only** — Use OTEL for traces without LLM-specific features

## Decision

Use **Langfuse v3** for both observability (tracing all LLM calls) and prompt management (storing/versioning the system prompt). Langfuse is optional — the system works without it.

### Integration architecture

```mermaid
graph TB
    subgraph "Application"
        Main[main.py]
        Graph[graph.py]
        LLM[Mistral AI]
    end

    subgraph "Langfuse v3"
        Tracing[Trace Collection<br/>───────────<br/>LLM calls, tool calls<br/>latency, tokens]
        Prompts[Prompt Management<br/>───────────<br/>drive-thru/orchestrator<br/>label: production]
        Sessions[Session Grouping<br/>───────────<br/>Group traces by<br/>conversation session]
    end

    Main -->|CallbackHandler| Tracing
    Graph -->|get_prompt()| Prompts
    Main -->|metadata.langfuse_session_id| Sessions
```

### Handler creation (v3 pattern)

```python
# main.py:19-38

def _create_langfuse_handler():
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None                           # Langfuse disabled — no error

    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    Langfuse(                                  # Initialize singleton client
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_base_url,
    )
    return CallbackHandler()                   # No constructor args in v3!
```

### Session tracking via metadata

```python
# main.py:68-72

config["callbacks"] = [langfuse_handler]
config["metadata"] = {"langfuse_session_id": session_id}
```

### Key v3 differences from v2

| Aspect | v2 | v3 |
|--------|----|----|
| **Import** | `from langfuse.callback import CallbackHandler` | `from langfuse.langchain import CallbackHandler` |
| **Credentials** | On handler constructor | On `Langfuse()` singleton client |
| **Session ID** | `CallbackHandler(session_id=...)` | `config["metadata"]["langfuse_session_id"]` |
| **Flush** | `handler.flush()` | `get_client().flush()` |

### Prompt management

The system prompt is fetched from Langfuse with label `"production"` and a hardcoded fallback (see [ADR-005](./005-runtime-prompt-compilation.md)):

```python
prompt = langfuse.get_prompt("drive-thru/orchestrator", label="production")
```

Prompts are seeded via `scripts/seed_langfuse_prompts.py`.

**Why LangSmith was rejected:**
- Langfuse is open-source and self-hostable
- Langfuse includes prompt management (LangSmith requires LangChain Hub separately)
- Better pricing model for development and small-scale usage

**Why custom logging only was rejected:**
- No trace visualization, session grouping, or token usage dashboards
- Loguru handles local debugging well but is not a replacement for an observability platform

**Why OTEL only was rejected:**
- Generic tracing lacks LLM-specific features (token counts, prompt/completion visualization, prompt versioning)
- The project does include OTEL dependencies for future integration, but Langfuse is the primary observability layer

## Consequences

**Benefits:**
- Full trace visibility: every LLM call, tool call, and response is captured with latency and token counts
- Session grouping: all turns in a conversation are grouped under a single session ID
- Prompt versioning: the system prompt can be iterated in Langfuse's UI without code changes
- Graceful degradation: the system works identically without Langfuse configured (empty keys = disabled)
- Flush-on-exit ensures no traces are lost when the CLI process terminates

**Tradeoffs:**
- External dependency on Langfuse cloud (or self-hosted instance)
- Network calls for both tracing and prompt fetching add latency
- v3 API is newer and may have breaking changes in future minor versions
- Dual prompt storage (Langfuse + fallback in code) can diverge silently

---

[Back to ADR Index](./adr.md)
