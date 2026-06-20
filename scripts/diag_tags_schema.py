#!/usr/bin/env python3
"""
READ-ONLY Notion schema diagnostic for the CPE Tracker 'tags' blocker.

What it does (and ONLY this):
  - notion.databases.retrieve(DATABASE_ID)   <-- a pure GET, no writes
  - inspects the 'tags' property (id YbSu)
  - measures per-property schema byte weight
It never writes to Notion, never edits .env, never prints the token.

Run in your venv from anywhere:
  C:\\Work\\GRC\\.venv\\Scripts\\python.exe C:\\Work\\GRC\\darksword\\backups\\diag_tags_schema.py

Safe to delete afterward.
"""
import os, json
from dotenv import load_dotenv
from notion_client import Client

# Load creds from the project's .env (adjust path if you move this file)
ENV_PATH = r"C:\Work\GRC\darksword\.env"
load_dotenv(ENV_PATH)

tok = os.getenv("NOTION_TOKEN")
db  = os.getenv("DATABASE_ID")
if not tok or not db:
    raise SystemExit("Missing NOTION_TOKEN / DATABASE_ID in .env")

notion = Client(auth=tok)
obj = notion.databases.retrieve(database_id=db)   # READ-ONLY
props = obj["properties"]

title = "".join(t.get("plain_text", "") for t in obj.get("title", [])) or "(untitled)"
print(f"DB: {title}")
print(f"property count: {len(props)}")

# Byte weight of each property's schema definition as the API returns it
sizes = {n: len(json.dumps(c, ensure_ascii=False).encode("utf-8")) for n, c in props.items()}
api_total = len(json.dumps(props, ensure_ascii=False).encode("utf-8"))
print(f"API-visible schema bytes (full properties object): {api_total:,}")
print(f"  (Notion's reported internal cap figure was ~209,597; error showed tags at ~208,877)")

print("\n=== TOP 10 properties by API-visible byte weight ===")
for n, sz in sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:10]:
    print(f"  {sz:>9,}  {props[n]['type']:<13} {n!r}  (id={props[n]['id']})")

print("\n=== 'tags' property ===")
tname = next((n for n, c in props.items() if c["id"] == "YbSu"), None) or ("tags" if "tags" in props else None)
if tname is None:
    print("  !! No property with id 'YbSu' or name 'tags' found.")
else:
    c = props[tname]
    print(f"  name={tname!r}  id={c['id']}  type={c['type']}  api_bytes={sizes[tname]:,}")
    if c["type"] == "multi_select":
        opts = c["multi_select"]["options"]
        print(f"  >>> STILL multi_select. options enumerated = {len(opts)}")
        print(f"  sample: {[o['name'] for o in opts[:6]]}")
    elif c["type"] == "rich_text":
        print(f"  >>> now rich_text. API config = {json.dumps(c['rich_text'])}")
        print(f"  >>> API exposes NO option list for a rich_text property.")
    else:
        print(f"  raw: {json.dumps(c)[:400]}")

print("\n=== INTERPRETATION GUIDE ===")
print("  A) tags.type == multi_select  -> conversion never took. Options still live; fix = redo conversion.")
print("  B) tags.type == rich_text AND api_total is SMALL (few KB) -> the ~208KB weight is")
print("     orphaned option metadata Notion retains internally but does NOT expose via API.")
print("     => cannot purge options through the API (nothing to see). Fix = DELETE + RECREATE")
print("        the property as fresh rich_text.")
print("  C) tags.type == rich_text BUT tags still huge in api_bytes -> options ARE still in the")
print("     returned schema; an in-place option purge MIGHT be possible.")
