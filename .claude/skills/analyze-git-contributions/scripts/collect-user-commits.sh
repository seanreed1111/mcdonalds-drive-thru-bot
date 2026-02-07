#!/bin/bash

# collect-user-commits.sh
# Collects all commits for a specified author with structured output
#
# Usage: ./collect-user-commits.sh <repo_path> <author_pattern> [since_date] [until_date]
# Output format: hash|author_name|author_email|date|subject (one per line)
# Exit codes: 0=success, 1=invalid repo, 2=no commits found
#
# Optional date parameters:
#   since_date: Only commits after this date (format: YYYY-MM-DD or @timestamp)
#   until_date: Only commits before this date (format: YYYY-MM-DD or @timestamp)

set -euo pipefail

# Check arguments
if [ $# -lt 2 ] || [ $# -gt 4 ]; then
    echo "Usage: $0 <repo_path> <author_pattern> [since_date] [until_date]" >&2
    exit 1
fi

REPO_PATH="$1"
AUTHOR_PATTERN="$2"
SINCE_DATE="${3:-}"
UNTIL_DATE="${4:-}"

# Validate git repository
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_PATH" >&2
    exit 1
fi

# Collect commits for the author
# Format: hash|author_name|author_email|date|subject
# Use --all to include all branches
# Use --date=iso for consistent date formatting

# Build git log command with optional date filters
GIT_CMD=(git -C "$REPO_PATH" log --author="$AUTHOR_PATTERN" --all --date=iso --format='%H|%an|%ae|%ad|%s')

if [ -n "$SINCE_DATE" ]; then
    GIT_CMD+=(--since="$SINCE_DATE")
fi

if [ -n "$UNTIL_DATE" ]; then
    GIT_CMD+=(--until="$UNTIL_DATE")
fi

COMMITS=$("${GIT_CMD[@]}" 2>/dev/null || true)

# Check if any commits were found
if [ -z "$COMMITS" ]; then
    echo "Error: No commits found for author: $AUTHOR_PATTERN" >&2
    exit 2
fi

# Output commits
echo "$COMMITS"
exit 0
