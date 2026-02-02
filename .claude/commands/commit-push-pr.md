---
allowed-tools: Bash(git checkout --branch:*), Bash(git add:*), Bash(git status:*), Bash(git push:*), Bash(git commit:*), Bash(gh pr create:*), Skill(changelog-generator)
description: Commit, push, and open a PR with changelog update
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`

## Your task

Based on the above changes:

### **CRITICAL: Prevent circular dependencies**
**Before doing ANYTHING else, check if CHANGELOG.md is the ONLY file with changes.**
- If CHANGELOG.md is the only modified file, SKIP Phase 2 entirely
- Only proceed to Phase 2 if there are code/feature changes beyond CHANGELOG.md
- This prevents infinite loops: code → changelog → changelog → changelog...

### Phase 1: Create PR (single message)
1. Create a new branch if on main
2. Create a single commit with an appropriate message
3. Push the branch to origin
4. Create a pull request using `gh pr create`
5. You have the capability to call multiple tools in a single response. You MUST do all of the above in a single message.

### Phase 2: Update changelog (conditional - see CRITICAL note above)
**ONLY if changes include files OTHER than CHANGELOG.md:**
6. Invoke the `changelog-generator` skill to update the CHANGELOG.md
7. Add, commit, and push the changelog updates with message: "Update CHANGELOG"

Do not use any other tools or do anything else beyond these steps.
