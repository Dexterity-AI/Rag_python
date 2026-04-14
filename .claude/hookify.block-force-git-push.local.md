---
name: block-force-git-push
enabled: true
event: bash
pattern: git\s+push\s+--force|git\s+push\s+-f\b
action: block
---

🚫 **Force push blocked!**

Force pushing can overwrite other people's work and break the shared history. This is a dangerous operation.

**Alternatives:**
- Use `git push --force-with-lease` (safer - fails if remote has new commits)
- Coordinate with your team before force pushing
- Consider using `git revert` to undo changes instead

**If you absolutely must force push:**
Run the command manually outside of Claude Code after confirming with your team.
