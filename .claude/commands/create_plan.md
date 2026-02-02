---
description: Create detailed implementation plans through interactive research and iteration
model: opus

---

# Implementation Plan

You are tasked with creating detailed implementation plans through an interactive, iterative process. You should be skeptical, thorough, and work collaboratively with the user to produce high-quality technical specifications.

## Initial Response

When this command is invoked:

1. **Check if parameters were provided**:
   - If a file path or ticket reference was provided as a parameter, skip the default message
   - Immediately read any provided files FULLY
   - Begin the research process

2. **If no parameters provided**, respond with:
```
I'll help you create a detailed implementation plan. Let me start by understanding what we're building.

Please provide:
1. The task/ticket description (or reference to a ticket file)
2. Any relevant context, constraints, or specific requirements
3. Links to related research or previous implementations

I'll analyze this information and work with you to create a comprehensive plan.

Tip: You can also invoke this command with a ticket file directly: `/create_plan docs/tickets/eng_1234.md`
For deeper analysis, try: `/create_plan think deeply about docs/tickets/eng_1234.md`
```

Then wait for the user's input.

## Process Steps

### Step 1: Context Gathering & Initial Analysis

1. **Read all mentioned files immediately and FULLY**:
   - Ticket files (e.g., `docs/tickets/eng_1234.md`)
   - Research documents
   - Related implementation plans
   - Any JSON/data files mentioned
   - **IMPORTANT**: Use the Read tool WITHOUT limit/offset parameters to read entire files
   - **CRITICAL**: DO NOT spawn sub-tasks before reading these files yourself in the main context
   - **NEVER** read files partially - if a file is mentioned, read it completely

2. **Spawn initial research tasks to gather context**:
   Before asking the user any questions, use specialized agents to research in parallel:

   - Use the **codebase-locator** agent to find all files related to the ticket/task
   - Use the **codebase-analyzer** agent to understand how the current implementation works
   - If relevant, use the **thoughts-locator** agent to find any existing thoughts documents about this feature
   - If a Linear ticket is mentioned, use the **linear-ticket-reader** agent to get full details

   These agents will:
   - Find relevant source files, configs, and tests
   - Identify the specific directories to focus on based on the task
   - Trace data flow and key functions
   - Return detailed explanations with file:line references

3. **Read all files identified by research tasks**:
   - After research tasks complete, read ALL files they identified as relevant
   - Read them FULLY into the main context
   - This ensures you have complete understanding before proceeding

4. **Analyze and verify understanding**:
   - Cross-reference the ticket requirements with actual code
   - Identify any discrepancies or misunderstandings
   - Note assumptions that need verification
   - Determine true scope based on codebase reality

5. **Present informed understanding and focused questions**:
   ```
   Based on the ticket and my research of the codebase, I understand we need to [accurate summary].

   I've found that:
   - [Current implementation detail with file:line reference]
   - [Relevant pattern or constraint discovered]
   - [Potential complexity or edge case identified]

   Questions that my research couldn't answer:
   - [Specific technical question that requires human judgment]
   - [Business logic clarification]
   - [Design preference that affects implementation]
   ```

   Only ask questions that you genuinely cannot answer through code investigation.

### Step 2: Research & Discovery

After getting initial clarifications:

1. **If the user corrects any misunderstanding**:
   - DO NOT just accept the correction
   - Spawn new research tasks to verify the correct information
   - Read the specific files/directories they mention
   - Only proceed once you've verified the facts yourself

2. **Create a research todo list** using TodoWrite to track exploration tasks

3. **Spawn parallel sub-tasks for comprehensive research**:
   - Create multiple Task agents to research different aspects concurrently
   - Use the right agent for each type of research:

   **For deeper investigation:**
   - **codebase-locator** - To find more specific files (e.g., "find all files that handle [specific component]")
   - **codebase-analyzer** - To understand implementation details (e.g., "analyze how [system] works")
   - **codebase-pattern-finder** - To find similar features we can model after

   **For historical context:**
   - **thoughts-locator** - To find any research, plans, or decisions about this area
   - **thoughts-analyzer** - To extract key insights from the most relevant documents

   **For related tickets:**
   - **linear-searcher** - To find similar issues or past implementations

   Each agent knows how to:
   - Find the right files and code patterns
   - Identify conventions and patterns to follow
   - Look for integration points and dependencies
   - Return specific file:line references
   - Find tests and examples

3. **Wait for ALL sub-tasks to complete** before proceeding

4. **Present findings and design options**:
   ```
   Based on my research, here's what I found:

   **Current State:**
   - [Key discovery about existing code]
   - [Pattern or convention to follow]

   **Design Options:**
   1. [Option A] - [pros/cons]
   2. [Option B] - [pros/cons]

   **Open Questions:**
   - [Technical uncertainty]
   - [Design decision needed]

   Which approach aligns best with your vision?
   ```

### Step 3: Plan Structure Development

Once aligned on approach:

1. **Create initial plan outline**:
   ```
   Here's my proposed plan structure:

   ## Overview
   [1-2 sentence summary]

   ## Implementation Phases:
   1. [Phase name] - [what it accomplishes]
   2. [Phase name] - [what it accomplishes]
   3. [Phase name] - [what it accomplishes]

   Does this phasing make sense? Should I adjust the order or granularity?
   ```

2. **Get feedback on structure** before writing details

### Step 4: Detailed Plan Writing

## Task Organization Principles

Plans should organize work into **phases grouped by subsystem** to enable parallel execution.

### Grouping Strategy

During execution, tasks are **grouped by subsystem** to share agent context. Structure your plan to make grouping clear:

- Tasks under the same phase heading touching the same subsystem → run in one agent
- Phases touching different subsystems → can run in parallel
- Max 3-4 tasks per phase (split larger sections)

Example structure:
```markdown
## Phase 1: Authentication (no dependencies)
### Task 1.1: Add login
### Task 1.2: Add logout

## Phase 2: Billing (depends on Phase 1)
### Task 2.1: Add billing API
### Task 2.2: Add webhooks

## Phase 3: Integration (depends on Phases 1 & 2)
### Task 3.1: Wire auth + billing
```

### Task Sizing

A task includes **everything** to complete one logical unit:
- Implementation + tests + types + exports
- All steps a single agent should do together

**Right-sized:** "Add user authentication" - one agent does model, service, tests, types
**Wrong:** Separate tasks for model, service, tests - these should be one task

**Bundle trivial items:** Group small related changes (add export, update config, rename) into one task.

### Context Loading

Each phase should specify which files need to be read before starting work:

```markdown
## Phase 1: Authentication

### Context
Before starting, read these files:
- `src/auth/` - existing authentication code
- `tests/auth/` - existing test patterns
- `src/config.ts` - configuration structure
```

This ensures agents have the necessary context loaded before making changes.

After structure approval:

1. **Write the plan** to `plan/future-plans/YYYY-MM-DD-<feature-name>.md`
   - Format: `YYYY-MM-DD-<feature-name>.md` where:
     - YYYY-MM-DD is today's date
     - feature-name is a brief kebab-case description
     - Optional: Include ticket reference like `YYYY-MM-DD-ENG-XXXX-description.md`
   - Examples:
     - `plan/future-plans/2025-01-08-parent-child-tracking.md`
     - With ticket: `plan/future-plans/2025-01-08-ENG-1478-parent-child-tracking.md`
2. **Use this template structure**:

### Standard Template (Single File)

Use this for plans under 400 lines:

````markdown
# [Feature Name] Implementation Plan

> **Status:** DRAFT | APPROVED | IN_PROGRESS | COMPLETED

## Table of Contents

- [Overview](#overview)
- [Current State Analysis](#current-state-analysis)
- [Desired End State](#desired-end-state)
- [What We're NOT Doing](#what-were-not-doing)
- [Implementation Approach](#implementation-approach)
- [Dependencies](#dependencies)
- [Phase 1: Descriptive Name](#phase-1-descriptive-name)
- [Phase 2: Descriptive Name](#phase-2-descriptive-name)
- [Testing Strategy](#testing-strategy)
- [References](#references)

## Overview

[Brief 2-3 paragraph description of what we're implementing and why]

## Current State Analysis

[What exists now, what's missing, key constraints discovered]

### Key Discoveries:
- [Important finding with file:line reference]
- [Pattern to follow]
- [Constraint to work within]

## Desired End State

[A Specification of the desired end state after this plan is complete]

**Success Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**How to Verify:**
- [Specific commands or steps to verify completion]

## What We're NOT Doing

[Explicitly list out-of-scope items to prevent scope creep]

## Implementation Approach

[High-level strategy and reasoning]

## Dependencies

**Execution Order:**

1. Phase 1 (no dependencies)
2. Phase 2 (depends on Phase 1)
3. Phase 3 (depends on Phases 1 & 2)

**Dependency Graph:**

```
Phase 1 (Authentication)
  ├─> Phase 2 (Billing - needs auth)
  └─> Phase 3 (Integration - needs both)
```

**Parallelization:**
- Phases 1 and 4 can run in parallel (independent subsystems)
- Phase 2 must wait for Phase 1
- Phase 3 must wait for Phases 1 and 2

---

## Phase 1: [Descriptive Name]

### Overview
[What this phase accomplishes]

### Context
Before starting, read these files:
- `src/relevant/file.ts` - [why this file is relevant]
- `tests/relevant/` - [existing test patterns]

### Dependencies
**Depends on:** None
**Required by:** Phase 2, Phase 3

### Changes Required

#### 1.1: [Component/File Group]
**File:** `path/to/file.ext`

**Changes:**
[Summary of changes]

```[language]
// Specific code to add/modify
```

**Rationale:** [Why this change is needed]

#### 1.2: [Another Component]
**File:** `path/to/another.ext`

**Changes:**
[Summary of changes]

### Success Criteria

#### Automated Verification:
- [ ] Migration applies cleanly: `make migrate`
- [ ] Unit tests pass: `make test-component`
- [ ] Type checking passes: `npm run typecheck`
- [ ] Linting passes: `make lint`
- [ ] Integration tests pass: `make test-integration`

#### Manual Verification:
- [ ] Feature works as expected when tested via UI
- [ ] Performance is acceptable under load
- [ ] Edge case handling verified manually
- [ ] No regressions in related features

**Verify:** After completing automated verification, pause for manual confirmation before proceeding.

---

## Phase 2: [Descriptive Name]

### Overview
[What this phase accomplishes]

### Context
Before starting, read these files:
- [Files to read]

### Dependencies
**Depends on:** Phase 1
**Required by:** Phase 3

### Changes Required

[Similar structure as Phase 1...]

### Success Criteria

#### Automated Verification:
[Automated checks...]

#### Manual Verification:
[Manual testing steps...]

---

## Testing Strategy

### Unit Tests:
- [What to test]
- [Key edge cases]

### Integration Tests:
- [End-to-end scenarios]

### Manual Testing Steps:
1. [Specific step to verify feature]
2. [Another verification step]
3. [Edge case to test manually]

## Performance Considerations

[Any performance implications or optimizations needed]

## Migration Notes

[If applicable, how to handle existing data/systems]

## References

- Original ticket: `[path/to/ticket.md]` (if applicable)
- Related research: `[path/to/research.md]` (if applicable)
- Similar implementation: `[file:line]`
- Dependencies: `[external libraries or services]`
````

### Large Plan Template (Multi-File)

For plans over 400 lines, split into separate files in a directory:

**Directory Structure:**
```
plan/future-plans/YYYY-MM-DD-feature-name/
├── README.md                    # Overview, dependencies, checklist
├── 01-authentication.md         # First phase
├── 02-billing.md                # Second phase
└── 03-integration.md            # Third phase
```

**Main README.md:**
````markdown
# [Feature Name] Implementation Plan

> **Status:** DRAFT | APPROVED | IN_PROGRESS | COMPLETED

## Table of Contents

- [Overview](#overview)
- [Dependencies](#dependencies)
- [Task Checklist](#task-checklist)
- [Phase Files](#phase-files)

## Overview

[Brief 2-3 paragraph summary of what we're building and why]

## Current State Analysis

[What exists now, what's missing, key constraints]

## Desired End State

[Specification of desired end state]

**Success Criteria:**
- [ ] Overall criterion 1
- [ ] Overall criterion 2

## What We're NOT Doing

[Out-of-scope items]

## Dependencies

**Execution Order:**

1. [Phase 1: Authentication](./01-authentication.md) (no dependencies)
2. [Phase 2: Billing](./02-billing.md) (depends on Phase 1)
3. [Phase 3: Integration](./03-integration.md) (depends on Phases 1 & 2)

**Dependency Graph:**

```
01-authentication.md
  ├─> 02-billing.md
  └─> 03-integration.md
```

**Parallelization:**
- Phases 1 and 4 can run in parallel (independent subsystems)
- Phase 2 must wait for Phase 1

## Task Checklist

- [ ] [Phase 1: Authentication](./01-authentication.md)
- [ ] [Phase 2: Billing](./02-billing.md)
- [ ] [Phase 3: Integration](./03-integration.md)

## Phase Files

1. [Authentication](./01-authentication.md)
2. [Billing](./02-billing.md)
3. [Integration](./03-integration.md)

## References

[Links to tickets, research, etc.]
````

**Individual Phase File (e.g., 01-authentication.md):**
````markdown
# Phase 1: Authentication

← [Back to Main Plan](./README.md)

## Table of Contents

- [Overview](#overview)
- [Context](#context)
- [Dependencies](#dependencies)
- [Changes Required](#changes-required)
- [Success Criteria](#success-criteria)

## Overview

[Brief description of this phase]

## Context

Before starting, read these files:
- `src/auth/` - existing authentication code
- `tests/auth/` - existing test patterns

## Dependencies

**Depends on:** None

**Required by:**
- [Phase 2: Billing](./02-billing.md)
- [Phase 3: Integration](./03-integration.md)

## Changes Required

### 1.1: Add Login Logic
**File:** `src/auth/login.ts`

**Changes:**
[Detailed changes...]

### 1.2: Add Tests
**File:** `tests/auth/login.test.ts`

**Changes:**
[Test implementation...]

## Success Criteria

### Automated Verification:
- [ ] Tests pass: `npm test -- tests/auth/`
- [ ] Type check passes: `npm run typecheck`

### Manual Verification:
- [ ] Login flow works in UI
- [ ] Error handling is user-friendly

---

← [Back to Main Plan](./README.md)
````

### Step 5: Present and Review

1. **Present the draft plan location**:
   ```
   I've created the initial implementation plan at:
   `plan/future-plans/YYYY-MM-DD-<feature-name>.md`

   Please review it and let me know:
   - Are the phases properly scoped and grouped by subsystem?
   - Can any phases be parallelized?
   - Are the success criteria specific enough (both automated and manual)?
   - Is the context loading clear for each phase?
   - Any technical details that need adjustment?
   - Missing edge cases or considerations?
   ```

2. **Iterate based on feedback** - be ready to:
   - Add missing phases
   - Adjust task grouping and parallelization
   - Clarify success criteria (both automated and manual)
   - Add/remove scope items
   - Refine context loading sections

3. **Continue refining** until the user is satisfied

## Important Guidelines

1. **Be Skeptical**:
   - Question vague requirements
   - Identify potential issues early
   - Ask "why" and "what about"
   - Don't assume - verify with code

2. **Be Interactive**:
   - Don't write the full plan in one shot
   - Get buy-in at each major step
   - Allow course corrections
   - Work collaboratively

3. **Be Thorough**:
   - Read all context files COMPLETELY before planning
   - Research actual code patterns using parallel sub-tasks
   - Include specific file paths and line numbers
   - Write measurable success criteria with clear automated vs manual distinction
   - Automated steps should use `make` whenever possible
   - Identify subsystem boundaries for task grouping and parallelization
   - Document context loading needs for each phase
   - Bundle trivial changes together (don't create separate tasks for small related changes)

4. **Be Practical**:
   - Focus on incremental, testable changes
   - Consider migration and rollback
   - Think about edge cases
   - Include "what we're NOT doing"

5. **Track Progress**:
   - Use TodoWrite to track planning tasks
   - Update todos as you complete research
   - Mark planning tasks complete when done

6. **No Open Questions in Final Plan**:
   - If you encounter open questions during planning, STOP
   - Research or ask for clarification immediately
   - Do NOT write the plan with unresolved questions
   - The implementation plan must be complete and actionable
   - Every decision must be made before finalizing the plan

## Success Criteria Guidelines

**Always separate success criteria into two categories:**

1. **Automated Verification** (can be run by execution agents):
   - Commands that can be run: `make test`, `npm run lint`, etc.
   - Specific files that should exist
   - Code compilation/type checking
   - Automated test suites

2. **Manual Verification** (requires human testing):
   - UI/UX functionality
   - Performance under real conditions
   - Edge cases that are hard to automate
   - User acceptance criteria

**Format example:**
```markdown
### Success Criteria:

#### Automated Verification:
- [ ] Database migration runs successfully: `make migrate`
- [ ] All unit tests pass: `go test ./...`
- [ ] No linting errors: `golangci-lint run`
- [ ] API endpoint returns 200: `curl localhost:8080/api/new-endpoint`

#### Manual Verification:
- [ ] New feature appears correctly in the UI
- [ ] Performance is acceptable with 1000+ items
- [ ] Error messages are user-friendly
- [ ] Feature works correctly on mobile devices
```

## Planning Rules

When creating plans, follow these rules:

1. **Table of contents required**: Every plan must start with a linked table of contents
2. **Document dependencies**: Every plan must have a Dependencies section showing:
   - Execution order (which phases must run first)
   - Dependency graph (which phases depend on which other phases)
   - Parallelization opportunities (which phases can run simultaneously)
3. **Phase dependencies**: Each phase must specify what it depends on and what depends on it
4. **Explicit paths**: Use exact file paths - say "create `src/utils/helpers.ts`" not "create a utility"
5. **Context per phase**: List files to read before starting each phase
6. **Verify every phase**: End with both automated AND manual success criteria
7. **One agent per task**: All steps within a task are handled by the same agent
8. **Split large plans**: Plans over 400 lines → split into multiple files in a directory with bidirectional links
9. **Status tracking**: Include status badge at top (DRAFT/APPROVED/IN_PROGRESS/COMPLETED)
10. **No open questions**: Resolve all questions before finalizing plan - research or ask for clarification immediately
11. **Bundle trivial changes**: Group small related changes (add export, update config, rename) into one task
12. **Task grouping**: Group tasks by subsystem to enable parallel execution and context sharing

## Common Patterns

### For Database Changes:
- Start with schema/migration
- Add store methods
- Update business logic
- Expose via API
- Update clients

### For New Features:
- Research existing patterns first
- Start with data model
- Build backend logic
- Add API endpoints
- Implement UI last

### For Refactoring:
- Document current behavior
- Plan incremental changes
- Maintain backwards compatibility
- Include migration strategy

## Sub-task Spawning Best Practices

When spawning research sub-tasks:

1. **Spawn multiple tasks in parallel** for efficiency
2. **Each task should be focused** on a specific area
3. **Provide detailed instructions** including:
   - Exactly what to search for
   - Which directories to focus on
   - What information to extract
   - Expected output format
4. **Be EXTREMELY specific about directories**:
   - Use exact directory paths from the ticket or task description
   - Don't use generic terms - be specific about which component/module
   - Include the full path context in your prompts
   - Verify directory names match the actual codebase structure
5. **Specify read-only tools** to use
6. **Request specific file:line references** in responses
7. **Wait for all tasks to complete** before synthesizing
8. **Verify sub-task results**:
   - If a sub-task returns unexpected results, spawn follow-up tasks
   - Cross-check findings against the actual codebase
   - Don't accept results that seem incorrect

Example of spawning multiple tasks:
```python
# Spawn these tasks concurrently:
tasks = [
    Task("Research database schema", db_research_prompt),
    Task("Find API patterns", api_research_prompt),
    Task("Investigate UI components", ui_research_prompt),
    Task("Check test patterns", test_research_prompt)
]
```

## Example Interaction Flow

```
User: /create_plan
Assistant: I'll help you create a detailed implementation plan...

User: We need to add user authentication. See docs/tickets/auth-feature.md
Assistant: Let me read that ticket file completely first...

[Reads file fully]

Based on the ticket, I understand we need to implement user authentication with login/logout functionality. Before I start planning, I have some questions...

[Interactive process continues...]
```
