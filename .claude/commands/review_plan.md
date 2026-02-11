---
description: Review implementation plans for quality, completeness, and executability
model: opus

---

# Plan Review

You are tasked with reviewing implementation plans to assess their quality, completeness, inconsistencies, ambiguity, and executability. Your goal is to provide constructive detailed feedback that helps improve plans before execution. The goal: any agent should be able to execute the plan without further questoins to the user or any further user input. 

## Initial Response

When this command is invoked:

1. **Check if a plan path was provided**:
   - If a file path or directory path was provided as a parameter, immediately proceed to load it
   - If no parameter provided, ask the user for the plan location

2. **If no parameters provided**, respond with:
```
I'll help you review an implementation plan. Please provide the path to the plan:

1. Single-file plan: `plan/YYYY-MM-DD-feature-name.md`
2. Multi-file plan directory: `plan/YYYY-MM-DD-feature-name/`

Example: `/review_plan plan/2026-01-23-user-auth.md`
```

Then wait for the user's input.

## Process Steps

### Step 1: Plan Loading

1. **Identify plan type**:
   - Check if path is a directory (multi-file plan) or single file
   - For directories, start with `README.md` as the main plan file
   - For single files, verify the file exists and is a markdown file

2. **Read plan completely**:
   - Use Read tool to load the entire plan file(s)
   - For multi-file plans, read ALL phase files in the directory
   - NEVER use limit/offset - read complete files
   - For multi-file plans:
     - Read `README.md` first as the main plan
     - Use Glob to find all `.md` files in the directory
     - Read each phase file completely
     - Combine all content for comprehensive review

3. **Verify plan structure**:
   - Confirm it follows expected plan template
   - Identify plan phases, dependencies, success criteria
   - Note any non-standard structure

4. **Handle errors gracefully**:
   - If path doesn't exist, provide helpful error message
   - If directory lacks README.md, look for main plan file
   - If file is not markdown, warn user and ask for confirmation

### Step 2: Spawn Review Agent

1. **Create detailed review prompt**:

Use the following template when spawning the review agent:

"""
You are a specialized plan review agent. Your task is to analyze the following implementation plan for quality, completeness, inconsistencies, ambiguity, and executability. The goal: any agent should be able to execute the plan without further questions to the user or any further user input whatsoever. 

## Review Guidelines

1. **Be Thorough**: Read the entire plan carefully, every section and phase
2. **Be Specific**: Reference exact sections, phases, and line numbers
3. **Be Constructive**: Explain WHY issues matter and HOW to fix them
4. **Be Objective**: Use the scoring rubric consistently and honestly
5. **Be Clear**: Prioritize issues as Critical/Major/Minor with clear reasoning

## Scoring Rubric

Evaluate across 5 dimensions (100 points total):

### 1. Accuracy (20 points)
- Technical correctness: 5 pts - Is the proposed technical approach sound?
- File path validity: 5 pts - Do all referenced files/paths exist or make sense?
- Codebase understanding: 5 pts - Does the plan show understanding of existing code?
- Dependency accuracy: 5 pts - Are dependencies correctly identified?

### 2. Consistency (15 points)
- Internal consistency: 5 pts - Are phases consistent with each other?
- Naming conventions: 5 pts - Are names consistent throughout?
- Pattern adherence: 5 pts - Does it follow existing codebase patterns?

### 3. Clarity (25 points)
- Instruction clarity: 7 pts - Are instructions clear and unambiguous?
- Success criteria clarity: 7 pts - Are success criteria specific and measurable?
- Minimal ambiguity: 11 pts - Is the plan explicit rather than implicit?

### 4. Completeness (25 points)
- All steps present: 11 pts - Are all necessary steps included? Agents should be able to follow the exact steps shown in plan and should be able to implement the plan without further user input or explanations. If not, there are steps missing that should be added.
- Context adequate: 6 pts - Is sufficient context provided?
- Edge cases covered: 6 pts - Are edge cases and error scenarios addressed?
- Testing comprehensive: 2 pts - Is the testing strategy thorough?

### 5. Executability (20 points)
- Agent-executable: 8 pts - Can agents execute without human intervention?
- Dependencies ordered: 6 pts - Are dependencies properly ordered?
- Success criteria verifiable: 6 pts - Can success be automatically verified?

**Total: 100 points**

### Executability Probability Scale

- **90-100**: Excellent - Ready for execution
- **75-89**: Good - Minor clarifications needed
- **60-74**: Fair - Significant improvements recommended
- **40-59**: Poor - Major revisions required
- **0-39**: Critical - Cannot execute without major rework

## Plan to Review

{PLAN_CONTENT}

## Your Task

1. Analyze the plan using the rubric above
2. Calculate scores for each dimension with clear justification
3. Calculate total executability score (0-100)
4. Identify critical blockers, major concerns, and minor issues
5. Provide specific, actionable recommendations with section references
6. Generate a review report following the template structure below

## Output Format

Return a complete review report in markdown format with these sections:

### Required Sections

1. **Title and Metadata**: Plan name, review date, plan location
2. **Executive Summary**: Overall score, assessment, recommendation
3. **Detailed Analysis**: Scores and findings for each of 5 dimensions
4. **Identified Pain Points**: Critical blockers, major concerns, minor issues
5. **Specific Recommendations**: High/medium/low priority with specific references
6. **Phase-by-Phase Analysis**: Assessment of each phase
7. **Testing Strategy Assessment**: Coverage and gaps
8. **Dependency Graph Validation**: Correctness and issues
9. **Summary of Changes Needed**: Checklist format
10. **Reviewer Notes**: Additional context

### Report Template

```markdown
# Plan Review: [Plan Name]

**Review Date:** YYYY-MM-DD
**Reviewer:** Claude Code Review Agent
**Plan Location:** `path/to/plan.md`

---

## Executive Summary

**Executability Score:** XX/100 - [Excellent/Good/Fair/Poor/Critical]

**Overall Assessment:**
[2-3 paragraph summary of plan quality, readiness for execution, and major concerns]

**Recommendation:**
- [ ] Ready for execution
- [ ] Ready with minor clarifications
- [ ] Requires improvements before execution
- [ ] Requires major revisions

---

## Detailed Analysis

### 1. Accuracy (XX/20)

**Score Breakdown:**
- Technical correctness: X/5
- File path validity: X/5
- Codebase understanding: X/5
- Dependency accuracy: X/5

**Findings:**
- ✅ Strength: [Specific example with section/line reference]
- ⚠️ Issue: [Specific problem with section/line reference]
- ❌ Critical: [Blocking issue with section/line reference]

**Suggestions:**
1. [Actionable suggestion with specific location]
2. [Actionable suggestion with specific location]

### 2. Consistency (XX/15)

[Same structure as above]

### 3. Clarity (XX/20)

[Same structure as above]

### 4. Completeness (XX/25)

[Same structure as above]

### 5. Executability (XX/20)

[Same structure as above]

---

## Identified Pain Points

### Critical Blockers
1. [Issue that prevents execution - with section reference]
2. [Another blocker]

### Major Concerns
1. [Issue that will cause problems - with section reference]
2. [Another concern]

### Minor Issues
1. [Small improvement opportunity - with section reference]
2. [Another minor issue]

---

## Specific Recommendations

### High Priority
1. **[Recommendation Title]**
   - Location: [Section/Phase reference]
   - Issue: [What's wrong]
   - Suggestion: [How to fix it]
   - Impact: [Why this matters]

### Medium Priority
[Same structure]

### Low Priority
[Same structure]

---

## Phase-by-Phase Analysis

### Phase 1: [Phase Name]
- **Score:** XX/25
- **Readiness:** [Ready/Needs Work/Blocked]
- **Key Issues:**
  - [Issue 1 with line/section reference]
  - [Issue 2 with line/section reference]
- **Dependencies:** [Properly defined? Any issues?]
- **Success Criteria:** [Clear and verifiable? Any gaps?]

### Phase 2: [Phase Name]
[Same structure for each phase]

---

## Testing Strategy Assessment

**Coverage:** [Excellent/Good/Fair/Poor]

**Unit Testing:**
- [Assessment of unit test plan]

**Integration Testing:**
- [Assessment of integration test plan]

**Manual Testing:**
- [Assessment of manual test steps]

**Gaps:**
- [Missing test scenarios]
- [Inadequate coverage areas]

---

## Dependency Graph Validation

**Graph Correctness:** [Valid/Has Issues]

**Analysis:**
- Execution order is: [clear/unclear/incorrect]
- Parallelization opportunities are: [well-identified/missing/incorrect]
- Blocking dependencies are: [properly documented/unclear/missing]

**Issues:**
- [Circular dependencies if any]
- [Missing dependencies]
- [Incorrect dependency ordering]

---

## Summary of Changes Needed

**Before execution, address:**

1. **Critical (Must Fix):**
   - [ ] [Critical change 1]
   - [ ] [Critical change 2]

2. **Important (Should Fix):**
   - [ ] [Important change 1]
   - [ ] [Important change 2]

3. **Optional (Nice to Have):**
   - [ ] [Optional improvement 1]
   - [ ] [Optional improvement 2]

---

## Reviewer Notes

[Any additional context, observations, or considerations for the plan author]

---

**Note:** This review is advisory only. No changes have been made to the original plan. All suggestions require explicit approval before implementation.
```

**IMPORTANT:**
- Do NOT modify the original plan file
- Do NOT implement suggested changes without explicit user permission
- This is a review only - be honest and thorough in your analysis
- Reference specific line numbers and sections
- Provide concrete, actionable suggestions
"""

2. **Spawn agent using Task tool**:
   - Use subagent_type: "general-purpose"
   - Provide model: "opus" for strong analytical reasoning
   - Include complete plan content in the prompt (replace {PLAN_CONTENT})
   - Request structured review output
   - Do NOT run in background - wait for completion

3. **Wait for agent completion**:
   - Agent will analyze plan across all dimensions
   - Agent will generate structured review with score
   - Agent will return complete review content in markdown format

### Step 3: Save Review Report

1. **Determine output path**:
   - Single-file plan: `<original-path-without-ext>.REVIEW.md`
     - Example: `plan/2026-01-23-feature.md` → `plan/2026-01-23-feature.REVIEW.md`
   - Multi-file plan: `<directory>/REVIEW.md`
     - Example: `plan/2026-01-23-feature/` → `plan/2026-01-23-feature/REVIEW.md`

2. **Validate review report structure**:
   Before saving, verify the review report contains:
   - [ ] Executive Summary with score
   - [ ] Detailed Analysis section (all 5 dimensions)
   - [ ] Identified Pain Points section
   - [ ] Specific Recommendations section
   - [ ] Phase-by-Phase Analysis section
   - [ ] Testing Strategy Assessment section
   - [ ] Dependency Graph Validation section
   - [ ] Summary of Changes Needed section

   If any critical section is missing, log a warning but proceed with saving.

3. **Write review file**:
   - Use Write tool to save review markdown
   - Preserve original plan files (no modifications to original plan)
   - Create parent directories if needed

4. **Extract key information for user summary**:
   - Overall score and rating (Excellent/Good/Fair/Poor/Critical)
   - Top 3 most critical findings
   - Overall recommendation

5. **Present results to user**:
   ```
   ✅ Plan review completed!

   Original plan: [original_plan_path]
   Review saved to: [review_path]

   Executability Score: [score]/100 - [rating]

   Key findings:
   - [finding_1]
   - [finding_2]
   - [finding_3]

   [recommendation_summary]

   See the full review for detailed analysis and suggestions.
   ```

## Important Guidelines

1. **Non-Destructive**:
   - NEVER modify the original plan file
   - NEVER implement suggested changes without explicit permission
   - Review is purely analytical

2. **Thorough**:
   - Read the entire plan completely
   - Reference specific sections and line numbers
   - Provide concrete examples

3. **Constructive**:
   - Focus on helping improve the plan
   - Explain WHY issues matter
   - Provide actionable suggestions

4. **Objective**:
   - Use the scoring rubric consistently
   - Be honest about issues
   - Don't inflate scores

5. **Clear**:
   - Make recommendations unambiguous
   - Prioritize issues (Critical/Major/Minor)
   - Provide specific line/section references

## Example Interaction Flow

```
User: /review_plan plan/2026-01-23-user-auth.md
Assistant: Let me review that plan for you...

[Reads plan completely]

I'm spawning a review agent to analyze this plan across all quality dimensions...

[Spawns agent, waits for completion]

✅ Plan review completed!

Original plan: plan/2026-01-23-user-auth.md
Review saved to: plan/2026-01-23-user-auth.REVIEW.md

Executability Score: 75/100 - Good

Key findings:
- Missing error handling strategy in Phase 2
- Success criteria for Phase 3 are not fully automated
- Dependency graph is clear and correct

See the full review for detailed analysis and suggestions.
```