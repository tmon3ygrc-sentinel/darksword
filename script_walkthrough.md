# ⚔️ DARKSWORD — Script Walkthrough
**notion_logger_v.6.py — Line by Line**

> This document explains every section of the DARKSWORD pipeline so you own the code, not just run it.
> Last updated: V6.0 Final Merge (Autonomous Pipeline + Test Mode + Librarian pagination)

---

## Table of Contents

1. [Header & Imports](#1-header--imports)
2. [Configuration & Mode Detection](#2-configuration--mode-detection)
3. [Caches](#3-caches)
4. [Field Mappings](#4-field-mappings)
5. [Analyst System Prompt](#5-analyst-system-prompt)
6. [Utility Functions](#6-utility-functions)
7. [Pipeline Functions](#7-pipeline-functions)
8. [Notion Functions](#8-notion-functions)
9. [The Engine — push_record()](#9-the-engine--push_record)
10. [Parser](#10-parser)
11. [Main — Control Loop](#11-main--control-loop)
12. [Running The Two Modes](#12-running-the-two-modes)
13. [Key Concepts Reference](#13-key-concepts-reference)
14. [Merge Log — What Came From Where](#14-merge-log--what-came-from-where)

---

## 1. Header & Imports

```python
"""
⚔️  DARKSWORD — GRC Intelligence Platform V6.0
...
"""
```
A **docstring** — Python ignores it at runtime. Documentation for humans. Think of it as the classification header on an intel report.

---

```python
import os
```
Gives Python access to your **operating system** — specifically used to read environment variables from your `.env` file like `NOTION_TOKEN`.

---

```python
import re
```
**Regular Expressions** — a pattern matching engine. Used to find all `===INTEL_RECORD_START===` blocks in your text file, split `"Week 26 – Title"` on the dash, and clean transcript artifacts in `scrub()`.

---

```python
import sys
```
Gives access to **system-level info** — specifically `sys.argv`, the list of words you typed when you ran the script. `python script.py --test` means `sys.argv = ['script.py', '--test']`.

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
Modern Python way to handle file paths. `Path(__file__)` means "the folder this script lives in" — so the script always finds `governance_input.txt` regardless of where you run it from.

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

## 2. Configuration & Mode Detection

```python
SCRIPT_DIR = Path(__file__).parent.absolute()
```
`__file__` = this script's own file path. `.parent` = the folder it's in. `.absolute()` = full path, no relative shortcuts. Anchors every file operation to the script's home folder.

---

```python
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")
```
The `/` here isn't division — `Path` objects use it to **join paths**. Reads the `.env` file in the same folder as this script.

---

```python
TEST_MODE = "--test" in sys.argv
```
The entire mock/live switch in one line. `sys.argv` is a list. `"--test" in sys.argv` evaluates to `True` or `False`. That single boolean controls the entire rest of the script.

---

```python
NOTION_TOKEN      = os.getenv("NOTION_TOKEN")
DATABASE_ID       = os.getenv("DATABASE_ID")
CMMC_DB_ID        = os.getenv("CMMC_DATABASE_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
```
Reads four values from your `.env` file into memory. If a key doesn't exist, `os.getenv()` returns `None` instead of crashing.

---

```python
if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError("❌ Missing NOTION_TOKEN or DATABASE_ID in .env")
```
**Guard clause.** `not NOTION_TOKEN` is `True` when the value is `None` or empty. Stops the script immediately with a clear message instead of crashing mysteriously 50 lines later.

---

```python
if not TEST_MODE and not ANTHROPIC_API_KEY:
    raise ValueError("❌ Missing ANTHROPIC_API_KEY...")
```
Same guard — but only triggers in Live Mode. `and` means both conditions must be true. In Test Mode this check is skipped entirely — no API key needed, $0.00 cost.

---

```python
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if not TEST_MODE else None
```
**Ternary operator** — one-line if/else. Live Mode: create the Claude client. Test Mode: set it to `None`. Setting to `None` instead of skipping prevents `NameError` crashes if something accidentally references it.

---

## 3. Caches

```python
LEARNING_CACHE = {
    "Week 25": "2d655ed7...",
    "Week 26": "2d655ed7...",
    "Week 27": "2d655ed7...",
}
```
A **dictionary** — key/value pairs. The key is what your `.txt` file says (`"Week 26"`), the value is the Notion Page ID of that week's record. Your phone book — look up a name, get a number. Hardcoded because these IDs don't change.

---

```python
CMMC_CACHE: Dict[str, str] = {}
```
An **empty dictionary** that starts empty and gets filled at runtime by `load_cmmc_cache()`. Dynamic because Notion won't give you page IDs automatically — it has to query them fresh. The `: Dict[str, str]` is a type hint saying it maps strings to strings.

---

## 4. Field Mappings

```python
SELECT_FIELDS = {
    "content_category", "exploit_maturity", "source", ...
}
```
A **set** — like a list but faster for membership checks, no duplicates. These are Notion fields that accept exactly **one value** (dropdown). When the main loop sees a key in this set, it formats it as `{"select": {"name": value}}`.

---

```python
MULTI_SELECT_FIELDS = {
    "detection_opportunities", "attack_tactic", ...
}
```
Same idea — Notion fields that accept **multiple comma-separated values** (tags). The script splits on commas and formats each piece as a separate tag object.

---

```python
RICH_TEXT_FIELDS = {"key_takeaways", "executive_summary", "operational_relevance", "record_id"}
DATE_FIELDS      = {"intel_date", "intel_timestamp"}
NUMBER_FIELDS    = {"risk_severity_score"}
```
Same pattern — each set tells the main loop what Notion property format to use.

---

```python
SKIP_FIELDS = {
    "url", "title", "cpe_credits",
    "cmmc_mapping", "learning_phase",
    "GRC_Learning_Plan_All_Phases",
    "Master Frameworks(CMMC 2.0 / NIST 800-171)"
}
```
Fields the main loop **completely ignores** — either hardcoded in the `props` block, or handled separately in the relation logic below the loop. Without this, the loop would try to process them as regular fields and format them wrong.

---

## 5. Analyst System Prompt

```python
ANALYST_PROMPT = """
### MISSION OBJECTIVE
...
"""
```
A multi-line string sent to Claude as the **system message** — the standing orders that shape every response. It defines the output schema, field definitions, story identification rules, and validation steps. Claude reads this before it sees any transcript.

This is what makes Claude output perfectly structured `fieldname:: value` records instead of prose. The prompt is the contract between your script and the AI.

---

## 6. Utility Functions

These three helpers were integrated from Librarian's rewrite — cleaner property builders that keep `push_record()` readable.

```python
def to_text(val: str) -> list:
    return [{"text": {"content": str(val)[:2000]}}] if val else []
```
Builds a Notion `rich_text` block. The `[:2000]` slices the string to 2000 characters — Notion's hard limit on text fields. Returns an empty list if val is falsy, which tells Notion to leave the field blank.

---

```python
def to_select(val: str) -> dict:
    return {"name": str(val).strip()} if val else None
```
Builds a Notion `select` block. `.strip()` removes accidental leading/trailing spaces that would create duplicate dropdown options in Notion.

---

```python
def to_multi(val: str) -> list:
    items = [x.strip() for x in str(val).split(",")]
    return [{"name": i} for i in items if i]
```
Splits `"T1190, T1078, T1059"` into `["T1190", "T1078", "T1059"]` and wraps each in a Notion tag object. The `if i` at the end filters out empty strings from double commas.

---

```python
def scrub(text: str) -> str:
    text = re.sub(r'\b\d+:\d{2}\b', '', text)   # timestamps: 0:00, 12:34
    text = re.sub(r'\s+', ' ', text).strip()      # normalize whitespace
    return text
```
Cleans YouTube auto-caption noise from transcripts.

**What it removes:** timestamps like `0:00`, `12:34`, and excess whitespace.

**What it deliberately keeps:** anything in brackets like `[CVE-2024-1234]`, `[MITRE T1190]`, `[CISA KEV]` — these are intel content, not caption noise. An earlier version of this function used `re.sub(r'\[.*?\]', '', text)` which stripped all bracket content including threat intelligence. That regex was removed.

---

## 7. Pipeline Functions

```python
def extract_video_id(url: str) -> str:
```
Handles four YouTube URL formats with a list of regex patterns. Tries each one in order and returns the first match. If none match, raises a `ValueError` with the bad URL so you know exactly what to fix.

---

```python
def get_transcript(url: str) -> str:
```
Fetches the YouTube transcript using `YouTubeTranscriptApi`, then passes it through `scrub()`. Catches three specific exceptions: `TranscriptsDisabled`, `NoTranscriptFound`, and a catch-all for network errors. Each raises a `RuntimeError` with a clear message instead of a raw API traceback.

---

```python
def analyze_with_claude(transcript: str, url: str, today: str) -> str:
```
Sends the cleaned transcript to Claude with the `ANALYST_PROMPT` as the system message. `max_tokens=8000` gives Claude enough room to generate multiple full intel records. Returns the raw text output.

---

```python
def load_mock_data() -> str:
```
**Test Mode only.** Reads your existing `governance_input.txt` and returns it as if it just came from Claude. Costs $0.00. The entire point is to let you test the Notion push logic independently from the API call — run it 100 times to verify relations, field mappings, and error handling without spending a penny.

---

```python
def write_governance_file(content: str):
```
Writes Claude's output to `governance_input.txt`. Simple, but important — this is the handoff point between the Claude pipeline and the Notion push pipeline.

---

## 8. Notion Functions

```python
def load_cmmc_cache():
```
Queries your CMMC Notion database and builds `CMMC_CACHE` in memory. 

**Pagination** (integrated from Librarian): Notion returns max 100 results per query. The `while has_more` loop keeps fetching pages until it has all of them. Without this, a database over 100 controls would silently miss entries.

```python
while has_more:
    kwargs = {"database_id": CMMC_DB_ID, "page_size": 100}
    if cursor:
        kwargs["start_cursor"] = cursor
    res = notion.databases.query(**kwargs)
    has_more = res.get("has_more", False)
    cursor   = res.get("next_cursor")
```

The `**kwargs` syntax unpacks a dictionary as keyword arguments — the `start_cursor` key only gets added to the API call when a cursor exists.

---

```python
def update_compliance_status(control_ids: List[str], log_page_url: str):
```
The GRC write-back. After a record is pushed to the Daily Threat Brief database, this loops through the CMMC control IDs and updates each one in your CMMC database — stamping it as `"Evidence Pending"` and linking back to the source record. This is the evidence trail for audits.

---

## 9. The Engine — push_record()

```python
def push_record(record: dict, source_label: str, url: str) -> bool:
```
Takes the parsed record dictionary and builds the full Notion API payload. Returns `True` or `False` so the caller knows if it succeeded.

---

```python
props = {
    "Title":        {"title": [{"text": {"content": page_title}}]},
    "url":          {"url": url} if url else {},
    "date_watched": {"date": {"start": date.today().isoformat()}},
    "cpe_credits":  {"number": 0.5},
}
```
**Hardcoded base properties** — these four fields are set identically every run regardless of what's in your `.txt` file. Note `{"url": url} if url else {}` — passing an empty dict `{}` instead of `None` prevents the Notion API from rejecting a null URL value.

---

```python
for key, val in record.items():
    if key in SKIP_FIELDS or not val: continue
    if str(val).lower() in ("none", "unknown", "empty", "n/a"): continue
```
The routing loop. `continue` skips to the next iteration. Two skip conditions: field is in SKIP_FIELDS, OR the value is a placeholder string. This prevents pushing `"None"` or `"Unknown"` into Notion as real data.

---

```python
    if key in SELECT_FIELDS:
        props[key] = {"select": to_select(val)}
    elif key in MULTI_SELECT_FIELDS:
        props[key] = {"multi_select": to_multi(val)}
    elif key in RICH_TEXT_FIELDS:
        props[key] = {"rich_text": to_text(val)}
    elif key in DATE_FIELDS:
        props[key] = {"date": {"start": str(val).strip()}}
    elif key in NUMBER_FIELDS:
        try:
            props[key] = {"number": float(val)}
        except (ValueError, TypeError):
            pass
```
Routes each field to the correct Notion format. The `except (ValueError, TypeError)` on the number conversion is **specific** — it only catches bad number conversions, not everything. A bare `except:` would swallow `KeyboardInterrupt` and `SystemExit`.

---

```python
cmmc_raw = (
    record.get("Master Frameworks(CMMC 2.0 / NIST 800-171)", "") or
    record.get("cmmc_mapping", "")
)
```
**The compatibility bridge.** Tries the Notion column name first, falls back to the short key. The `or` operator returns the first truthy value — if the first `.get()` returns an empty string (falsy), it tries the second. Supports both autonomous mode (Notion column names) and manual mode (short keys).

---

```python
learning_raw = (
    record.get("GRC_Learning_Plan_All_Phases", "") or
    record.get("learning_phase", "")
)
if learning_raw:
    phase_key = re.split(r'\s[–-]\s', learning_raw)[0].strip()
```
Same dual-key compatibility for the Learning Plan relation. The `re.split(r'\s[–-]\s', ...)` handles both em dash `–` and regular hyphen `-` in `"Week 26 – Building compliance programs"`. The `[0]` takes everything before the dash — just `"Week 26"` — which is the lookup key for `LEARNING_CACHE`.

---

```python
response = notion.pages.create(
    parent={"database_id": DATABASE_ID},
    properties=props
)
```
The actual Notion API call. `parent={"database_id": DATABASE_ID}` is the correct format — not `"data_source_id"`, not `"type"`. This is the line that creates the record in your database.

---

## 10. Parser

```python
blocks = re.findall(
    r'===INTEL_RECORD_START===(.*?)===INTEL_RECORD_END===',
    content,
    re.DOTALL
)
```
Scans the entire file and extracts everything between each pair of start/end markers. `.*?` is non-greedy — the `?` prevents it from swallowing multiple records at once. `re.DOTALL` makes `.` match newlines so multi-line record content gets captured.

---

```python
for line in block.strip().split('\n'):
    if '::' in line:
        k, v = line.split('::', 1)
        raw[k.strip()] = v.strip()
```
Splits each record into lines, then splits each line on `::`. The `1` argument means "split on the first `::` only" — so values that contain `::` (like URLs or timestamps) don't break the parser. Both key and value get `.strip()` to remove whitespace.

---

## 11. Main — Control Loop

```python
while True:
```
**Infinite loop** — keeps the menu alive until you explicitly choose Exit. Every iteration takes input, does the work, then loops back to the menu.

---

```python
if choice == "0":
    break
```
`break` exits the `while True` loop. Script ends cleanly.

---

```python
elif choice == "1":
    if TEST_MODE:
        print("❌ Autonomous mode disabled in --test.")
        continue
```
Option 1 is double-locked — it checks `TEST_MODE` again inside the branch. `continue` skips back to the top of the loop without running the rest of the block.

---

```python
except (RuntimeError, ValueError) as e:
    print(f"❌ Pipeline failed: {e}")
    continue
```
**Specific exception handling** — only catches `RuntimeError` (from `get_transcript()`) and `ValueError` (from `extract_video_id()`). The pipeline fails gracefully and returns to the menu instead of crashing the whole script.

---

```python
elif choice == "3" and TEST_MODE:
```
Option 3 only appears in the menu AND only executes when `TEST_MODE` is `True`. Double-locked so you can't accidentally trigger mock mode in production.

---

## 12. Running The Two Modes

```bash
# Free — debug all day, $0.00
python notion_logger_v.6.py --test

# Live — full autonomous pipeline
python notion_logger_v.6.py
```

### Test Mode menu:
```
⚔️   DARKSWORD — GRC Intelligence Platform V6.0
     💡 TEST MODE  |  $0.00  |  API Disconnected

1. Autonomous Pipeline  ← disabled
2. Manual Pipeline
3. Test Pipeline        ← YOU ARE HERE
0. Exit
```

### Live Mode menu:
```
⚔️   DARKSWORD — GRC Intelligence Platform V6.0
     🔴 LIVE MODE  |  API Connected

1. Autonomous Pipeline  (YouTube → Claude → Notion)
2. Manual Pipeline      (governance_input.txt → Notion)
0. Exit
```

---

## 13. Key Concepts Reference

| Concept | What It Is | Where Used |
|---|---|---|
| Dictionary `{}` | Key/value store, like a phone book | LEARNING_CACHE, CMMC_CACHE, props |
| Set `{}` | Unordered collection, fast membership check | SELECT_FIELDS, SKIP_FIELDS, etc. |
| Guard clause | Early exit if conditions aren't met | Top of every function |
| List comprehension | Compact loop that builds a list | to_multi(), relation builders |
| Ternary operator | One-line if/else | `claude = ... if not TEST_MODE else None` |
| `sys.argv` | Words typed when running the script | `--test` flag detection |
| `.get(key, default)` | Safe dictionary lookup, no crash if missing | Every record.get() call |
| `or` chaining | Returns first truthy value | CMMC/Learning Plan compatibility bridge |
| `re.DOTALL` | Makes regex `.` match newlines | parse_records block extraction |
| `**kwargs` | Unpacks dictionary as function arguments | Pagination in load_cmmc_cache() |
| `break` | Exits a loop immediately | Exit menu option |
| `continue` | Skips current loop iteration to next | SKIP_FIELDS check, TEST_MODE lock |
| Specific exceptions | Catching only expected error types | Number conversion, pipeline errors |
| Non-greedy `.*?` | Regex match as few chars as possible | Block extraction between markers |

---

## 14. Merge Log — What Came From Where

This script is the result of live debugging against a real Notion database combined with a code review of an alternative rewrite.

| Feature | Origin | Notes |
|---|---|---|
| Core field mappings | DARKSWORD V5.4 | Confirmed working against live DB |
| `--test` / `TEST_MODE` flag | DARKSWORD V6.0 | $0.00 debug mode |
| Dual-key compatibility bridge | DARKSWORD V6.0 | Both Notion names and short keys work |
| `scrub()` function | Librarian rewrite | Fixed: removed `[.*?]` regex that stripped CVEs/MITRE IDs |
| Pagination in `load_cmmc_cache()` | Librarian rewrite | Handles databases >100 records |
| `to_text()`, `to_select()`, `to_multi()` | Librarian rewrite | Cleaner property builders |
| Specific exception types | Security review | Replaced bare `except:` |
| `{}` instead of `None` for empty URL | Security review | Notion API rejects null url values |
| `LEARNING_CACHE` preserved | DARKSWORD V5.4 | Librarian's rewrite removed this — restored |
| Parser `parse_records()` | DARKSWORD V5.4 | Librarian's rewrite had `records = []` TODO — restored |
| Correct parent `{"database_id": ...}` | DARKSWORD V5.4 | Librarian used `data_source_id` which is not a valid Notion API field |
| Correct property names `Title`, `url` | DARKSWORD V5.4 | Librarian used `Topic/Concept`, `Source URL` which don't match your DB |