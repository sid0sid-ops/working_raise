import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
patterns = [
    re.compile(r"3090|4090", re.IGNORECASE),
    re.compile(r"64\s*GB|24\s*GB", re.IGNORECASE),
    re.compile(r"Siddharth|Tripathi", re.IGNORECASE),
    re.compile(r"C:\\Users\\[^\s\'\"]+", re.IGNORECASE),
]

matches = []
for root, dirs, files in os.walk(base_dir):
    if any(p in root for p in [".git", ".chromadb", "__pycache__", ".cache", ".pytest_cache", ".env"]):
        continue
    for f in files:
        if f.endswith((".py", ".ps1", ".sh", ".json", ".yml", ".yaml", ".md", ".txt")) and f != ".env":
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_no, line in enumerate(fp, 1):
                        for p in patterns:
                            if p.search(line):
                                matches.append((os.path.relpath(path, base_dir), line_no, line.strip()))
                                break
            except Exception:
                pass

print(f"Total matches found: {len(matches)}")
for rel, line_no, text in matches:
    print(f"{rel}:{line_no}: {text[:130]}")
