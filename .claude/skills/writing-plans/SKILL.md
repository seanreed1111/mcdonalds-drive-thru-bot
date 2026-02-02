---
name: writing-plans
description: Create implementation plans through interactive research and discovery. Routes to /create_plan command.
---

# Writing Plans

## When to Use

Invoke this skill when you need to:
- Create implementation plans for new features or tasks
- Plan complex refactoring or architectural changes
- Document step-by-step approaches for multi-phase work
- Organize work into executable tasks with clear dependencies
- Plan features that span multiple subsystems or files

## What Happens

This skill **delegates to the /create_plan command**, which provides:
- Interactive research process with sub-agent analysis
- Comprehensive codebase investigation before planning
- Iterative plan development with user collaboration
- Structured templates with dependencies and success criteria
- Plans saved to `plan/YYYY-MM-DD-<feature-name>.md`

The command will:
1. Gather context through parallel research tasks
2. Analyze the codebase to understand current state
3. Collaborate with you on approach and structure
4. Create a detailed, actionable implementation plan
5. Iterate based on your feedback until approved

## Invocation

To use this skill:

```
/writing-plans
```

Or with context:

```
/writing-plans <task description>
```

This will automatically invoke the `/create_plan` command with the appropriate parameters.

## Output Location

Plans are saved to:
- Simple plans: `plan/YYYY-MM-DD-<feature-name>.md`
- Large plans (>400 lines): `plan/YYYY-MM-DD-<feature-name>/` directory with multiple files

## Quick Examples

```bash
# Create a plan for a new feature
/writing-plans Add user authentication system

# Create a plan from existing ticket
/writing-plans See ticket at docs/tickets/eng-123.md

# Start interactive planning session
/writing-plans
```

The command will guide you through the planning process step by step.
