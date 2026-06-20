#!/usr/bin/env python3
"""
GUARDED backfill of a rich_text property from a CSV, matched by record_id.

DEFAULT IS SAFE: without --execute it does a DRY RUN (read-only) and reports
how many rows it would update, with a sample. Idempotent — re-running is safe.

Usage (run in venv, after fix_recreate_property.py recreated the property):
  # dry run
  python fix_backfill_tags.py --csv <fresh_export.csv> --field tags
  # write
  python fix_backfill_tags.py --csv <fresh_export.csv> --field tags --execute

Assumes each Notion page carries a 'record_id' rich_text property (it does,
per the pipeline schema) used as the join key.
Never edits .env, never prints the token.
"""
import os, sys, csv, json, argparse
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(r"C:\Work\GRC\darksword\.env")
TOK = os.getenv("NOTION_TOKEN"); DB = os.getenv("DATABASE_ID")
if not TOK or not DB:
    sys.exit("Missing NOTION_TOKEN / DATABASE_ID in .env")
notion = Client(auth=TOK)

ap = argparse.ArgumentParser()
ap.add_argument("--csv", required=True)
ap.add_argument("--field", default="tags")
ap.add_argument("--key-col", default="record_id")
ap.add_argument("--key-prop", default="record_id", help="Notion property holding record_id")
ap.add_argument("--execute", action="store_true")
args = ap.parse_args()

if not os.path.isfile(args.csv):
    sys.exit(f"CSV not found: {args.csv}")

def plain(prop):
    """Extract plain text from a title or rich_text property value."""
    arr = prop.get("rich_text") or prop.get("title") or []
    return "".join(x.get("plain_text", "") for x in arr).strip()

# 1) Build record_id -> page_id map (paginated, READ-ONLY)
id_to_page, cursor = {}, None
while True:
    resp = notion.databases.query(database_id=DB, start_cursor=cursor, page_size=100) \
           if cursor else notion.databases.query(database_id=DB, page_size=100)
    for pg in resp["results"]:
        kp = pg["properties"].get(args.key_prop)
        if kp:
            rid = plain(kp)
            if rid:
                id_to_page[rid] = pg["id"]
    if not resp.get("has_more"):
        break
    cursor = resp["next_cursor"]
print(f"pages indexed by {args.key_prop}: {len(id_to_page):,}")

# 2) Read CSV, plan updates
with open(args.csv, newline="", encoding="utf-8-sig") as fh:
    rows = list(csv.DictReader(fh))
if args.key_col not in rows[0] or args.field not in rows[0]:
    sys.exit(f"CSV missing required columns {args.key_col!r}/{args.field!r}. "
             f"Found: {list(rows[0].keys())[:6]}…")

plan, missing = [], []
for r in rows:
    rid = (r.get(args.key_col) or "").strip()
    val = (r.get(args.field) or "").strip()
    if not rid:
        continue
    pid = id_to_page.get(rid)
    if not pid:
        missing.append(rid); continue
    plan.append((pid, rid, val))

print(f"CSV rows: {len(rows):,} | matched to pages: {len(plan):,} | "
      f"unmatched record_ids: {len(missing)}")
if missing:
    print("  unmatched (first 5):", missing[:5])
print("  sample update:", (plan[0][1], plan[0][2][:80]) if plan else "(none)")

if not args.execute:
    print("\n[DRY RUN] no writes. Re-run with --execute to backfill.")
    sys.exit(0)

# 3) Execute updates (idempotent)
ok = 0
for pid, rid, val in plan:
    notion.pages.update(
        page_id=pid,
        properties={args.field: {"rich_text": [{"text": {"content": val[:2000]}}]}},
    )
    ok += 1
    if ok % 25 == 0:
        print(f"  …{ok}/{len(plan)}")
print(f"backfilled {ok}/{len(plan)} pages.")
