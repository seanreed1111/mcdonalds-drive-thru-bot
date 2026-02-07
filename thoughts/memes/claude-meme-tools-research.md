# Claude Meme Tools & Skills Research

Searched: 2026-02-07

## MCP Servers (Meme Generation)

### 1. haltakov/meme-mcp (Most Popular)
- **Repo**: https://github.com/haltakov/meme-mcp
- **NPM**: https://www.npmjs.com/package/meme-mcp
- **Author**: Vladimir Haltakov
- **What it does**: Simple MCP server for generating memes using the ImgFlip API. Implements a `generateMeme` tool that accepts template ID, text0, and text1 parameters.
- **Setup**: Requires free ImgFlip account credentials (`IMGFLIP_USERNAME`, `IMGFLIP_PASSWORD`). Configured via Claude Desktop or Claude Code MCP settings using the `meme-mcp` NPM package.
- **Deep dive article**: https://skywork.ai/skypage/en/vladimir-haltakov-imgflip-meme-server/1980168474760695808
- **Listed on**: [LobeHub](https://lobehub.com/mcp/haltakov-meme-mcp), [Glama](https://glama.ai/mcp/servers/@haltakov/meme-mcp), [PulseMCP](https://www.pulsemcp.com/servers/haltakov-meme-generator-imgflip), [Playbooks](https://playbooks.com/mcp/haltakov-meme-generator-imgflip)

### 2. redblock-ai/imgflip-mcp (More Feature-Rich)
- **Repo**: https://github.com/redblock-ai/imgflip-mcp
- **What it does**: "Meme Creation Protocol" server for Claude and other AI assistants. Uses ImgFlip API with more tools than haltakov's version.
- **Tools provided**: `imgflip_search_memes`, `imgflip_get_template_info`, `imgflip_create_meme`, `imgflip_generate_search_terms`, `imgflip_create_from_concept`
- **Released**: April 2025

### 3. lidorshimoni/meme-mcp (Fork)
- **Repo**: https://github.com/lidorshimoni/meme-mcp
- **What it does**: Fork of haltakov/meme-mcp with same ImgFlip API integration.

### 4. Owen's Custom Meme MCP (Blog Post / Tutorial)
- **Blog**: https://www.owenmc.dev/posts/claude-memes
- **What it does**: Custom implementation using a vector database populated with embeddings of ImgFlip meme templates + a backend server for semantic search against the vector DB. More sophisticated approach that matches meme templates to prompts via semantic similarity.
- **Architecture**: Vector DB + backend server + MCP protocol

### 5. Paras Madan's Tutorial
- **Article**: https://medium.com/@parasmadan.in/building-meme-generator-mcp-server-from-scratch-fb87caab4b2c
- **What it does**: Step-by-step tutorial on building a meme generator MCP server from scratch.

---

## Claude Code Skills (No Meme-Specific Skills Found)

No dedicated "meme" Claude Code skills were found in any of the major skill collections. The meme generation use case is primarily served by MCP servers rather than skills.

### Skill Collections Searched (for reference)
- https://github.com/anthropics/skills (Official Anthropic skills)
- https://github.com/ComposioHQ/awesome-claude-skills
- https://github.com/travisvn/awesome-claude-skills
- https://github.com/BehiSecc/awesome-claude-skills
- https://github.com/hesreallyhim/awesome-claude-code
- https://github.com/VoltAgent/awesome-agent-skills (200+ skills, none meme-specific)
- https://github.com/daymade/claude-code-skills
- https://github.com/abubakarsiddik31/claude-skills-collection
- https://github.com/mkdev-me/claude-skills

### Skill Factory (for building your own)
- https://github.com/alirezarezvani/claude-code-skill-factory

---

## Summary

| Tool | Type | Approach | Complexity |
|------|------|----------|------------|
| haltakov/meme-mcp | MCP Server | ImgFlip API, simple | Low |
| redblock-ai/imgflip-mcp | MCP Server | ImgFlip API, multi-tool | Medium |
| Owen's custom MCP | MCP Server | Vector DB + ImgFlip | High |
| Paras Madan tutorial | Tutorial | Build from scratch | Medium |

**Key takeaway**: Meme generation for Claude is done via MCP servers (not skills). All implementations use ImgFlip API as the backend. The `redblock-ai/imgflip-mcp` has the richest feature set with search, template info, and concept-to-meme generation.
