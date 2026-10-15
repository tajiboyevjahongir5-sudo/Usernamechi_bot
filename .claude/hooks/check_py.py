"""PostToolUse: tahrirlangan .py faylni py_compile bilan tekshiradi."""
import json, py_compile, sys

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path", "")
if not path.endswith(".py"):
    sys.exit(0)
try:
    py_compile.compile(path, doraise=True)
except py_compile.PyCompileError as e:
    print(f"Sintaksis xatosi: {e.msg}", file=sys.stderr)
    sys.exit(2)  # Claude'ga xato qaytariladi, u darhol tuzatadi
