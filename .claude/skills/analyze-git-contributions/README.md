# Analyze Git Contributions Skill

Intelligently analyzes git contributions and groups them by functional components using AI.

## Quick Start

```bash
# From within a git repository
/analyze-git-contributions

# From outside, specify path
/analyze-git-contributions /path/to/repo
```

## What It Does

1. **Collects** all commits for a specified author from a git repository
2. **Analyzes** commits using AI to identify functional components and patterns
3. **Groups** commits semantically by functionality (not just directory structure)
4. **Generates** a comprehensive markdown report with statistics

## Output Example

The skill produces a markdown report with:
- Summary of contribution themes
- Functional component groups (e.g., "Authentication System", "API Endpoints")
- Detailed commit information with file changes
- Statistics (files changed, additions/deletions, most active areas)

## Scripts

### fast-extract-commits.sh (Primary)
Fast batch extraction with caching support.

```bash
./scripts/fast-extract-commits.sh <repo_path> <author_pattern> [options]
# Options: --since=DATE, --until=DATE, --use-cache, --no-cache
# Output: JSONL format (one JSON object per commit)
# Performance: 3-5x faster than individual extraction
```

### batch-extract-commits.sh
Internal script for batch git operations.

```bash
./scripts/batch-extract-commits.sh <repo_path> <author_pattern> [since] [until]
# Used internally by fast-extract-commits.sh
# Extracts all commits in a single git command
```

### cache-manage.sh
Cache management utility.

```bash
./scripts/cache-manage.sh status /path/to/repo   # Show cache info
./scripts/cache-manage.sh clear /path/to/repo    # Clear cache
./scripts/cache-manage.sh info /path/to/repo     # Show metadata
```

### collect-user-commits.sh
Collects commit metadata (legacy, still used for sampling).

```bash
./scripts/collect-user-commits.sh <repo_path> <author_pattern>
# Output: hash|author_name|author_email|date|subject (one per line)
# Exit codes: 0=success, 1=invalid repo, 2=no commits
```

### extract-commit-details.sh
Extracts details for a single commit (legacy).

```bash
./scripts/extract-commit-details.sh <repo_path> <commit_hash>
# Output: commit message and file changes with statistics
# Exit codes: 0=success, 1=invalid commit
```

## Features

- **Auto-detection**: Automatically detects repository and author from git config
- **Semantic grouping**: AI analyzes commit patterns to group by functionality
- **Comprehensive**: Includes commit messages, file changes, and statistics
- **Reusable**: Works across different repositories and authors
- **Error handling**: Gracefully handles invalid repos, no commits, large repos
- **Fast performance**: Batch extraction with caching for 3-5x speed improvement

## Performance

The skill uses optimized batch processing for fast analysis:

| Commits | First Run | Cached Run |
|---------|-----------|------------|
| 50      | ~5s       | ~1s        |
| 100     | ~10s      | ~2s        |
| 200     | ~15s      | ~2s        |
| 500     | ~30s      | ~3s        |
| 1000    | ~60s      | ~5s        |

### Caching

Commit details are cached in `.git-analysis-cache/` within the repository. The cache is automatically invalidated when new commits are added.

**Managing the cache:**
```bash
# Check cache status
./scripts/cache-manage.sh status /path/to/repo

# Clear cache
./scripts/cache-manage.sh clear /path/to/repo

# View cache metadata
./scripts/cache-manage.sh info /path/to/repo
```

**Note:** Add `.git-analysis-cache/` to your `.gitignore` to avoid committing cache files.

## Testing

Scripts tested successfully with:
- Valid repository: ✅ (1,379 commits analyzed)
- Invalid repository: ✅ (proper error: exit code 1)
- No commits for author: ✅ (proper error: exit code 2)
- Invalid commit hash: ✅ (proper error: exit code 1)
- Multi-file commits: ✅
- Binary files: ✅

## Installation

Already installed at: `~/.claude/skills/analyze-git-contributions/`

The skill will be auto-discovered by Claude Code and available via `/analyze-git-contributions`.
