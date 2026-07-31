import sys
search = sys.argv[1]
with open("main.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if search in line:
            print(f"{i}: {line.strip()}")
