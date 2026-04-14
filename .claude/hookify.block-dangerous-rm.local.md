---
name: block-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-rf|rm\s+--no-preserve-root
action: block
---

🚫 **Dangerous rm command blocked!**

You're attempting to recursively and forcefully delete files. This operation is destructive and cannot be undone.

**If you really need to do this:**
1. Double-check the target path
2. Consider using `rm -ri` (interactive) instead
3. Or run the command manually outside of Claude Code

**Blocked pattern:** `rm -rf` or `rm --no-preserve-root`
