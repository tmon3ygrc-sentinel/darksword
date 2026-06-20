#!/usr/bin/env python3
"""
READ-ONLY: option cardinality per property in the CPE Tracker.

Counts how many options each select / multi_select property enumerates.
Cardinality is ruler-independent, so it pinpoints the real bloat without
depending on byte-size serialization quirks.

  notion.databases.retrieve(DATABASE_ID)   <-- pure GET, no writes

Run in your venv:
  C:\\Work\\GRC\\.venv\\Scripts\\python.exe C:\\Work\\GRC\\darksword\\backups\\diag_option_cardinality.py

Safe to delete afterward.
"""
import os, json
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(r"C:\Work\GRC\darksword\.env")
tok = os.getenv("NOTION_TOKEN"); db = os.getenv("DATABASE_ID")
if not tok or not db:
    raise SystemExit("Missing NOTION_TOKEN / DATABASE_ID in .env")

notion = Client(auth=tok)
props = notion.databases.retrieve(database_id=db)["properties"]   # READ-ONLY

rows = []
for name, c in props.items():
    t = c["type"]
    if t in ("select", "multi_select", "status"):
        opts = c[t].get("options", [])
        rows.append((len(opts), t, name, c["id"]))

rows.sort(reverse=True)
print(f"{'OPTIONS':>8}  {'TYPE':<13} NAME (id)")
print("-" * 60)
for n, t, name, pid in rows:
    flag = "  <-- high cardinality" if n > 300 else ""
    print(f"{n:>8}  {t:<13} {name!r} (id={pid}){flag}")

print(f"\ntotal option objects across all enum properties: {sum(r[0] for r in rows):,}")
print("Rule of thumb: a 'select/multi_select' meant as an enum should be")
print("low-cardinality (tens). Hundreds+ means freeform values are leaking")
print("into an enum field -> convert to rich_text AND fix the source that emits them.")
