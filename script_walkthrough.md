# ⚔️ DARKSWORD — Script Walkthrough
**notion_logger_v.6.py — Line by Line**

> This document explains every section of the DARKSWORD pipeline so you own the code, not just run it.

---

## Lines 1–11 — Header & Imports

```python
"""
⚔️  DARKSWORD — GRC Intelligence Platform V6.0
"""
```
A **docstring** — Python ignores it at runtime. It's documentation for humans. Think of it as the classification header on an intel report.

---

```python
import os
```
Gives Python access to your **operating system** — specifically used to read environment variables from your `.env` file like `NOTION_TOKEN`.

---

```python
import re
```
**Regular Expressions** — a pattern matching engine. Used to find all `===INTEL_RECORD_START===` blocks in your text file and to split `"Week 26 – Title"` on the dash.

---

```python
import sys
```
Gives access to **system-level info** — specifically `sys.argv`, which is the list of words you typed when you ran the script. `python script.py --test` means `sys.argv = ['script.py', '--test']`.

---

```python
import anthropic
```
The official Anthropic SDK. Handles the HTTP request to Claude's API so you don't have to write raw web requests.

---

```python
from datetime import date
```
Pulls just the `date` class from Python's built-in datetime library. Used to stamp `date_watched` with today's date automatically.

---

```python
from pathlib import Path
```
Modern Python way to handle file paths. `Path(__file__)` means "the folder this script lives in" — so the script always finds `governance_input.txt` in the right place regardless of where you run it from.

---

```python
from typing import List, Dict
```
**Type hints** — tells Python (and you) what data types functions expect. `List[str]` means a list of strings. Doesn't change behavior, makes the code readable and catches bugs early.

---

```python
from notion_client import Client
```
The official Notion SDK. Wraps the Notion API so `notion.pages.create()` works instead of writing raw HTTP calls.

---

```python
from dotenv import load_dotenv
```
Reads your `.env` file and loads `NOTION_TOKEN=xxx` into memory so `os.getenv("NOTION_TOKEN")` can find it.

---

## Lines 14–45 — Configuration & Mode Detection

```python
SCRIPT_DIR = Path(__file__).parent.absolute()
```
`__file__` = this script's own file path. `.parent` = the folder it's in. `.absolute()` = full path, no relative shortcuts. This anchors every file operation to the script's home folder.

---

```python
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")
```
The `/` here isn't division — `Path` objects use it to **join paths**. This says "look for `.env` in the same folder as this script."

---

```python
TEST_MODE = "--test" in sys.argv
```
The entire mock/live switch in one line. `sys.argv` is a list. `"--test" in sys.argv` is `True` or `False`. That boolean controls the entire rest of the script.

---

```python
NOTION_TOKEN      = os.getenv("NOTION_TOKEN")
DATABASE_ID       = os.getenv("DATABASE_ID")
CMMC_DB_ID        = os.getenv("CMMC_DATABASE_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```
Reads four values from your `.env` file into memory. If a key doesn't exist in `.env`, `os.getenv()` returns `None` instead of crashing.

---

```python
if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError("❌ Missing NOTION_TOKEN or DATABASE_ID in .env")
```
**Guard clause.** `not NOTION_TOKEN` is `True` when the value is `None` or empty. If either critical key is missing, the script stops immediately with a clear message instead of crashing mysteriously 50 lines later.

---

```python
if not TEST_MODE and not ANTHROPIC_API_KEY:
    raise ValueError("❌ Missing ANTHROPIC_API_KEY...")
```
Same guard — but only triggers in Live Mode. `and` means both conditions must be true. In Test Mode this entire check is skipped — no API key needed.

---

```python
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if not TEST_MODE else None
```
**Ternary operator** — one-line if/else. In Live Mode: create the Claude client. In Test Mode: set it to `None`. Setting it to `None` instead of not defining it prevents `NameError` crashes if something accidentally references it.

---

## Lines 48–60 — The Caches

```python
LEARNING_CACHE = {
    "Week 25": "2d655ed7...",
    "Week 26": "2d655ed7...",
}
```
A **dictionary** — key/value pairs. The key is what your `.txt` file says (`"Week 26"`), the value is the Notion Page ID of that week's record. This is your phone book — look up a name, get a number.

---

```python
CMMC_CACHE: Dict[str, str] = {}
```
An **empty dictionary** with a type hint saying it will map strings to strings. Starts empty — `load_cmmc_cache()` fills it at runtime by querying Notion. Dynamic, unlike `LEARNING_CACHE` which is hardcoded because Notion won't give you page IDs automatically.

---

## Lines 63–95 — Field Mapping Sets

```python
SELECT_FIELDS = {
    "content_category", "exploit_maturity", ...
}
```
A **set** — like a list but faster for checking membership, no duplicates. These are Notion fields that accept exactly **one value** (dropdown). When the script sees a key from your `.txt` that's in this set, it formats it as `{"select": {"name": value}}`.

---

```python
MULTI_SELECT_FIELDS = {
    "detection_opportunities", "attack_tactic", ...
}
```
Same idea — Notion fields that accept **multiple values** (multi-select tags). The script splits the comma-separated string from your `.txt` and formats each piece as a separate tag.

---

```python
RICH_TEXT_FIELDS = {"key_takeaways", "executive_summary", ...}
DATE_FIELDS      = {"intel_date", "intel_timestamp"}
NUMBER_FIELDS    = {"risk_severity_score"}
```
Same pattern — each set tells the main loop what Notion format to use for fields that land in it.

---

```python
SKIP_FIELDS = {"url", "title", "cmmc_mapping", ...}
```
Fields the main loop should **completely ignore** — either handled separately below (relations) or hardcoded in the `props` block at the top of `push_record`.

---

## `load_cmmc_cache()` — The Phone Book Builder

```python
def load_cmmc_cache():
    if not CMMC_DB_ID: return
```
`def` defines a reusable function. First line is a guard — if no CMMC database ID is configured, exit immediately. No crash, no noise.

---

```python
    res = notion.databases.query(database_id=CMMC_DB_ID)
```
Fires an API call to Notion — "give me all records from my CMMC database." `res` is the raw JSON response.

---

```python
    for page in res.get("results", []):
```
Loops through every record returned. `.get("results", [])` means "if 'results' key exists use it, otherwise use empty list" — prevents crash if Notion returns unexpected data.

---

```python
        title_props = page["properties"].get("Name", {}).get("title", [])
        if title_props:
            cid = title_props[0].get("plain_text", "").strip()
            CMMC_CACHE[cid] = page["id"]
```
Drills into Notion's nested JSON to extract the control ID text (like `"AC.L2-3.1.1"`) and maps it to that page's unique ID. After this loop, `CMMC_CACHE["AC.L2-3.1.1"]` gives you the page ID instantly.

---

## `push_record()` — The Engine

```python
def push_record(record: dict, source_label: str, url: str) -> bool:
```
Takes three inputs — the parsed record dictionary, a label string, and the URL. Returns `True` or `False` so the caller knows if it succeeded.

---

```python
    props = {
        "Title":        {"title": [{"text": {"content": page_title}}]},
        "url":          {"url": url if url else None},
        "date_watched": {"date": {"start": date.today().isoformat()}},
        "cpe_credits":  {"number": 0.5},
    }
```
**Hardcoded base properties** — these four fields get set the same way every single run regardless of what's in your `.txt` file. `date.today().isoformat()` produces `"2026-05-16"` automatically.

---

```python
    for key, val in record.items():
        if key in SKIP_FIELDS or not val: continue
```
Loops through every key/value pair parsed from your `.txt`. `continue` skips to the next iteration — if the key is in SKIP_FIELDS or the value is empty, do nothing and move on.

---

```python
        if val.lower() in ("none", "unknown", "empty", "n/a"): continue
```
If your AI writes `"None"` or `"Unknown"` as a value, skip it — don't push placeholder text into Notion as real data.

---

```python
        if key in SELECT_FIELDS:
            props[key] = {"select": {"name": str(val).strip()}}
        elif key in MULTI_SELECT_FIELDS:
            items = [x.strip() for x in str(val).split(",")]
            props[key] = {"multi_select": [{"name": i} for i in items if i]}
```
The routing logic. Checks which set the key belongs to and formats accordingly. The multi_select line is a **list comprehension** — a compact loop that splits `"T1190, T1078"` into `["T1190", "T1078"]` and wraps each in `{"name": "T1190"}`.

---

```python
    cmmc_raw = (
        record.get("Master Frameworks(CMMC 2.0 / NIST 800-171)", "") or
        record.get("cmmc_mapping", "")
    )
```
**The compatibility bridge** — tries the Notion column name first, falls back to the short key. The `or` operator returns the first truthy value. If the first `.get()` returns an empty string (falsy), it tries the second.

---

```python
    rels = [{"id": CMMC_CACHE[cid]} for cid in cids if cid in CMMC_CACHE]
```
A list comprehension. For each control ID in the comma-separated list, look it up in `CMMC_CACHE` and build a relation object — but only if that ID actually exists in the cache. The `if cid in CMMC_CACHE` filters out misses silently.

---

## `parse_records()` — The Parser

```python
    blocks = re.findall(
        r'===INTEL_RECORD_START===(.*?)===INTEL_RECORD_END===',
        content,
        re.DOTALL
    )
```
The regex engine scans your entire `.txt` file and pulls out everything between each pair of start/end markers. `.*?` means "match anything, as few characters as possible" — the `?` prevents it from swallowing multiple records at once. `re.DOTALL` makes `.` match newlines too.

---

```python
        for line in block.strip().split('\n'):
            if '::' in line:
                k, v = line.split('::', 1)
                raw[k.strip()] = v.strip()
```
Splits each record into individual lines, then splits each line on `::` — the `1` means "split on the first `::` only" so values containing `::` don't break. Strips whitespace from both sides.

---

## `main()` — The Control Loop

```python
    while True:
```
**Infinite loop** — keeps the menu alive until you explicitly choose Exit. Every iteration asks for input, does the work, then loops back to show the menu again.

---

```python
        if choice == "0":
            break
```
`break` exits the `while True` loop. Script ends cleanly.

---

```python
        elif choice == "3" and TEST_MODE:
```
Option 3 only exists in the menu AND only works when `TEST_MODE` is `True`. Double-locked so you can't accidentally trigger mock mode in production.

---

## Running The Two Modes

```bash
# Free — debug all day, $0.00
python notion_logger_v.6.py --test

# Live — full autonomous pipeline
python notion_logger_v.6.py
```

---

## Key Concepts Reference

| Concept | What It Is | Where Used |
|---|---|---|
| Dictionary `{}` | Key/value store, like a phone book | LEARNING_CACHE, CMMC_CACHE, props |
| Set `{}` | Unordered collection, fast membership check | SELECT_FIELDS, SKIP_FIELDS, etc. |
| Guard clause | Early exit if conditions aren't met | Top of every function |
| List comprehension | Compact loop that builds a list | multi_select formatting, rels building |
| Ternary operator | One-line if/else | `claude = ... if not TEST_MODE else None` |
| `sys.argv` | Words typed when running the script | `--test` flag detection |
| `.get(key, default)` | Safe dictionary lookup, no crash if missing | Every record.get() call |
| `or` chaining | Returns first truthy value | CMMC/Learning Plan compatibility bridge |
| `re.DOTALL` | Makes regex `.` match newlines | parse_records block extraction |
| `break` | Exits a loop | Exit menu option |
| `continue` | Skips current loop iteration | SKIP_FIELDS check |