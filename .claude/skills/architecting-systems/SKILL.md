---
name: architecting-systems
description: Designs scalable system architectures and technical documents. Use when planning features, evaluating tradeoffs, documenting decisions, or analyzing complexity.
---

# Architecting Systems

**Core principle:** Build the best possible system, not validate poor ideas. Challenge assumptions, propose better approaches.

## Before You Design

**Never start until you understand:**
- The problem and who experiences it
- Constraints (technical, business, timeline)
- Success criteria and how they'll be measured
- Scope and non-goals

If requirements are incomplete or assumptions seem wrong, call it out explicitly.

## Convention Over Invention

Default to battle-tested solutions. Use established patterns, common conventions, and existing libraries rather than reinventing.

## Workflow

### 1. Understand

Ask questions until you have clarity on problem, constraints, success criteria, and user workflows. Challenge assumptions.

### 2. Design

- **Research first** - Search codebase for patterns, research established approaches
- **Create architecture** - Use Mermaid diagrams (`Skill(ce:visualizing-with-mermaid)`)
- **Plan for failure** - Identify failure modes and mitigations
- **Document tradeoffs** - Why this approach over alternatives

### 3. Document

**Structure:** TL;DR → Problem & Goals → Architecture → Key Decisions → Operations → Success Metrics

- Start with 2-3 sentence TL;DR
- Focus on decisions (why this over alternatives)
- Keep scannable with headers and diagrams
- Aim for 6-8 pages max

## Handling Gaps

| Problem | Response |
|---------|----------|
| Incomplete requirements | List specific gaps, request clarification |
| Unrealistic constraints | Challenge with data/examples |
| Unclear scope | Propose 2-3 alternatives with tradeoffs |
| Missing success metrics | Suggest specific, measurable criteria |

## Core Responsibilities

- Architecture diagrams with Mermaid
- Scalable designs using proven patterns
- Failure mode identification
- Measurable success criteria
- Tradeoff documentation
- Push back on scope creep
