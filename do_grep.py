import os
with open("main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
with open("grep_out.txt", "w", encoding="utf-8") as out:
    for i, l in enumerate(lines):
        if "def get_admin_token" in l:
            out.write(f"{i+1}: {l.strip()}\n")
