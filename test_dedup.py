# test_dedup.py — throwaway verification, delete after
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from notion_logger_v7 import record_exists

# 1. KNOWN-GOOD: a record_id you can see in CPE Tracker right now
known_good = "simplycyber-ep1151-2026-06-11-01"
print(f"Known-good  → {record_exists(known_good)}  (expect True)")

# 2. KNOWN-BAD: garbage that can't exist
known_bad = "simplycyber-ep9999-0000-00-00-99"
print(f"Known-bad   → {record_exists(known_bad)}  (expect False)")

# 3. MALFORMED: placeholder values the guard should short-circuit
for bad in ("unknown", "", "n/a", "none"):
    result = record_exists(bad)
    status = "✅" if not result else "❌"
    print(f"Placeholder {bad!r:10} → {result}  (expect False) {status}")

# Verdict
