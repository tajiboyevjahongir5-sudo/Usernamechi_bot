import sys
search = "_get_fast_client"
with open("main.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if search in line:
            print(f"{i}: {line.strip()}")
