#!/bin/bash

# fast-extract-commits.sh
# Fast commit extraction with batch processing and optional caching
#
# Usage: ./fast-extract-commits.sh <repo_path> <author_pattern> [options]
# Options:
#   --since=DATE        Only commits after this date
#   --until=DATE        Only commits before this date
#   --use-cache         Use cached data if available (default: true)
#   --no-cache          Force fresh extraction, ignore cache
#   --output=FILE       Write to file instead of stdout
#
# Output: JSONL format (same as batch-extract-commits.sh)
# Exit codes: 0=success, 1=invalid repo, 2=no commits

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults
USE_CACHE=true
OUTPUT_FILE=""
SINCE_DATE=""
UNTIL_DATE=""

# Parse arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <repo_path> <author_pattern> [options]" >&2
    echo "Options:" >&2
    echo "  --since=DATE    Only commits after this date" >&2
    echo "  --until=DATE    Only commits before this date" >&2
    echo "  --use-cache     Use cached data if available (default)" >&2
    echo "  --no-cache      Force fresh extraction" >&2
    echo "  --output=FILE   Write to file instead of stdout" >&2
    exit 1
fi

REPO_PATH="$1"
AUTHOR_PATTERN="$2"
shift 2

# Parse optional arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --since=*)
            SINCE_DATE="${1#--since=}"
            ;;
        --until=*)
            UNTIL_DATE="${1#--until=}"
            ;;
        --use-cache)
            USE_CACHE=true
            ;;
        --no-cache)
            USE_CACHE=false
            ;;
        --output=*)
            OUTPUT_FILE="${1#--output=}"
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
    shift
done

# Validate git repository
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_PATH" >&2
    exit 1
fi

# Get repository root (for cache location)
REPO_ROOT=$(git -C "$REPO_PATH" rev-parse --show-toplevel 2>/dev/null)
CACHE_DIR="$REPO_ROOT/.git-analysis-cache"
CACHE_FILE="$CACHE_DIR/commit-details.jsonl"
CACHE_META="$CACHE_DIR/cache-meta.json"

# Normalize author pattern for cache key
AUTHOR_KEY=$(echo "$AUTHOR_PATTERN" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')

# Check cache validity
check_cache() {
    if [ ! -f "$CACHE_FILE" ] || [ ! -f "$CACHE_META" ]; then
        return 1  # No cache
    fi

    # Read cache metadata
    local cached_author cached_since cached_until cached_timestamp
    cached_author=$(grep -o '"author":"[^"]*"' "$CACHE_META" 2>/dev/null | cut -d'"' -f4 || echo "")
    cached_since=$(grep -o '"since":"[^"]*"' "$CACHE_META" 2>/dev/null | cut -d'"' -f4 || echo "")
    cached_until=$(grep -o '"until":"[^"]*"' "$CACHE_META" 2>/dev/null | cut -d'"' -f4 || echo "")
    cached_timestamp=$(grep -o '"timestamp":[0-9]*' "$CACHE_META" 2>/dev/null | cut -d':' -f2 || echo "0")

    # Check if cache matches current request
    local current_author_key
    current_author_key=$(echo "$AUTHOR_PATTERN" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]')

    if [ "$cached_author" != "$current_author_key" ]; then
        return 1  # Different author
    fi

    if [ "$cached_since" != "$SINCE_DATE" ] || [ "$cached_until" != "$UNTIL_DATE" ]; then
        return 1  # Different date range
    fi

    # Check for new commits since cache was created
    local latest_commit_timestamp
    latest_commit_timestamp=$(git -C "$REPO_PATH" log --author="$AUTHOR_PATTERN" --all -1 --format='%at' 2>/dev/null || echo "0")

    if [ "$latest_commit_timestamp" -gt "$cached_timestamp" ]; then
        return 1  # New commits exist
    fi

    return 0  # Cache is valid
}

# Write cache metadata
write_cache_meta() {
    local timestamp
    timestamp=$(date +%s)

    mkdir -p "$CACHE_DIR"
    cat > "$CACHE_META" << EOF
{
  "author": "$AUTHOR_KEY",
  "since": "$SINCE_DATE",
  "until": "$UNTIL_DATE",
  "timestamp": $timestamp,
  "repo": "$REPO_ROOT"
}
EOF
}

# Main extraction logic
extract_commits() {
    local args=("$REPO_PATH" "$AUTHOR_PATTERN")

    if [ -n "$SINCE_DATE" ]; then
        args+=("$SINCE_DATE")
    fi

    if [ -n "$UNTIL_DATE" ]; then
        if [ -z "$SINCE_DATE" ]; then
            args+=("")  # Empty since_date placeholder
        fi
        args+=("$UNTIL_DATE")
    fi

    "$SCRIPT_DIR/batch-extract-commits.sh" "${args[@]}"
}

# Check if we can use cache
if [ "$USE_CACHE" = true ] && check_cache; then
    # Use cached data
    if [ -n "$OUTPUT_FILE" ]; then
        cp "$CACHE_FILE" "$OUTPUT_FILE"
    else
        cat "$CACHE_FILE"
    fi
    exit 0
fi

# Perform fresh extraction
RESULT=$(extract_commits)

if [ -z "$RESULT" ]; then
    echo "Error: No commits found for author: $AUTHOR_PATTERN" >&2
    exit 2
fi

# Write to cache
mkdir -p "$CACHE_DIR"
echo "$RESULT" > "$CACHE_FILE"
write_cache_meta

# Output result
if [ -n "$OUTPUT_FILE" ]; then
    echo "$RESULT" > "$OUTPUT_FILE"
else
    echo "$RESULT"
fi

exit 0
