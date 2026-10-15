"""PreToolUse(Bash): master'ga push va force push'ni bloklaydi."""
import json, re, sys

cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command", "")
# Faqat `git push ...` bo'laklarini tekshiramiz (commit xabaridagi so'zlar hisobga olinmaydi)
for part in re.split(r"&&|\|\||;|\||\n", cmd):
    m = re.search(r"\bgit\s+push\b(.*)", part)
    if not m:
        continue
    args = m.group(1)
    if re.search(r"\bmaster\b", args):
        print("Bloklandi: deploy 'main'dan, 'master'ga push qilinmaydi.", file=sys.stderr)
        sys.exit(2)
    if re.search(r"(--force\b|--force-with-lease\b|(^|\s)-f\b|\s\+\S)", args):
        print("Bloklandi: force push faqat foydalanuvchi ruxsati bilan.", file=sys.stderr)
        sys.exit(2)
