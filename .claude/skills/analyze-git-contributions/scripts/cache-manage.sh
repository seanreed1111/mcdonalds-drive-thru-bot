#!/bin/bash

# cache-manage.sh
# Manages the git analysis cache
#
# Usage: ./cache-manage.sh <command> [repo_path]
# Commands:
#   status [repo]    Show cache status (size, age, validity)
#   clear [repo]     Clear the cache
#   info [repo]      Show detailed cache metadata
#
# If repo_path is omitted, uses current directory

set -euo pipefail

# Parse arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <command> [repo_path]" >&2
    echo "Commands:" >&2
    echo "  status [repo]    Show cache status" >&2
    echo "  clear [repo]     Clear the cache" >&2
    echo "  info [repo]      Show detailed cache metadata" >&2
    exit 1
fi

COMMAND="$1"
REPO_PATH="${2:-.}"

# Validate git repository
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_PATH" >&2
    exit 1
fi

# Get repository root
REPO_ROOT=$(git -C "$REPO_PATH" rev-parse --show-toplevel 2>/dev/null)
CACHE_DIR="$REPO_ROOT/.git-analysis-cache"
CACHE_FILE="$CACHE_DIR/commit-details.jsonl"
CACHE_META="$CACHE_DIR/cache-meta.json"

case "$COMMAND" in
    status)
        if [ ! -d "$CACHE_DIR" ]; then
            echo "No cache exists for this repository."
            exit 0
        fi

        echo "Cache Directory: $CACHE_DIR"

        if [ -f "$CACHE_FILE" ]; then
            SIZE=$(du -h "$CACHE_FILE" 2>/dev/null | awk '{print $1}')
            LINES=$(wc -l < "$CACHE_FILE" 2>/dev/null | tr -d ' ')
            echo "Cache File: $CACHE_FILE"
            echo "  Size: $SIZE"
            echo "  Commits cached: $LINES"

            if [ -f "$CACHE_META" ]; then
                TIMESTAMP=$(grep -o '"timestamp": [0-9]*' "$CACHE_META" 2>/dev/null | awk '{print $2}' || echo "0")
                TIMESTAMP="${TIMESTAMP:-0}"  # Default to 0 if empty
                if [ "$TIMESTAMP" -gt 0 ] 2>/dev/null; then
                    # Convert timestamp to human-readable date
                    if DATE_STR=$(date -r "$TIMESTAMP" '+%Y-%m-%d %H:%M:%S' 2>/dev/null); then
                        echo "  Last updated: $DATE_STR"
                    elif DATE_STR=$(date -d "@$TIMESTAMP" '+%Y-%m-%d %H:%M:%S' 2>/dev/null); then
                        echo "  Last updated: $DATE_STR"
                    else
                        echo "  Last updated: Unknown"
                    fi
                fi
            fi
        else
            echo "Cache file not found."
        fi
        ;;

    clear)
        if [ ! -d "$CACHE_DIR" ]; then
            echo "No cache to clear."
            exit 0
        fi

        rm -rf "$CACHE_DIR"
        echo "Cache cleared: $CACHE_DIR"
        ;;

    info)
        if [ ! -f "$CACHE_META" ]; then
            echo "No cache metadata found."
            exit 0
        fi

        echo "Cache Metadata:"
        cat "$CACHE_META"
        ;;

    *)
        echo "Unknown command: $COMMAND" >&2
        echo "Use: status, clear, or info" >&2
        exit 1
        ;;
esac

exit 0
