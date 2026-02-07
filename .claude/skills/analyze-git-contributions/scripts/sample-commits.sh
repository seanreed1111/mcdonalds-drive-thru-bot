#!/bin/bash

# sample-commits.sh
# Samples commits using time-stratified strategy
#
# Usage: ./sample-commits.sh <repo_path> <author_pattern> <sample_size>
# Strategy: Divide timeline into buckets, sample evenly from each
# Output: Same format as collect-user-commits.sh (subset of commits)
# Exit codes: 0=success, 1=invalid repo/args, 2=no commits

set -uo pipefail

# Check arguments
if [ $# -ne 3 ]; then
    echo "Usage: $0 <repo_path> <author_pattern> <sample_size>" >&2
    exit 1
fi

REPO_PATH="$1"
AUTHOR_PATTERN="$2"
SAMPLE_SIZE="$3"

# Validate sample size is a positive integer
if ! [[ "$SAMPLE_SIZE" =~ ^[0-9]+$ ]] || [ "$SAMPLE_SIZE" -le 0 ]; then
    echo "Error: sample_size must be a positive integer" >&2
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
    --oneline 2>/dev/null | wc -l | tr -d ' ')

# Check if any commits were found
if [ "$TOTAL_COMMITS" -eq 0 ]; then
    echo "Error: No commits found for author: $AUTHOR_PATTERN" >&2
    exit 2
fi

# If total commits <= sample size, return all commits
if [ "$TOTAL_COMMITS" -le "$SAMPLE_SIZE" ]; then
    git -C "$REPO_PATH" log \
        --author="$AUTHOR_PATTERN" \
        --all \
        --date=iso \
        --format='%H|%an|%ae|%ad|%s' 2>/dev/null
    exit 0
fi

# Time-stratified sampling algorithm
# Divide timeline into buckets and sample evenly from each

# Number of buckets (use 10 buckets for good distribution)
NUM_BUCKETS=10
COMMITS_PER_BUCKET=$((SAMPLE_SIZE / NUM_BUCKETS))
REMAINDER=$((SAMPLE_SIZE % NUM_BUCKETS))

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

# Calculate bucket duration in seconds
TIMELINE_DURATION=$((LAST_TIMESTAMP - FIRST_TIMESTAMP))

# Handle edge case where all commits are at the same time
if [ "$TIMELINE_DURATION" -eq 0 ]; then
    git -C "$REPO_PATH" log \
        --author="$AUTHOR_PATTERN" \
        --all \
        --date=iso \
        --format='%H|%an|%ae|%ad|%s' \
        -n "$SAMPLE_SIZE" 2>/dev/null
    exit 0
fi

BUCKET_DURATION=$((TIMELINE_DURATION / NUM_BUCKETS))

# Sample commits from each bucket and output directly
for i in $(seq 0 $((NUM_BUCKETS - 1))); do
    # Calculate bucket time range
    BUCKET_START=$((FIRST_TIMESTAMP + i * BUCKET_DURATION))
    BUCKET_END=$((FIRST_TIMESTAMP + (i + 1) * BUCKET_DURATION))

    # For the last bucket, include everything up to and beyond LAST_TIMESTAMP
    if [ $i -eq $((NUM_BUCKETS - 1)) ]; then
        BUCKET_END=$((LAST_TIMESTAMP + 86400))  # Add one day to ensure we catch the last commit
    fi

    # Calculate how many commits to take from this bucket
    # Add 1 extra commit to first N buckets if there's a remainder
    TAKE_COUNT=$COMMITS_PER_BUCKET
    if [ $i -lt $REMAINDER ]; then
        TAKE_COUNT=$((TAKE_COUNT + 1))
    fi

    # Skip if TAKE_COUNT is 0
    if [ "$TAKE_COUNT" -eq 0 ]; then
        continue
    fi

    # Get commits from this bucket
    # Use Unix timestamps directly (git supports @timestamp format)
    BUCKET_COMMITS=$(git -C "$REPO_PATH" log \
        --author="$AUTHOR_PATTERN" \
        --all \
        --since="@$BUCKET_START" \
        --until="@$BUCKET_END" \
        --date=iso \
        --format='%H|%an|%ae|%ad|%s' 2>/dev/null || true)

    # Count commits in bucket
    if [ -n "$BUCKET_COMMITS" ]; then
        BUCKET_COUNT=$(echo "$BUCKET_COMMITS" | wc -l | tr -d ' ')

        # Sample evenly from bucket
        if [ "$BUCKET_COUNT" -le "$TAKE_COUNT" ]; then
            # Take all commits if bucket has fewer than needed
            echo "$BUCKET_COMMITS"
        else
            # Sample evenly distributed commits from bucket
            # Calculate step size for even distribution
            STEP=$((BUCKET_COUNT / TAKE_COUNT))
            if [ "$STEP" -eq 0 ]; then
                STEP=1
            fi

            # Take every Nth commit
            echo "$BUCKET_COMMITS" | awk "NR % $STEP == 1" | head -n "$TAKE_COUNT"
        fi
    fi
done

exit 0
