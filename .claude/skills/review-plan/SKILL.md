---
name: review-plan
description: Review implementation plans for quality and executability
---

# Review Plan

## When to Use

Invoke this skill when you need to:
- Review an implementation plan before execution
- Assess plan quality, completeness, and clarity
- Identify potential blockers or ambiguities in plans
- Get structured feedback on plan improvements
- Validate that a plan is ready for agent execution

## What Happens

This skill **delegates to the /review_plan command**, which provides:
- Comprehensive analysis across 5 quality dimensions
- Executability probability score (0-100%)
- Detailed findings with specific section references
- Prioritized recommendations for improvements
- Phase-by-phase analysis
- Testing strategy assessment
- Review saved to `*.REVIEW.md` file

The command will:
1. Load the specified plan file(s) completely
2. Spawn a specialized review agent with opus model
3. Analyze plan for accuracy, consistency, clarity, completeness, executability
4. Generate structured review report with scoring
5. Save review to same directory as original plan
6. **Never** modify the original plan file

## Invocation

To use this skill:

```bash
# Review a specific plan file
/review-plan plan/2026-01-23-feature-name.md

# Review a multi-file plan (directory)
/review-plan plan/2026-01-23-feature-name/

# Interactive mode (prompts for plan path)
/review-plan
```

## Output Location

Review saved to:
- Single-file plan: `plan/YYYY-MM-DD-feature-name.REVIEW.md`
- Multi-file plan: `plan/YYYY-MM-DD-feature-name/REVIEW.md`

## Review Criteria

Plans are evaluated on:
1. **Accuracy** (20 pts) - Technical correctness, valid paths, correct understanding
2. **Consistency** (15 pts) - Internal consistency, naming conventions, patterns
3. **Clarity** (20 pts) - Unambiguous instructions, clear success criteria
4. **Completeness** (25 pts) - All steps included, no missing context, edge cases
5. **Executability** (20 pts) - Can agents execute without human intervention?

## Quick Examples

```bash
# Review a plan before execution
/review-plan plan/2026-01-23-add-authentication.md

# Review a complex multi-file plan
/review-plan plan/2026-01-23-database-migration/

# Interactive review
/review-plan
```

The agent will provide detailed analysis and save a review report.
