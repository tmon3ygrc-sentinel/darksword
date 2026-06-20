#!/usr/bin/env python3
"""
GUARDED delete + recreate of a Notion property (orphaned-options fix).

DEFAULT IS SAFE: with no --execute it only INSPECTS (read-only) and prints
the exact payloads it WOULD send. Destructive actions require --execute AND
a typed --confirm match AND an existing --backup file.

Usage (run in venv, next session, per the runbook):
  # 1) inspect (read-only)
  python fix_recreate_property.py --field tags

  # 2) delete (destructive) — needs backup + typed confirm
  python fix_recreate_property.py --field tags --action delete \
      --backup <fresh_export.csv> --execute --confirm "DELETE tags"

  # 3) re-run diag_tags_schema.py and CONFIRM schema dropped before recreate

  # 4) recreate as fresh rich_text
  python fix_recreate_property.py --field tags --action recreate --execute

This script never edits .env and never prints the token.
"""
import os, sys, json, argparse
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(r"C:\Work\GRC\darksword\.env")
TOK = os.getenv("NOTION_TOKEN"); DB = os.getenv("DATABASE_ID")
if not TOK or not DB:
    sys.exit("Missing NOTION_TOKEN / DATABASE_ID in .env")
notion = Client(auth=TOK)

ap = argparse.ArgumentParser()
ap.add_argument("--field", required=True, help="property name, e.g. tags")
ap.add_argument("--action", choices=["inspect", "delete", "recreate"], default="inspect")
ap.add_argument("--execute", action="store_true", help="actually send writes")
ap.add_argument("--confirm", default="", help='must equal "DELETE <field>" for delete')
ap.add_argument("--backup", default="", help="path to a fresh, verified CSV export (required for delete)")
args = ap.parse_args()

props = notion.databases.retrieve(database_id=DB)["properties"]  # READ-ONLY
cur = props.get(args.field)
print(f"Field {args.field!r}: ", end="")
if cur:
    print(f"present | id={cur['id']} | type={cur['type']} | "
          f"api_bytes={len(json.dumps(cur,ensure_ascii=False).encode()):,}")
else:
    print("NOT present in schema")

if args.action == "inspect":
    print("\n[inspect] no writes. Payloads that delete/recreate WOULD send:")
    print("  delete   :", json.dumps({"properties": {args.field: None}}))
    print("  recreate :", json.dumps({"properties": {args.field: {"rich_text": {}}}}))
    sys.exit(0)

if args.action == "delete":
    if not cur:
        sys.exit(f"Refusing: {args.field!r} is not present — nothing to delete.")
    if not args.backup or not os.path.isfile(args.backup):
        sys.exit("Refusing delete: --backup must point to an existing fresh CSV export.")
    if args.confirm != f"DELETE {args.field}":
        sys.exit(f'Refusing delete: pass --confirm "DELETE {args.field}" to proceed.')
    payload = {"properties": {args.field: None}}
    if not args.execute:
        print("\n[DRY RUN] would PATCH:", json.dumps(payload)); sys.exit(0)
    print("\n[EXECUTE] deleting property…")
    notion.databases.update(database_id=DB, **payload)
    print("done. NOW re-run diag_tags_schema.py and confirm schema size dropped "
          "BEFORE recreating.")
    sys.exit(0)

if args.action == "recreate":
    if cur:
        sys.exit(f"Refusing: {args.field!r} already exists (id={cur['id']}). "
                 "Delete it first, or pick a clean name.")
    payload = {"properties": {args.field: {"rich_text": {}}}}
    if not args.execute:
        print("\n[DRY RUN] would PATCH:", json.dumps(payload)); sys.exit(0)
    print("\n[EXECUTE] recreating as fresh rich_text…")
    notion.databases.update(database_id=DB, **payload)
    print("done. Property recreated empty. Next: run fix_backfill_tags.py.")
