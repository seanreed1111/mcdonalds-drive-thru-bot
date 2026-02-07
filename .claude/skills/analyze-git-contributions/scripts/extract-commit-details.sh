#!/bin/bash

# extract-commit-details.sh
# Extracts detailed information for a single commit
#
# Usage: ./extract-commit-details.sh <repo_path> <commit_hash>
# Output: Structured data with commit message and file changes
# Exit codes: 0=success, 1=invalid commit

set -euo pipefail

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <repo_path> <commit_hash>" >&2
    exit 1
fi

REPO_PATH="$1"
COMMIT_HASH="$2"

# Validate git repository
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_PATH" >&2
    exit 1
fi

# Validate commit hash
if ! git -C "$REPO_PATH" cat-file -e "$COMMIT_HASH^{commit}" 2>/dev/null; then
    echo "Error: Invalid commit hash: $COMMIT_HASH" >&2
    exit 1
fi

# Get full commit message
echo "=== COMMIT MESSAGE ==="
git -C "$REPO_PATH" show --format=%B -s "$COMMIT_HASH" 2>/dev/null

# Get file changes with statistics
echo "=== FILES CHANGED ==="
# Use --numstat for machine-readable format: additions deletions filename
# Handle binary files (shows - - filename)
# Handle merge commits gracefully
git -C "$REPO_PATH" show --numstat --format="" "$COMMIT_HASH" 2>/dev/null | while IFS=$'\t' read -r additions deletions filename; do
    # Skip empty lines
    if [ -z "$filename" ]; then
        continue
    fi

    # Handle binary files (additions and deletions are -)
    if [ "$additions" = "-" ]; then
        additions="0"
    fi
    if [ "$deletions" = "-" ]; then
        deletions="0"
    fi

    # Output: filename|additions|deletions
    echo "$filename|$additions|$deletions"
done

exit 0
