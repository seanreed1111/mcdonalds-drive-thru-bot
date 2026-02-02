# Changelog Style Guide

This style guide is based on [Common Changelog](https://common-changelog.org/) with additional writing style recommendations from the [WARP changelog guidelines](https://broadinstitute.github.io/warp/docs/contribution/contribute_to_warp/changelog_style).

## Core Principles

1. **Changelogs are for humans** - Write for users, not machines
2. **Communicate the impact of changes** - Focus on what users need to know
3. **Sort content by importance** - Most important changes first
4. **Skip content that isn't important** - Omit noise and trivia
5. **Link each change to further information** - Provide references for context

## File Structure

**Filename:** `CHANGELOG.md`

**File Header:** Begin with `# Changelog`

**Release Organization:** Order releases latest-first, following Semantic Versioning rules.

## Release Format

### Header Format

```markdown
## VERSION - DATE
```

**VERSION:**
- Must be valid semantic version (e.g., `1.2.3`)
- NO "v" prefix
- Should link to a GitHub release or tag
- Example: `## [1.2.3](https://github.com/owner/repo/releases/tag/1.2.3) - 2026-01-22`

**DATE:**
- ISO 8601 format: `YYYY-MM-DD`
- Use the commit/release date, not regional formats

### Release Content Structure

Each release contains:
1. Optional **notice** (single sentence about special status)
2. One or more **change groups** organized by category

## Change Categories

Use exactly four categories, listed in this order:

1. **Changed** - Modifications to existing functionality
2. **Added** - New functionality
3. **Removed** - Removed functionality
4. **Fixed** - Bug fixes

**DO NOT use:** "Deprecated," "Security," or other categories. Map security fixes to "Fixed" and deprecation notices to "Changed" or a release notice.

### Category Format

```markdown
### Changed
- Change description with reference (#123)
```

### Breaking Changes

Breaking changes MUST:
- Be prefixed with `**Breaking:**`
- Appear first within their category
- Be listed in the most relevant category (Changed, Added, Removed, or Fixed)

Example:
```markdown
### Changed
- **Breaking:** Rename `process()` to `execute()` for clarity (#456)
- Update configuration format to support nested values (#457)
```

## Change Entry Format

Each change entry follows this structure:

```
- [Description] ([references]) ([authors])
```

### Description (Required)

Write descriptions in **imperative mood** (command form):
- ✅ "Add voice ordering feature"
- ✅ "Fix memory leak in agent session"
- ✅ "Remove deprecated `legacy_mode` parameter"
- ❌ "Added voice ordering"
- ❌ "Memory leak was fixed"
- ❌ "We removed the legacy mode"

**Writing Style:**
- **Active voice** - "Fix broken link" not "Broken link was fixed"
- **Complete sentences** - Capitalize first word
- **No end periods** - Bullets don't need terminal punctuation
- **No pronouns** - Omit "I," "we," "they," "you"
- **One change per bullet** - Multiple sentences explaining one change are acceptable

**Good Examples:**
```markdown
- Add LLM handoff support for multi-stage conversations (#234)
- Fix race condition in session cleanup that caused occasional crashes (#235)
- Update Pydantic models to v2 for better validation. This improves runtime type checking and reduces serialization overhead (#236)
```

**Bad Examples:**
```markdown
- We added support for handoffs.
- The race condition was fixed.
- Updated models. (#236)
```

### References (Required)

Provide at least one reference in parentheses after the description:

**Commits:**
```markdown
- Add menu validation ([`a3f8d12`](https://github.com/owner/repo/commit/a3f8d12))
```

**Pull Requests/Issues:**
```markdown
- Fix agent timeout (#142)
- Resolve upstream bug (livekit/agents#89)
```

**External Tickets:**
```markdown
- Update billing integration (JIRA-1234)
```

**Multiple References:**
Use commas for same type, separate parentheses for different types:
```markdown
- Refactor session handler (#45, #47) ([`b2c9e41`](url))
```

### Authors (Optional)

Include contributor names after references:

```markdown
- Add dark mode support (#156) (Alice, Bob)
- Fix typo in documentation ([`8f3a2b1`](url)) (Charlie)
```

## Notices

Use a single-sentence notice before change groups to clarify special status:

```markdown
## [2.0.0](url) - 2026-01-22

_If upgrading from 1.x: see [`UPGRADING.md`](UPGRADING.md) for migration steps._

### Changed
- **Breaking:** Replace REST API with GraphQL endpoint (#301)
```

**Use notices for:**
- Yanked releases
- Prerelease status
- Required migration/upgrade steps
- Significant compatibility notes

## What to Include

**DO include:**
- New features and capabilities
- Breaking changes (always!)
- Bug fixes that affect users
- Significant refactorings
- Performance improvements
- API changes
- Configuration changes
- Dependency updates (major versions)
- Documentation improvements (substantial)
- Runtime environment changes

**DO NOT include:**
- Dotfile changes (.gitignore, .editorconfig)
- Development-only dependency changes
- Minor code style tweaks
- Whitespace/formatting fixes
- Commits that negate each other in the same release
- Internal refactorings with no user impact
- Minor documentation typos

## Writing Best Practices

### Remove Noise

Filter out changes that don't impact users. A good test: "Would a user care about this?"

### Rephrase Consistently

Harmonize terminology across different contributors while staying faithful to the original intent:

**Before:**
- Bump openai sdk to 1.2.3 (#101)
- Update the openai package (#102)

**After:**
- Update OpenAI SDK from 1.2.0 to 1.2.3 (#101, #102)

### Merge Related Changes

Combine multiple commits that address the same feature or fix:

**Before:**
- Add user model (#201)
- Add user validation (#202)
- Add user tests (#203)

**After:**
- Add user management with validation and tests (#201, #202, #203)

### Separate Messages from Descriptions

Keep changelog entries concise (one line when possible). Detailed explanations belong in:
- Commit messages
- Pull request descriptions
- Linked documentation

**Good:**
```markdown
- Add support for custom STT models (#145)
```

**Too verbose:**
```markdown
- Add support for custom STT models. This was a highly requested feature that allows users to bring their own speech-to-text models. We've implemented it using a plugin architecture that makes it easy to integrate any model that follows our STT interface. See the documentation for more details on how to use this feature. (#145)
```

## Antipatterns to Avoid

❌ **Verbatim commit messages** - Don't copy raw commit messages without editing

❌ **Raw PR titles** - Rephrase for clarity and consistency

❌ **Conventional Commits without refinement** - Machine-generated changelogs need human editing

❌ **Regional date formats** - Always use ISO 8601 (YYYY-MM-DD)

❌ **Unclear references** - "See #123" without context

❌ **Passive voice** - "Was fixed" instead of "Fix"

❌ **Personal pronouns** - "We added" instead of "Add"

## Complete Example

```markdown
# Changelog

## [2.1.0](https://github.com/owner/repo/releases/tag/2.1.0) - 2026-01-22

### Added
- Add voice ordering workflow with menu validation (#234) (Alice)
- Add support for custom wake words (#235)

### Changed
- Update LiveKit Agents SDK to 0.9.0 for improved stability (#236)
- Improve turn detection accuracy in noisy environments (#237) (Bob)

### Fixed
- Fix session cleanup race condition causing occasional crashes (#238)
- Fix menu item modifier validation (#239, #240)

## [2.0.0](https://github.com/owner/repo/releases/tag/2.0.0) - 2026-01-15

_If upgrading from 1.x: see [`UPGRADING.md`](UPGRADING.md) for migration steps._

### Changed
- **Breaking:** Replace configuration format with Pydantic models (#220)
- **Breaking:** Rename `process()` method to `execute()` for consistency (#221)
- Update menu system to use structured Pydantic models (#222)

### Added
- Add comprehensive test suite with 95% coverage (#223)
- Add BDD scenarios for voice ordering workflows (#224)

### Removed
- **Breaking:** Remove deprecated `legacy_mode` parameter (#225)
- Remove support for Python 3.8 (#226)

### Fixed
- Fix audio buffer overflow in high-concurrency scenarios (#227)

## [1.5.2](https://github.com/owner/repo/releases/tag/1.5.2) - 2026-01-10

### Fixed
- Fix typo in agent instructions (#215)
- Fix logging configuration for production deployments (#216)
```

## Quick Reference

| Element | Format | Example |
|---------|--------|---------|
| **Release header** | `## [VERSION](url) - YYYY-MM-DD` | `## [1.2.3](url) - 2026-01-22` |
| **Category** | `### CategoryName` | `### Added` |
| **Change entry** | `- Description (refs) (authors)` | `- Add feature (#123) (Alice)` |
| **Breaking change** | `- **Breaking:** Description` | `- **Breaking:** Rename method (#45)` |
| **Notice** | `_Single sentence._` | `_See UPGRADING.md._` |
| **Multiple refs** | `(#1, #2)` | `(#45, #47, #48)` |
| **External ref** | `(owner/repo#123)` | `(livekit/agents#89)` |
| **Commit ref** | `([`hash`](url))` | `([`a3f8d12`](url))` |

---

**Note:** This style guide prioritizes [Common Changelog](https://common-changelog.org/) conventions. When in doubt, follow Common Changelog over other sources.
