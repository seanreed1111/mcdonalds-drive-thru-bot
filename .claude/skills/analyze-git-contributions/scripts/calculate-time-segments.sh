#!/bin/bash

# calculate-time-segments.sh
# Calculates optimal time segments to keep commits per segment in target range
#
# Usage: ./calculate-time-segments.sh <repo_path> <author_pattern> <target_commits_per_segment>
# Output: Date ranges, one per line (format: start_date|end_date|commit_count)
# Exit codes: 0=success, 1=invalid repo/args, 2=no commits

set -uo pipefail

# Check arguments
if [ $# -ne 3 ]; then
    echo "Usage: $0 <repo_path> <author_pattern> <target_commits_per_segment>" >&2
    exit 1
fi

REPO_PATH="$1"
AUTHOR_PATTERN="$2"
TARGET_COMMITS="$3"

# Validate target is a positive integer
if ! [[ "$TARGET_COMMITS" =~ ^[0-9]+$ ]] || [ "$TARGET_COMMITS" -le 0 ]; then
    echo "Error: target_commits_per_segment must be a positive integer" >&2
    exit 1
fi

# Validate git repository
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_PATH" >&2
    exit 1
fi

# Get total commit count
TOTAL_COMMITS=$(git -C "$REPO_PATH" log \
    --author="$AUTHOR_PATTERN" \
    --all \
    --oneline | wc -l | tr -d ' ')

# Check if any commits were found
if [ "$TOTAL_COMMITS" -eq 0 ]; then
    echo "Error: No commits found for author: $AUTHOR_PATTERN" >&2
    exit 2
fi

# If total commits <= target, return single segment
if [ "$TOTAL_COMMITS" -le "$TARGET_COMMITS" ]; then
    FIRST_DATE=$(git -C "$REPO_PATH" log \
        --author="$AUTHOR_PATTERN" \
        --all \
        --reverse \
        --format='%ad' \
        --date=short | head -1 2>/dev/null)

    LAST_DATE=$(git -C "$REPO_PATH" log \
        --author="$AUTHOR_PATTERN" \
        --all \
        --format='%ad' \
        --date=short | head -1 2>/dev/null)

    echo "$FIRST_DATE|$LAST_DATE|$TOTAL_COMMITS"
    exit 0
fi

# Calculate number of segments needed
NUM_SEGMENTS=$(( (TOTAL_COMMITS + TARGET_COMMITS - 1) / TARGET_COMMITS ))

# Get first and last commit timestamps
FIRST_TIMESTAMP=$(git -C "$REPO_PATH" log \
    --author="$AUTHOR_PATTERN" \
    --all \
    --reverse \
    --format='%at' | head -1 2>/dev/null)

LAST_TIMESTAMP=$(git -C "$REPO_PATH" log \
    --author="$AUTHOR_PATTERN" \
    --all \
    --format='%at' | head -1 2>/dev/null)

# Calculate initial segment duration
TIMELINE_DURATION=$((LAST_TIMESTAMP - FIRST_TIMESTAMP))
SEGMENT_DURATION=$((TIMELINE_DURATION / NUM_SEGMENTS))

# Minimum segment duration (1 day in seconds)
MIN_SEGMENT_DURATION=86400

if [ "$SEGMENT_DURATION" -lt "$MIN_SEGMENT_DURATION" ]; then
    SEGMENT_DURATION=$MIN_SEGMENT_DURATION
fi

# Generate segments with adaptive boundaries
# Strategy: Dynamically adjust segment duration based on commit density
CURRENT_START=$FIRST_TIMESTAMP
REMAINING_COMMITS=$TOTAL_COMMITS

# Maximum commits allowed per segment (upper bound)
MAX_COMMITS_PER_SEGMENT=$((TARGET_COMMITS + 100))

while [ "$CURRENT_START" -lt "$LAST_TIMESTAMP" ]; do
    # Calculate how many commits we still need to process
    COMMITS_LEFT=$(git -C "$REPO_PATH" log \
        --author="$AUTHOR_PATTERN" \
        --all \
        --since="@$CURRENT_START" \
        --oneline | wc -l | tr -d ' ')

    if [ "$COMMITS_LEFT" -eq 0 ]; then
        break
    fi

    # If remaining commits fit in one segment, take them all
    if [ "$COMMITS_LEFT" -le "$MAX_COMMITS_PER_SEGMENT" ]; then
        CURRENT_END=$((LAST_TIMESTAMP + 86400))
        SEGMENT_COUNT=$COMMITS_LEFT
    else
        # Binary search for the right end time to get close to TARGET_COMMITS
        TIME_LEFT=$((LAST_TIMESTAMP - CURRENT_START))

        # Initial guess: proportional to target commits
        ESTIMATED_DURATION=$((TIME_LEFT * TARGET_COMMITS / COMMITS_LEFT))

        # Ensure minimum duration
        if [ "$ESTIMATED_DURATION" -lt "$MIN_SEGMENT_DURATION" ]; then
            ESTIMATED_DURATION=$MIN_SEGMENT_DURATION
        fi

        CURRENT_END=$((CURRENT_START + ESTIMATED_DURATION))

        # Ensure we don't go beyond last commit
        if [ "$CURRENT_END" -gt "$((LAST_TIMESTAMP + 86400))" ]; then
            CURRENT_END=$((LAST_TIMESTAMP + 86400))
        fi

        # Count commits in estimated segment
        SEGMENT_COUNT=$(git -C "$REPO_PATH" log \
            --author="$AUTHOR_PATTERN" \
            --all \
            --since="@$CURRENT_START" \
            --until="@$CURRENT_END" \
            --oneline | wc -l | tr -d ' ')

        # Binary search to refine the end time
        MAX_ITERATIONS=10
        ITERATION=0
        LOWER_BOUND=$CURRENT_START
        UPPER_BOUND=$((LAST_TIMESTAMP + 86400))

        while [ "$ITERATION" -lt "$MAX_ITERATIONS" ]; do
            if [ "$SEGMENT_COUNT" -ge $((TARGET_COMMITS - 50)) ] && [ "$SEGMENT_COUNT" -le "$MAX_COMMITS_PER_SEGMENT" ]; then
                # Good enough, accept this segment
                break
            elif [ "$SEGMENT_COUNT" -lt "$TARGET_COMMITS" ]; then
                # Too few commits, expand the time range
                LOWER_BOUND=$CURRENT_END
                CURRENT_END=$(( (CURRENT_END + UPPER_BOUND) / 2 ))
            else
                # Too many commits, shrink the time range
                UPPER_BOUND=$CURRENT_END
                CURRENT_END=$(( (CURRENT_END + LOWER_BOUND) / 2 ))
            fi

            # Ensure we don't create a segment smaller than minimum duration
            if [ $((CURRENT_END - CURRENT_START)) -lt "$MIN_SEGMENT_DURATION" ]; then
                CURRENT_END=$((CURRENT_START + MIN_SEGMENT_DURATION))
            fi

            # Recount commits
            SEGMENT_COUNT=$(git -C "$REPO_PATH" log \
                --author="$AUTHOR_PATTERN" \
                --all \
                --since="@$CURRENT_START" \
                --until="@$CURRENT_END" \
                --oneline | wc -l | tr -d ' ')

            ITERATION=$((ITERATION + 1))
        done
    fi

    # Convert timestamps to dates
    if command -v date >/dev/null 2>&1; then
        # Try macOS format first, then Linux format
        START_DATE=$(date -r "$CURRENT_START" '+%Y-%m-%d' 2>/dev/null || date -d "@$CURRENT_START" '+%Y-%m-%d' 2>/dev/null)
        END_DATE=$(date -r "$((CURRENT_END - 86400))" '+%Y-%m-%d' 2>/dev/null || date -d "@$((CURRENT_END - 86400))" '+%Y-%m-%d' 2>/dev/null)
    fi

    # Output segment (only if it has commits)
    if [ "$SEGMENT_COUNT" -gt 0 ]; then
        echo "$START_DATE|$END_DATE|$SEGMENT_COUNT"
    fi

    # Move to next segment
    CURRENT_START=$CURRENT_END

    # Safety check: prevent infinite loop
    if [ "$CURRENT_START" -ge "$((LAST_TIMESTAMP + 86400))" ]; then
        break
    fi
done

exit 0
