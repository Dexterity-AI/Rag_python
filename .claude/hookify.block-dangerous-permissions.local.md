---
name: block-dangerous-permissions
enabled: true
event: bash
pattern: chmod\s+777|chmod\s+a\+rwx|chown\s+root
action: block
---

🚫 **Dangerous permission change blocked!**

Setting 777 permissions or changing ownership to root creates security vulnerabilities.

**Why this is dangerous:**
- `777` gives everyone read, write, and execute permissions
- Any user/process can modify or execute the file
- Violates principle of least privilege

**Better alternatives:**
- Use `755` for executables (owner: all, group/others: read+execute)
- Use `644` for files (owner: write, group/others: read only)
- Use groups instead of 777 for shared access

**If you really need this:**
Run the command manually after confirming the security implications.
