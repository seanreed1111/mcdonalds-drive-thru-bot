---
name: analyze-git-contributions
description: Analyze git contributions and organize by functional components using AI
---

# Analyze Git Contributions

This skill analyzes a user's git contributions and intelligently groups them by functional components using AI-powered semantic analysis, producing a comprehensive markdown report.

## Core Principles

1. **Semantic Grouping**: Group commits by functionality and purpose, not directory structure
2. **Comprehensive Context**: Include commit messages, file changes, statistics, and temporal patterns
3. **Actionable Output**: Generate markdown reports that clearly communicate contribution themes
4. **Reusability**: Work across different repositories and authors without modification

## Workflow

### Phase 1: Setup and Validation
1. Determine repository path (use current directory or prompt for path)
2. Validate git repository using scripts
3. Detect or prompt for author name/email
4. Verify author has commits in repository

### Phase 2: Data Collection

#### Step 1: Count commits
1. Run `scripts/count-user-commits.sh` to get total commit count
2. Store count for decision logic

#### Step 2: Decide strategy based on count

**If count < 500:**
- Proceed with fast batch analysis
- Run `fast-extract-commits.sh` to gather all commit data in one pass
- Uses cached data if available (subsequent runs ~5 seconds)

**If count 500-2000:**
- Present user with options using AskUserQuestion:
  1. **Segmented analysis (Recommended)** - Create multiple reports, one per time period (e.g., quarterly)
  2. Intelligent sampling - Analyze 200 representative commits
  3. Date range filter - Specify a time period (e.g., last 6 months)
  4. Full analysis - Process all commits (may take longer)

**If count > 2000:**
- Inform user: "Found X commits. Please narrow the scope:"
- Options:
  1. **Segmented analysis (Recommended)** - Multiple reports by time period
  2. Date range filter - Specify a time period
  3. Intelligent sampling - 200 commits across entire timeline
- Do not offer "full analysis" option (would hit token limits)

#### Step 3: Collect based on strategy

**For full/fast analysis:**
```bash
# Fast batch extraction with caching
bash ~/.claude/skills/analyze-git-contributions/scripts/fast-extract-commits.sh \
    "$REPO_PATH" "$AUTHOR" --use-cache

# Output: JSONL format with all commit data including file changes
# Cached: Second runs complete in ~5 seconds
# First run: ~10-30 seconds depending on commit count
```

**For segmented analysis:**
- Run `scripts/calculate-time-segments.sh <repo> <author> <target_commits_per_segment>`
  - Script calculates date ranges and divides into segments
  - Target: 250-400 commits per segment (default: 300)
  - Returns: List of date ranges with commit counts
- For each segment:
  - Run `fast-extract-commits.sh <repo> <author> --since=<start> --until=<end>`
  - Analyze commits for that period (Phase 3)
  - Generate separate markdown file: `git-contributions-analysis-2024-Q1.md`
  - Include header: "Part X of Y - Period: YYYY-MM-DD to YYYY-MM-DD"
- Create index file listing all segments with links
- Each segment is analyzed independently (avoids token limits)

**For intelligent sampling:**
- Run `scripts/sample-commits.sh <repo> <author> 200` to get commit hashes
- Then use `fast-extract-commits.sh` to extract details for sampled commits
- Add note in report: "Analysis based on 200 representative commits sampled across YYYY-MM-DD to YYYY-MM-DD"
- Proceed to Phase 3 with sampled dataset

**For date range filter:**
- Run `fast-extract-commits.sh <repo> <author> --since=<date> --until=<date>`
- Process filtered commits
- Add note in report: "Analysis for period: YYYY-MM-DD to YYYY-MM-DD (X commits out of Y total)"
- Proceed to Phase 3 with filtered dataset

#### Step 4: Token budget check (safety)
- Before processing commit details, estimate token usage
- Rule of thumb: ~65 tokens per commit on average
- If estimated tokens > 20,000, reduce sample size or warn user
- This prevents edge cases (commits with huge diffs)
- For segmented analysis, each segment is checked independently

### Phase 3: AI Analysis
1. **Analyze commit semantics**: Read commit messages, file changes, and timing patterns
2. **Identify functional components**: Group commits by related functionality
   - Examples: "Authentication System", "Payment Processing", "UI/UX Improvements", "Bug Fixes", "Database Schema", "API Endpoints", "Test Coverage"
   - Look beyond directory structure - related changes across commits indicate a component
   - Consider temporal relationships (commits close in time often relate to same feature)
   - Examine file patterns (same files modified = related work)
3. **Generate component descriptions**: Summarize each component's purpose and impact
4. **Identify contribution themes**: High-level overview of major work areas

### Phase 4: Report Generation
1. Create markdown structure with metadata section
2. Add summary of contribution themes
3. For each component:
   - Component name and description
   - List commits with hash, date, subject
   - Show file changes with additions/deletions
4. Add statistics section:
   - Total files changed
   - Total additions/deletions
   - Most active areas
5. Write report to file or output directly

## Usage Patterns

### From Within Repository
```bash
# Run in current directory
/analyze-git-contributions

# Script auto-detects git config user.name
```

### External Repository
```bash
# Specify path
/analyze-git-contributions /path/to/repo

# Or when prompted
# Agent asks: "Enter repository path:"
# User provides: /Users/seanreed/projects/my-app
```

### Different Author
```bash
# Agent auto-detects from git config
# If not found or wrong author, agent asks:
# "Enter author name or email pattern:"
# User provides: "John Doe" or "john@example.com"
```

## Output Structure Example

### Full Analysis (< 500 commits)
```markdown
# Git Contributions Analysis
**Repository:** /path/to/repo
**Author:** Sean Reed
**Date Range:** 2025-01-01 to 2026-01-25
**Total Commits:** 342
**Analysis Scope:** All commits

## Summary
Implemented comprehensive real-time communication system with WebSocket support,
authentication mechanisms, and extensive test coverage. Major focus on payment
integration and API stability.

## Component: Real-Time Communication System
**Description:** Built WebSocket-based real-time messaging with presence detection
and reconnection logic.

**Commits (8):**
- `a1b2c3d` (2026-01-20) Add WebSocket connection manager
  - Files: websocket/manager.py (+245, -0), websocket/events.py (+120, -0)

- `e4f5g6h` (2026-01-19) Implement presence detection
  - Files: websocket/presence.py (+180, -0), tests/test_presence.py (+95, -0)

[... more commits ...]

## Component: Authentication & Security
**Description:** JWT-based authentication with session management and rate limiting.

**Commits (6):**
[... commits with details ...]

## Component: Bug Fixes & Maintenance
**Description:** Various bug fixes and code maintenance across the codebase.

**Commits (5):**
[... commits ...]

## Statistics
- Total files changed: 127
- Total additions: 3,450 lines
- Total deletions: 890 lines
- Most active areas: websocket/ (15 commits), auth/ (12 commits), api/ (10 commits)
```

### Sampled Analysis
```markdown
# Git Contributions Analysis
**Repository:** /path/to/repo
**Author:** Sean Reed
**Analysis Scope:** 200 sampled commits (out of 1,379 total)
**Sampling Strategy:** Time-stratified (evenly distributed across contribution timeline)
**Date Range:** 2024-01-15 to 2026-01-25
**Total Commits Analyzed:** 200

## Summary
[Analysis based on representative sample...]
```

### Date-Filtered Analysis
```markdown
# Git Contributions Analysis
**Repository:** /path/to/repo
**Author:** Sean Reed
**Analysis Scope:** Commits from 2025-06-01 to 2026-01-25
**Total Commits in Period:** 342
**Total Commits (All Time):** 1,379

## Summary
[Analysis of recent work...]
```

### Segmented Analysis (Index File)
```markdown
# Git Contributions Analysis - Index
**Repository:** /path/to/repo
**Author:** Sean Reed
**Total Commits:** 1,379
**Analysis Period:** 2024-01-15 to 2026-01-25
**Number of Segments:** 4

## Segments

### [Part 1: 2024-Q1-Q2 (Jan-Jun 2024)](git-contributions-analysis-2024-Q1-Q2.md)
- Period: 2024-01-15 to 2024-06-30
- Commits: 312
- Focus: Initial project setup, authentication system, core API

### [Part 2: 2024-Q3 (Jul-Sep 2024)](git-contributions-analysis-2024-Q3.md)
- Period: 2024-07-01 to 2024-09-30
- Commits: 298
- Focus: Payment integration, database migrations

### [Part 3: 2024-Q4 (Oct-Dec 2024)](git-contributions-analysis-2024-Q4.md)
- Period: 2024-10-01 to 2024-12-31
- Commits: 387
- Focus: WebSocket implementation, real-time features

### [Part 4: 2025 (Jan 2025)](git-contributions-analysis-2025.md)
- Period: 2025-01-01 to 2025-01-25
- Commits: 382
- Focus: Performance optimization, bug fixes, testing
```

### Segmented Analysis (Individual Segment)
```markdown
# Git Contributions Analysis - Part 1 of 4
**Repository:** /path/to/repo
**Author:** Sean Reed
**Period:** 2024-01-15 to 2024-06-30
**Commits in This Period:** 312
**Total Commits (All Time):** 1,379

[See index file](git-contributions-analysis-index.md) for all segments

## Summary
[Analysis for this time period...]
```

## Error Handling

### Invalid Repository
```bash
# If not a git repo
echo "Error: Not a git repository. Please specify a valid git repository path."
# Offer to navigate to correct directory or provide path
```

### No Commits Found
```bash
# If author has no commits
echo "No commits found for author: $AUTHOR"
# List top 5 contributors and ask user to select:
# 1. John Doe (john@example.com) - 150 commits
# 2. Jane Smith (jane@example.com) - 87 commits
# ...
```

### Large Repository (500-2000 commits)
```bash
# If 500-2000 commits for author
echo "Found 1,379 commits for Sean Reed (spanning 2024-01-15 to 2026-01-25)."
echo ""
echo "How would you like to proceed?"
echo ""
echo "1. Segmented analysis (Recommended) - Create 4 reports, one per time period"
echo "   (~345 commits each, organized chronologically)"
echo ""
echo "2. Intelligent sampling - Analyze 200 representative commits"
echo "   evenly distributed across your contribution timeline"
echo ""
echo "3. Date range filter - Specify a time period"
echo "   (e.g., last 6 months: --since='2025-07-01')"
echo ""
echo "4. Full analysis - Process all 1,379 commits"
echo "   (may take longer)"
```

### Very Large Repository (>2000 commits)
```bash
# If >2000 commits for author
echo "Found 3,450 commits for Sean Reed (spanning 2020-03-10 to 2026-01-25)."
echo ""
echo "To provide focused analysis, please narrow the scope:"
echo ""
echo "1. Segmented analysis (Recommended) - Create 11 reports, one per"
echo "   time period (~314 commits each)"
echo ""
echo "2. Recent work - Last 6 months"
echo ""
echo "3. Recent work - Last year"
echo ""
echo "4. Custom date range - Specify dates"
echo ""
echo "5. Intelligent sampling - 200 commits across entire timeline"
```

### Author Matching
```bash
# Multiple email addresses detected for same author
echo "Detected multiple identities for this author:"
echo "  - Sean Reed <sean@work.com> - 250 commits"
echo "  - Sean Reed <sean@personal.com> - 45 commits"
echo "Group all commits together? (yes/no)"
```

## Script Usage

### count-user-commits.sh
```bash
# Usage
./scripts/count-user-commits.sh <repo_path> <author_pattern>

# Example
./scripts/count-user-commits.sh /path/to/repo "Sean Reed"

# Output: Single number (commit count)
# 1379

# Exit codes
# 0 - Success
# 1 - Invalid repository
# 2 - No commits found
```

### collect-user-commits.sh
```bash
# Usage
./scripts/collect-user-commits.sh <repo_path> <author_pattern> [since_date] [until_date]

# Example - All commits
./scripts/collect-user-commits.sh /path/to/repo "Sean Reed"

# Example - With date filter
./scripts/collect-user-commits.sh /path/to/repo "Sean Reed" "2025-01-01"

# Example - With date range
./scripts/collect-user-commits.sh /path/to/repo "Sean Reed" "2024-04-14" "2025-05-26"

# Output format (one line per commit)
# hash|author_name|author_email|date|subject
# a1b2c3d4e5f6|Sean Reed|sean@example.com|2026-01-20 14:30:00 -0800|Add WebSocket manager

# Date formats supported
# - YYYY-MM-DD (e.g., 2025-01-01)
# - @timestamp (e.g., @1704067200)

# Exit codes
# 0 - Success
# 1 - Invalid repository
# 2 - No commits found
```

### sample-commits.sh
```bash
# Usage
./scripts/sample-commits.sh <repo_path> <author_pattern> <sample_size>

# Example
./scripts/sample-commits.sh /path/to/repo "Sean Reed" 200

# Output: Same format as collect-user-commits.sh (subset of commits)
# Uses time-stratified sampling for even distribution across timeline

# Strategy
# - Divides timeline into 10 buckets
# - Samples evenly from each bucket
# - Ensures coverage across entire contribution history
# - If total commits <= sample_size, returns all commits

# Exit codes
# 0 - Success
# 1 - Invalid repository or arguments
# 2 - No commits found
```

### calculate-time-segments.sh
```bash
# Usage
./scripts/calculate-time-segments.sh <repo_path> <author_pattern> <target_commits_per_segment>

# Example
./scripts/calculate-time-segments.sh /path/to/repo "Sean Reed" 300

# Output format (one line per segment)
# start_date|end_date|commit_count
# 2024-04-14|2025-04-13|398
# 2025-04-14|2025-08-03|366
# 2025-08-04|2025-10-17|295
# 2025-10-18|2025-12-03|320

# Algorithm
# - Calculates optimal time segments to keep commits per segment in target range
# - Uses adaptive boundaries based on commit density
# - Busy periods get shorter time segments, quiet periods get longer segments
# - Target range: target_commits ± 100 commits
# - Recommended target: 300 (safe range: 250-400)

# Exit codes
# 0 - Success
# 1 - Invalid repository or arguments
# 2 - No commits found
```

### extract-commit-details.sh
```bash
# Usage
./scripts/extract-commit-details.sh <repo_path> <commit_hash>

# Example
./scripts/extract-commit-details.sh /path/to/repo a1b2c3d4e5f6

# Output format
# === COMMIT MESSAGE ===
# [full commit message]
# === FILES CHANGED ===
# filename|additions|deletions
# [one line per file]

# Exit codes
# 0 - Success
# 1 - Invalid commit hash
```

### fast-extract-commits.sh
```bash
# Usage
./scripts/fast-extract-commits.sh <repo_path> <author_pattern> [options]

# Options
#   --since=DATE     Only commits after this date
#   --until=DATE     Only commits before this date
#   --use-cache      Use cached data if available (default)
#   --no-cache       Force fresh extraction
#   --output=FILE    Write to file instead of stdout

# Example - Fast extraction with caching
./scripts/fast-extract-commits.sh /path/to/repo "Sean Reed"

# Example - Force fresh extraction
./scripts/fast-extract-commits.sh /path/to/repo "Sean Reed" --no-cache

# Example - With date filter
./scripts/fast-extract-commits.sh /path/to/repo "Sean Reed" --since="2025-01-01"

# Output format: JSONL (one JSON object per commit)
# {"hash":"...","author":"...","email":"...","date":"...","subject":"...","body":"...","files":[...]}

# Performance:
# - First run (173 commits): ~5-10 seconds
# - Cached run: ~1-2 seconds
# - Compared to original: 3-5x faster

# Exit codes
# 0 - Success
# 1 - Invalid repository
# 2 - No commits found
```

### cache-manage.sh
```bash
# Usage
./scripts/cache-manage.sh <command> [repo_path]

# Commands
./scripts/cache-manage.sh status /path/to/repo  # Show cache info
./scripts/cache-manage.sh clear /path/to/repo   # Clear cache
./scripts/cache-manage.sh info /path/to/repo    # Show metadata

# Example output for 'status':
# Cache Directory: /path/to/repo/.git-analysis-cache
# Cache File: /path/to/repo/.git-analysis-cache/commit-details.jsonl
#   Size: 44K
#   Commits cached: 54
#   Last updated: 2026-01-25 13:17:22

# Cache location: <repo>/.git-analysis-cache/
# Recommended: Add .git-analysis-cache/ to .gitignore
```

### batch-extract-commits.sh
```bash
# Usage (internal, used by fast-extract-commits.sh)
./scripts/batch-extract-commits.sh <repo_path> <author_pattern> [since] [until]

# Extracts all commit data in a single git command
# Output: JSONL format
# Much faster than calling extract-commit-details.sh per commit

# Example
./scripts/batch-extract-commits.sh /path/to/repo "Sean Reed"

# Exit codes
# 0 - Success
# 1 - Invalid repository
# 2 - No commits found
```

## Implementation Details

### Step 1: Detect Repository
```bash
# If no argument provided, use current directory
REPO_PATH=${1:-.}

# Validate it's a git repository
if ! git -C "$REPO_PATH" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Error: Not a git repository: $REPO_PATH"
    # Ask user for correct path
fi
```

### Step 2: Detect Author
```bash
# Try to auto-detect from git config
AUTHOR=$(git -C "$REPO_PATH" config user.name 2>/dev/null)

# If not found or need confirmation
if [ -z "$AUTHOR" ]; then
    # Ask user for author name or email
    # Use AskUserQuestion tool to prompt
fi
```

### Step 3: Collect Data
```bash
# Run fast extraction with caching
commits_jsonl=$(bash ~/.claude/skills/analyze-git-contributions/scripts/fast-extract-commits.sh "$REPO_PATH" "$AUTHOR")

# Check exit code
if [ $? -eq 2 ]; then
    # No commits found - list top contributors
fi

# The commits are now in JSONL format, ready for AI analysis
# Each line contains: hash, author, email, date, subject, body, files[]
# No need to run extract-commit-details.sh for each commit - it's all included!
# Can parse with jq if needed: echo "$commits_jsonl" | jq '.hash'
```

### Step 4: AI Analysis
- Parse all commit data into structured format
- Analyze commit messages for semantic patterns
- Look for file co-modification patterns
- Identify temporal clusters (related commits close in time)
- Group commits into functional components
- Generate descriptions for each component

### Step 5: Generate Report
- Create markdown with metadata
- Add summary section
- For each component, list commits with details
- Calculate and add statistics
- Write to file (default: `git-contributions-analysis.md`) or output directly

## Reusability Features

### Flexible Repository Input
- Current directory (default)
- Absolute path
- Relative path
- Validates and resolves to absolute path

### Smart Author Detection
- Auto-detect from `git config user.name`
- Pattern matching for partial names
- Email-based filtering
- Case-insensitive matching
- Handle multiple email addresses

### Output Options
- Generate markdown file in repository root
- Or output to stdout for piping
- Filename: `git-contributions-analysis-{author}-{date}.md`

## Token Budget Management

### Understanding Token Limits
- Read tool has a 25,000 token limit for file contents
- Commit details average ~65 tokens per commit
- Safe processing limit: ~230 commits (15,000 tokens)
- Leave ~10,000 tokens for AI analysis and context

### Scaling Strategies

**Tier 1: Auto-Process (<500 commits)**
- Process all commits with full details
- No user intervention needed
- Estimated tokens: 500 × 65 = 32,500 tokens
- Safe due to incremental processing

**Tier 2: User Choice (500-2000 commits)**
- Present all four strategies to user
- Recommended: Segmented analysis for complete coverage
- Alternative: Sampling for quick overview
- Full analysis still available but may take longer

**Tier 3: Require Scoping (>2000 commits)**
- Require user to choose strategy
- Do not offer "process all" option
- Prevent token overflow
- Segmented analysis recommended

### Token Budget Examples

**Segmented Analysis (300 commits per segment):**
- Per segment: 300 × 65 = 19,500 tokens
- Safely under 25,000 token limit
- Each segment generates separate report
- No accumulated token pressure

**Intelligent Sampling (200 commits):**
- Total: 200 × 65 = 13,000 tokens
- Well under limit with room for analysis
- Representative across timeline

**Date Filtering (6 months, ~300 commits):**
- Total: 300 × 65 = 19,500 tokens
- Safe for focused period analysis

## Optional Enhancements (Future)

### Branch Filtering
```bash
/analyze-git-contributions --branch=main
```

### Multiple Authors
```bash
/analyze-git-contributions --authors="John Doe,Jane Smith"
```

### Export Formats
- JSON for programmatic use
- HTML with interactive visualization
- CSV for spreadsheet analysis

## Success Criteria

- ✅ Auto-discovers repository and author
- ✅ Efficiently collects git data using scripts
- ✅ AI produces semantically meaningful component groupings
- ✅ Markdown output is readable and well-organized
- ✅ Works across different repositories without modification
- ✅ Handles edge cases gracefully (no commits, large repos, binary files)
- ✅ Scripts have proper error handling and exit codes
- ✅ Reusable for different authors and repositories
- ✅ Scales to repositories with 500-10,000+ commits without token errors
- ✅ Provides user control over analysis scope (sampling, filtering, segmentation)
- ✅ Segmented analysis covers ALL commits across multiple manageable reports
- ✅ Maintains meaningful AI analysis quality across all strategies
- ✅ Token usage stays under limits for all analysis types
- ✅ Clear communication about what was analyzed (scope metadata)

## Reference

For bash script patterns and error handling, refer to existing skills:
- `~/.claude/skills/reading-logs/SKILL.md` - "Count first, filter/sample, then read" principle
- `~/.claude/skills/reading-logs/scripts/aggregate-errors.sh` - Error handling patterns
- Standard git command patterns and output parsing

## Core Principle (from reading-logs skill)

**"Count first, filter/sample, then read"** - Never process all data without checking volume first

This skill applies the same principle:
1. Count commits before processing
2. Choose appropriate strategy based on count
3. Filter, sample, or segment as needed
4. Process within token budget
5. Maintain analysis quality throughout
