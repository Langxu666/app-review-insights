import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.openai_client import _fix_unescaped_strings, _fix_json_trailing_commas, _fix_truncated_json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

with open(os.path.join(DATA_DIR, "debug_raw_findings_response.txt"), "r", encoding="utf-8") as f:
    response = f.read()

print("Original length:", len(response))

# Step 1: fix unescaped strings
fixed = _fix_unescaped_strings(response)
print("After unescape fix length:", len(fixed))
try:
    json.loads(fixed)
    print("Step 1: SUCCESS")
except json.JSONDecodeError as e:
    print("Step 1: FAILED at pos", e.pos, ":", e.msg)
    start = max(0, e.pos - 40)
    end = min(len(fixed), e.pos + 40)
    print("  Context:", repr(fixed[start:end]))

# Step 2: fix trailing commas
fixed2 = _fix_json_trailing_commas(fixed)
try:
    json.loads(fixed2)
    print("Step 2: SUCCESS")
except json.JSONDecodeError as e:
    print("Step 2: FAILED at pos", e.pos, ":", e.msg)
    start = max(0, e.pos - 40)
    end = min(len(fixed2), e.pos + 40)
    print("  Context:", repr(fixed2[start:end]))

# Step 3: fix truncated
fixed3 = _fix_truncated_json(fixed2)
try:
    json.loads(fixed3)
    print("Step 3: SUCCESS")
except json.JSONDecodeError as e:
    print("Step 3: FAILED at pos", e.pos, ":", e.msg)
    start = max(0, e.pos - 40)
    end = min(len(fixed3), e.pos + 40)
    print("  Context:", repr(fixed3[start:end]))