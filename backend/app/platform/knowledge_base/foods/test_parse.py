"""Test script to debug parsing."""
from pathlib import Path

f = Path('app/platform/knowledge_base/foods/exchange_info.txt')
content = f.read_text(encoding='utf-8')
lines = content.splitlines()

print(f"Total lines: {len(lines)}")
print("\nFirst 15 lines:")
for i in range(min(15, len(lines))):
    print(f"{i+1:3d}: {repr(lines[i])}")
    if i >= 9:
        parts = lines[i].split('\t')
        print(f"      Parts ({len(parts)}): {parts[:5]}")

