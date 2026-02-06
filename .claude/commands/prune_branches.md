---
description: Delete all local git branches except master and the current branch
---

# Prune Local Branches

Delete all local git branches except `master` and the currently checked-out branch.

## Process:

1. **Identify branches to delete:**
   - Run `git branch` to list all local branches
   - Determine the current branch (marked with `*`)
   - Exclude `master` and the current branch from deletion

2. **Present the plan:**
   - List the branches that will be deleted
   - List the branches that will be kept (master + current)
   - Ask: "I will delete [N] branches. Shall I proceed?"

3. **Execute upon confirmation:**
   - Delete each branch with `git branch -D <branch>`
   - Show `git branch -v` after completion to confirm

## Important:
- **NEVER delete `master`**
- **NEVER delete the current branch**
- Use `git branch -D` (force delete) since branches may not be fully merged
- If there are no branches to delete, inform the user and stop
