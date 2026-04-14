---
name: block-privilege-escalation
enabled: true
event: bash
pattern: sudo\s+|su\s+-\s*$
action: block
---

🚫 **Privilege escalation blocked!**

Running commands with sudo or switching to root can make system-wide changes and is potentially dangerous.

**Security risks:**
- Can modify system files accidentally
- May run untrusted code with elevated privileges
- Actions may not be reversible

**If you really need elevated privileges:**
Run the command manually after understanding exactly what it does.
