#!/bin/bash

# count-user-commits.sh
# Fast commit count without fetching details
#
# Usage: ./count-user-commits.sh <repo_path> <author_pattern>
# Output: Single number (commit count)
# Exit codes: 0=success, 1=invalid repo, 2=no commits

set -euo pipefail

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <repo_path> <author_pattern>" >&2
    exit 1
fi

REPO_PATH="$1"
AUTHOR_PATTERN="$2"

# Validate git repository
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_PATH" >&2
    exit 1
fi

# Count commits for the author
# Use --oneline for minimal output, then count lines
# Use --all to include all branches
COUNT=$(git -C "$REPO_PATH" log \
    --author="$AUTHOR_PATTERN" \
    --all \
    --oneline 2>/dev/null | wc -l | tr -d ' ')

# Check if any commits were found
if [ "$COUNT" -eq 0 ]; then
    echo "Error: No commits found for author: $AUTHOR_PATTERN" >&2
    exit 2
fi

# Output count
echo "$COUNT"
exit 0
