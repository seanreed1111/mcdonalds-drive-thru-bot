#!/bin/bash

# batch-extract-commits.sh
# Extracts all commit data for an author in a single git command
#
# Usage: ./batch-extract-commits.sh <repo_path> <author_pattern> [since_date] [until_date]
# Output: JSONL format - one JSON object per commit
# Format: {"hash":"...","author":"...","email":"...","date":"...","subject":"...","body":"...","files":[{"path":"...","additions":N,"deletions":N},...]}
# Exit codes: 0=success, 1=invalid repo, 2=no commits

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

# Build git log command
# Format: COMMIT_START marker, then metadata, then body, then numstat
# We use a unique delimiter that won't appear in commit messages
DELIMITER="__COMMIT_BOUNDARY_7f3a2b1c__"
FORMAT="${DELIMITER}%H|%an|%ae|%ad|%s%n%b"

GIT_CMD=(git -C "$REPO_PATH" log --author="$AUTHOR_PATTERN" --all --date=iso --numstat --format="$FORMAT")

if [ -n "$SINCE_DATE" ]; then
    GIT_CMD+=(--since="$SINCE_DATE")
fi

if [ -n "$UNTIL_DATE" ]; then
    GIT_CMD+=(--until="$UNTIL_DATE")
fi

# Execute git command and parse output
OUTPUT=$("${GIT_CMD[@]}" 2>/dev/null || true)

if [ -z "$OUTPUT" ]; then
    echo "Error: No commits found for author: $AUTHOR_PATTERN" >&2
    exit 2
fi

# Parse the output into JSONL format
# State machine to track where we are in parsing
current_hash=""
current_author=""
current_email=""
current_date=""
current_subject=""
current_body=""
current_files=""
in_body=false

# Helper function to escape JSON strings
json_escape() {
    local str="$1"
    str="${str//\\/\\\\}"      # Escape backslashes first
    str="${str//\"/\\\"}"      # Escape double quotes
    str="${str//$'\n'/\\n}"    # Escape newlines
    str="${str//$'\r'/\\r}"    # Escape carriage returns
    str="${str//$'\t'/\\t}"    # Escape tabs
    printf '%s' "$str"
}

# Function to output current commit as JSON
output_commit() {
    if [ -n "$current_hash" ]; then
        local body_escaped=$(json_escape "$current_body")
        local subject_escaped=$(json_escape "$current_subject")

        # Remove trailing comma from files array if present
        current_files="${current_files%,}"

        echo "{\"hash\":\"$current_hash\",\"author\":\"$current_author\",\"email\":\"$current_email\",\"date\":\"$current_date\",\"subject\":\"$subject_escaped\",\"body\":\"$body_escaped\",\"files\":[$current_files]}"
    fi
}

# Process output line by line
while IFS= read -r line || [ -n "$line" ]; do
    # Check for commit boundary
    if [[ "$line" == "${DELIMITER}"* ]]; then
        # Output previous commit if exists
        output_commit

        # Parse new commit header
        # Format: DELIMITER hash|author|email|date|subject
        header="${line#$DELIMITER}"
        IFS='|' read -r current_hash current_author current_email current_date current_subject <<< "$header"

        # Reset state
        current_body=""
        current_files=""
        in_body=true
        continue
    fi

    # Check for numstat line (format: additions<TAB>deletions<TAB>filename)
    if [[ "$line" =~ ^[0-9-]+$'\t'[0-9-]+$'\t' ]]; then
        in_body=false

        # Parse numstat
        IFS=$'\t' read -r additions deletions filepath <<< "$line"

        # Handle binary files (shows - -)
        [ "$additions" = "-" ] && additions=0
        [ "$deletions" = "-" ] && deletions=0

        # Escape filepath for JSON
        filepath_escaped=$(json_escape "$filepath")

        # Add to files array
        if [ -n "$current_files" ]; then
            current_files+=","
        fi
        current_files+="{\"path\":\"$filepath_escaped\",\"additions\":$additions,\"deletions\":$deletions}"
    elif [ "$in_body" = true ] && [ -n "$current_hash" ]; then
        # Accumulate body text
        if [ -n "$current_body" ]; then
            current_body+=$'\n'
        fi
        current_body+="$line"
    fi
done <<< "$OUTPUT"

# Output final commit
output_commit

exit 0
