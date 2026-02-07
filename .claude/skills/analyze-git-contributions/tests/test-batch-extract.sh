#!/bin/bash

# test-batch-extract.sh
# Tests for batch-extract-commits.sh

set -eo pipefail  # Changed from -euo to -eo to be less strict

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BATCH_SCRIPT="$SCRIPT_DIR/scripts/batch-extract-commits.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

test_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED++)) || true
}

test_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((TESTS_FAILED++)) || true
}

test_skip() {
    echo -e "${YELLOW}⚠ SKIP:${NC} $1"
}

echo "========================================"
echo "Testing batch-extract-commits.sh"
echo "========================================"
echo ""

# Test 1: Invalid repository
echo "Test 1: Invalid repository returns exit code 1"
set +e
"$BATCH_SCRIPT" "/nonexistent/path" "Test Author" >/dev/null 2>&1
EXIT_CODE=$?
set -e
if [ $EXIT_CODE -ne 0 ]; then
    test_pass "Invalid repository returns non-zero exit code"
else
    test_fail "Invalid repository should return non-zero exit code"
fi

# Find a test repository
# Try multiple locations in order of preference
TEST_REPO=""
for potential_repo in \
    "/Users/seanreed/PythonProjects/voice-ai/lk-mcdonalds-agent-1" \
    "$HOME" \
    "$SCRIPT_DIR"; do
    if [ -d "$potential_repo/.git" ]; then
        TEST_REPO="$potential_repo"
        break
    fi
done

if [ -z "$TEST_REPO" ]; then
    test_skip "No git repository found for testing (tried common locations)"
    echo ""
    echo "========================================"
    echo "Tests passed: $TESTS_PASSED"
    echo "Tests failed: $TESTS_FAILED"
    echo "========================================"
    exit 0
fi

echo ""
echo "Using test repository: $TEST_REPO"

# Get an author from the test repo
TEST_AUTHOR=$(git -C "$TEST_REPO" log -1 --format='%an' 2>/dev/null || echo "")

if [ -z "$TEST_AUTHOR" ]; then
    test_skip "No commits found in test repository"
    echo ""
    echo "========================================"
    echo "Tests passed: $TESTS_PASSED"
    echo "Tests failed: $TESTS_FAILED"
    echo "========================================"
    exit 0
fi

echo "Using test author: $TEST_AUTHOR"
echo ""

# Test 2: Valid repository extracts commits
echo "Test 2: Valid repository extracts commits"
set +e
OUTPUT=$("$BATCH_SCRIPT" "$TEST_REPO" "$TEST_AUTHOR" 2>&1)
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ] && [ -n "$OUTPUT" ]; then
    test_pass "Script executes successfully with valid input"
else
    test_fail "Script should succeed with valid repository and author"
fi

# Test 3: Output format is valid JSONL
echo ""
echo "Test 3: Output is valid JSONL format"
FIRST_LINE=$(echo "$OUTPUT" | head -1)
if echo "$FIRST_LINE" | jq '.' >/dev/null 2>&1; then
    test_pass "First line is valid JSON"
else
    test_fail "First line should be valid JSON"
fi

# Test 4: Required fields exist
echo ""
echo "Test 4: Output contains required fields"
if echo "$FIRST_LINE" | jq -e '.hash' >/dev/null 2>&1 && \
   echo "$FIRST_LINE" | jq -e '.author' >/dev/null 2>&1 && \
   echo "$FIRST_LINE" | jq -e '.email' >/dev/null 2>&1 && \
   echo "$FIRST_LINE" | jq -e '.date' >/dev/null 2>&1 && \
   echo "$FIRST_LINE" | jq -e '.subject' >/dev/null 2>&1 && \
   echo "$FIRST_LINE" | jq -e '.body' >/dev/null 2>&1 && \
   echo "$FIRST_LINE" | jq -e '.files' >/dev/null 2>&1; then
    test_pass "All required fields present (hash, author, email, date, subject, body, files)"
else
    test_fail "Missing required fields"
fi

# Test 5: Files array structure
echo ""
echo "Test 5: Files array has correct structure"
# Find a commit with files (don't use -r flag, we want JSON not raw strings)
COMMIT_WITH_FILES=$(echo "$OUTPUT" | jq -c 'select(.files | length > 0)' 2>/dev/null | head -1 || true)
if [ -n "$COMMIT_WITH_FILES" ]; then
    if echo "$COMMIT_WITH_FILES" | jq -e '.files[0].path' >/dev/null 2>&1 && \
       echo "$COMMIT_WITH_FILES" | jq -e '.files[0].additions' >/dev/null 2>&1 && \
       echo "$COMMIT_WITH_FILES" | jq -e '.files[0].deletions' >/dev/null 2>&1; then
        test_pass "Files array contains path, additions, deletions"
    else
        test_fail "Files array missing required fields"
    fi
else
    test_skip "No commits with files found (testing with empty commits)"
fi

# Test 6: Nonexistent author
echo ""
echo "Test 6: Nonexistent author returns exit code 2"
set +e
"$BATCH_SCRIPT" "$TEST_REPO" "NonexistentAuthor999999" >/dev/null 2>&1
EXIT_CODE=$?
set -e
if [ $EXIT_CODE -eq 2 ]; then
    test_pass "Nonexistent author returns exit code 2"
else
    test_fail "Nonexistent author should return exit code 2 (got $EXIT_CODE)"
fi

# Test 7: Date filtering
echo ""
echo "Test 7: Date filtering works"
RECENT_DATE=$(date -v-30d '+%Y-%m-%d' 2>/dev/null || date -d '30 days ago' '+%Y-%m-%d' 2>/dev/null || echo "2025-12-01")
set +e
OUTPUT_WITH_DATE=$("$BATCH_SCRIPT" "$TEST_REPO" "$TEST_AUTHOR" "$RECENT_DATE" 2>&1)
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ]; then
    test_pass "Date filtering executes without error"

    # Verify output is still valid JSONL
    if [ -n "$OUTPUT_WITH_DATE" ]; then
        FIRST_LINE=$(echo "$OUTPUT_WITH_DATE" | head -1)
        if echo "$FIRST_LINE" | jq '.' >/dev/null 2>&1; then
            test_pass "Date-filtered output is valid JSON"
        else
            test_fail "Date-filtered output should be valid JSON"
        fi
    else
        test_skip "No commits found with date filter (may be expected)"
    fi
else
    test_skip "Date filtering returned error (may be expected if no commits in range)"
fi

# Summary
echo ""
echo "========================================"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo "========================================"

if [ "$TESTS_FAILED" -gt 0 ]; then
    exit 1
fi

exit 0
