# ⚔️ DARKSWORD — Script Walkthrough
**notion_logger_v7.py — Complete Reference**

> This document explains every section of the DARKSWORD pipeline so you own the code, not just run it.
> Last updated: V7.0 — current build `d2030d1`

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
12. [Running The Script](#12-running-the-script)
13. [Valid Field Values Reference](#13-valid-field-values-reference)
14. [Key Concepts Reference](#14-key-concepts-reference)
15. [Change Log — V6.0 → V6.1](#15-change-log--v60--v61)
16. [Change Log — V6.1 → V7.0](#16-change-log--v61--v70)
17. [Change Log — V7.0 Additions](#17-change-log--v70-additions)

---

## 1. Header & Imports

```python
"""
⚔️  DARKSWORD — GRC Intelligence Platform V7.0
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
The official Notion SDK. Wraps the Notion API so `notion.pages.create()` works instead of writing raw HTTP calls. **Pinned to `notion-client==2.2.1`** — do not upgrade without testing; async behavior changed in later versions.

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
TEST_MODE          = "--test"           in sys.argv
AUTO_MODE          = "--auto"           in sys.argv
AUTO_OTX_MODE      = "--auto-otx"      in sys.argv
AUTO_BARRICADE_MODE = "--auto-barricade" in sys.argv
```
Four boolean mode flags, each a single `in` membership check. The modes are mutually exclusive — any conflicting combination raises `ValueError` immediately after this block, before any API clients are initialized.

**Mutual exclusivity checks** (all six pairings):
- `--test` + `--auto`
- `--test` + `--auto-otx`
- `--test` + `--auto-barricade`
- `--auto` + `--auto-otx`
- `--auto` + `--auto-barricade`
- `--auto-otx` + `--auto-barricade`

**When to use each flag:**

| Flag | Use case |
|---|---|
| *(none)* | Interactive menu — full control |
| `--test` | Debug Notion push logic without API cost |
| `--auto` | Task Scheduler — Simply Cyber daily run |
| `--auto-otx` | Task Scheduler — AlienVault OTX daily run |
| `--auto-barricade` | Task Scheduler — Barricade Cyber daily run |

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
Same guard — but only triggers in Live Mode. In Test Mode this check is skipped entirely — no API key needed, $0.00 cost.

---

```python
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if not TEST_MODE else None
```
**Ternary operator** — one-line if/else. Live Mode: create the Claude client. Test Mode: set it to `None`. Setting to `None` instead of skipping prevents `NameError` crashes if something accidentally references it.

---

## 3. Caches

### LEARNING_CACHE

```python
LEARNING_CACHE = {
    "Week 1":  os.getenv("LEARNING_WEEK_1",  ""),
    ...
    "Week 36": os.getenv("LEARNING_WEEK_36", ""),
}
```
A **dictionary** mapping week labels to Notion page IDs. Keys are what gets matched during auto-detection (`"Week 23"`), values are the Notion page IDs stored in `.env`. Loaded from environment variables so IDs stay out of source code.

**Current weeks loaded:** 1, 2, 3, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 33, 35, 36

---

### DOMAIN_TO_WEEKS

```python
DOMAIN_TO_WEEKS = {
    "Incident Response (IR)":                    ["Week 23"],
    "Supply Chain Risk Management (SR)":         ["Week 19", "Week 29"],
    "Risk Assessment (RA)":                      ["Week 18", "Week 20"],
    "Access Control (AC)":                       ["Week 13"],
    "Identification and Authentication (IA)":    ["Week 13"],
    "Configuration Management (CM)":             ["Week 12"],
    "System Integrity (SI)":                     ["Week 17"],
    "System and Communications Protection (SC)": ["Week 17"],
    "Security Awareness and Training (AT)":      ["Week 5"],
    "Audit and Accountability (AU)":             ["Week 27", "Week 28"],
}
```
Maps each CMMC control domain to the most relevant learning plan week(s). A single domain can map to multiple weeks.

---

### CATEGORY_TO_WEEKS

```python
CATEGORY_TO_WEEKS = {
    "regulatory":            ["Week 25"],
    "advisory":              ["Week 26"],
    "supply-chain":          ["Week 19", "Week 29"],
    "incident":              ["Week 23"],
    "ransomware":            ["Week 23"],
    "campaign":              ["Week 18"],
    "vulnerability":         ["Week 20", "Week 21"],
    "malware":               ["Week 19"],
    "breach":                ["Week 28"],
    "law-enforcement":       ["Week 25"],
    "ai-risk":               ["Week 17"],
    "phishing":              ["Week 23"],
    "identity-intelligence": ["Week 13"],
}
```
Maps each `intel_category` value to relevant learning weeks. Works alongside `DOMAIN_TO_WEEKS` — both run on every record, results are combined into a single deduplicated set.

---

### CMMC_CACHE and CMMC_MISSES

```python
CMMC_CACHE: Dict[str, str] = {}
CMMC_MISSES: List[str]     = []
```
`CMMC_CACHE` is an empty dictionary filled at runtime by `load_cmmc_cache()`. Currently holds **128 controls**.

`CMMC_MISSES` accumulates any control IDs that `push_record()` could not resolve against the cache. After all records are pushed, `main()` prints a **miss report** listing every unresolved ID. This surfaces Claude output format issues or missing controls in the Notion database without interrupting the push loop.

---

## 4. Field Mappings

```python
SELECT_FIELDS = {
    "content_category", "exploit_maturity", "source", "story_type",
    "response_urgency", "asset_criticality", "active_exploitation",
    "confidence", "cisa_kev", "intel_type", "source_show"
}
```
A **set** of Notion fields that accept exactly **one value** (single dropdown). When the main loop sees a key in this set, it formats the value as `{"select": {"name": value}}`.

`source_show` is a select field with three canonical values: `"Simply Cyber Daily Threat Brief"`, `"AlienVault OTX"`, `"Barricade Cyber"`. The `ANALYST_PROMPT` instructs Claude to use only these exact strings.

---

```python
MULTI_SELECT_FIELDS = {
    "detection_opportunities", "attack_tactic",
    "identity_impact", "impacted_identity_provider",
    "content_type", "cpe_category", "tags", "kill_chain_phase",
    "attack_techniques", "target_sector",
    "threat_actor", "priority_level", "intel_category", "control_domains",
    "dfir_phase", "investigation_type"
}
```
Fields that accept **multiple comma-separated values** (tag clouds). The script splits on commas and formats each piece as a separate Notion tag object.

---

```python
RICH_TEXT_FIELDS = {
    "key_takeaways", "executive_summary", "operational_relevance", "record_id"
}
DATE_FIELDS      = {"intel_date", "intel_timestamp"}
NUMBER_FIELDS    = {"risk_severity_score"}
```
Same pattern — each set tells the main loop what Notion property format to apply.

---

```python
SKIP_FIELDS = {
    "url", "title", "cpe_credits",
    "cmmc_mapping", "learning_phase",
    "GRC_Learning_Plan_All_Phases",
    "Master Frameworks(CMMC 2.0 / NIST 800-171)"
}
```
Fields the main loop **completely ignores** — either hardcoded in the `props` block, or handled separately in the relation logic below the loop.

---

## 5. Analyst System Prompt

```python
ANALYST_PROMPT = """
### MISSION OBJECTIVE
...
"""
```
A multi-line string sent to Claude as the **system message** — the standing orders that shape every response. It defines the output schema, field definitions, story identification rules, valid field values, and validation steps. Claude reads this before it sees any transcript.

**Key prompt rules:**
- `identity_impact` and `impacted_identity_provider` must use **short comma-separated tags** from the Notion dropdown, not sentences
- `GRC_Learning_Plan_All_Phases` can be left blank — the script auto-detects it
- `threat_actor` set to `unknown` will show as empty in Notion (skipped by the placeholder filter)
- `source_show` must be one of three canonical values: `"Simply Cyber Daily Threat Brief"`, `"AlienVault OTX"`, or `"Barricade Cyber"`

---

### OTX_ANALYST_PROMPT

```python
OTX_ANALYST_PROMPT = (
    ANALYST_PROMPT
    .replace(...)
)
```

A modified copy of `ANALYST_PROMPT` built via chained `.replace()` calls. Used exclusively by the OTX Pipeline (Choice 4 / `--auto-otx`). Five targeted changes from the base prompt:

1. **Schema pre-fill** — `content_type:: Threat Intelligence Feed` is hard-coded in the schema template so Claude never defaults to "Podcast/Video".
2. **`content_category` added to schema** — added immediately after `content_type` with default "Threat Intelligence".
3. **`impacted_identity_provider` added to schema** — added before `===INTEL_RECORD_END===`.
4. **Field def: content_type** — `Do NOT use "Podcast/Video"` added explicitly.
5. **Field def: content_category** — strengthened with "Do NOT leave blank".

---

## 6. Utility Functions

```python
def to_text(val: str) -> list:
    return [{"text": {"content": str(val)[:2000]}}] if val else []
```
Builds a Notion `rich_text` block. The `[:2000]` slices the string to 2000 characters — Notion's hard limit on text fields.

---

```python
def to_select(val: str) -> dict:
    return {"name": str(val).strip()} if val else None
```
Builds a Notion `select` block. `.strip()` removes accidental leading/trailing spaces that would create duplicate dropdown options.

---

```python
def to_multi(val: str) -> list:
    items = [x.strip() for x in str(val).split(",")]
    return [{"name": i} for i in items if i]
```
Splits `"T1190, T1078, T1059"` into `["T1190", "T1078", "T1059"]` and wraps each in a Notion tag object. The `if i` at the end filters out empty strings from double commas.

---

```python
def normalize_cid(cid: str) -> str:
```
Strips whitespace and normalizes case on a CMMC control ID before cache lookup. Without this, `"AC.L2-3.1.1 "` (trailing space) would miss the cache entry `"AC.L2-3.1.1"`. All cache keys and lookup values pass through `normalize_cid()`.

---

```python
def scrub(text: str) -> str:
    text = re.sub(r'\b\d+:\d{2}\b', '', text)   # timestamps: 0:00, 12:34
    text = re.sub(r'\s+', ' ', text).strip()      # normalize whitespace
    return text
```
Cleans YouTube auto-caption noise from transcripts. Deliberately keeps bracket content like `[CVE-2024-1234]` and `[MITRE T1190]` — an earlier version stripped these with `re.sub(r'\[.*?\]', '', text)` which destroyed threat intelligence.

---

## 7. Pipeline Functions

```python
def extract_video_id(url: str) -> str:
```
Handles four YouTube URL formats with a list of regex patterns. Tries each one in order and returns the first match. If none match, raises `ValueError` with the bad URL.

---

```python
def get_show_notes(target_date: str = None) -> tuple:
```
**Primary Simply Cyber ingest.** Fetches structured show notes from `cyberthreatbrief.simplycyber.io` — no YouTube API, no yt-dlp, no Whisper, no FFmpeg.

Two-step process:
1. Hits the episodes listing page and finds the URL for the target date by matching `YYYY-MM-DD` in the href.
2. Fetches that episode page, strips nav/footer/script noise, runs `scrub()`, returns `(clean_text, canonical_url)`.

`target_date` defaults to today but accepts any `YYYY-MM-DD` string for backfill. Raises `RuntimeError` if the episode isn't published yet.

---

```python
def get_rss_episode_date() -> tuple[str, str | None]:
```
Returns `(date_str, youtube_url)` for the most recent Simply Cyber episode from the Transistor RSS feed.

- `date_str` — `YYYY-MM-DD` from the entry's `pubDate`
- `youtube_url` — full `https://www.youtube.com/watch?v=...` URL if extractable; `None` otherwise

YouTube URL extraction tries `entry.yt_videoid` first (YouTube namespace field), then scans `entry.links` for any href containing `youtube.com` or `youtu.be`.

Used by Choice 5 (interactive) and `--auto` (non-interactive). The YouTube URL is used by the `--auto` word count gate to trigger a transcript fallback.

---

```python
def get_barricade_intel(url: str) -> str:
```
Fetches a YouTube transcript via `YouTubeTranscriptApi` — no audio download, no Whisper. Used by both the Barricade pipeline and the Simply Cyber YouTube fallback (Choice 7 / `--auto` word count gate).

```python
ytt = YouTubeTranscriptApi()
try:
    transcript = ytt.fetch(video_id)
except VideoUnplayable:
    raise RuntimeError(f"❌ Video {video_id} is unplayable or restricted...")
```

Raises `RuntimeError` on `VideoUnplayable` so callers get a clean error rather than a raw SDK exception.

---

```python
def get_barricade_latest() -> tuple[str, str] | None:
```
Returns `(video_id, title)` for the most recent playable Barricade Cyber video, or `None` if already ingested.

**Flow:**
1. Polls the YouTube channel RSS feed (`channel_id=UCLco-g6YIjhPqOBBR6CUXpg`) with feedparser
2. Reads `barricade_last_ingested.txt` for the last ingested video ID (missing file = no prior ingest)
3. Loops through up to 15 RSS entries:
   - If `video_id == last_id` → return `None` (nothing new)
   - Probes `ytt.fetch(video_id)` — any exception means the video is restricted/unavailable, skip and try next
   - On successful fetch → return `(video_id, title)` without writing the dedup file
4. If all 15 entries fail → raises `RuntimeError`

**Important:** `get_barricade_latest()` does NOT write `barricade_last_ingested.txt`. The caller (`AUTO_BARRICADE_MODE` in `main()`) writes it after `push_all()` succeeds. This prevents marking a video as ingested when a later Claude or Notion step fails.

---

```python
def get_transcript(url: str) -> str:
```
Downloads YouTube audio via yt-dlp and transcribes with OpenAI Whisper. Retained for reference. **Not called by any active pipeline** — blocked at network level for Simply Cyber, and replaced by `get_barricade_intel()` for all other sources.

---

```python
def analyze_with_claude(content: str, url: str, today: str) -> str:
```
Sends cleaned content to Claude using `ANALYST_PROMPT` as the system message. `max_tokens=16000`. Returns raw Claude output string.

---

```python
def analyze_with_claude_prompt(content: str, url: str, today: str, prompt: str) -> str:
```
Identical to `analyze_with_claude()` but accepts a custom system prompt. Used by the OTX pipeline to pass `OTX_ANALYST_PROMPT`.

---

```python
def get_otx_pulses(api_key: str, lookback_hours: int = 24) -> list:
```
Fetches AlienVault OTX threat intelligence pulses through a three-gate filter:

**Gate 1 — Time filter:** Only pulses modified in the last `lookback_hours` (default 24). Server-side via `modified_since`.

**Gate 2 — Relevance filter:** Checks pulse tags against DARKSWORD-relevant keywords:
```python
RELEVANT_TAGS = {
    'ransomware', 'apt', 'nation-state', 'critical-infrastructure',
    'cisa', 'supply-chain', 'phishing', 'identity', 'malware',
    'vulnerability', 'exploit', 'lateral-movement', 'credential-access'
}
```

**Gate 3 — Deduplication:** Drops duplicate pulse IDs within the same run.

Returns a list of `{"content", "url", "name"}` dicts for direct input to `analyze_with_claude_prompt()`.

---

```python
def load_mock_data() -> str:
```
**Test Mode only.** Reads the existing `governance_input.txt` as if it came from Claude. $0.00 cost.

---

```python
def write_governance_file(content: str):
```
Writes Claude's output to `governance_input.txt`. Before writing, checks for `===INTEL_RECORD_START===` / `===INTEL_RECORD_END===` marker count mismatch — a mismatch indicates Claude was truncated mid-record.

---

## 8. Notion Functions

```python
def load_cmmc_cache(retries: int = 3, delay: int = 15):
```
Queries the CMMC Notion database and builds `CMMC_CACHE` in memory. Currently loads **128 controls**.

**Pagination:** Notion returns max 100 results per query. The `while has_more` loop fetches all pages.

**Retry loop:** Wraps the entire fetch in a `for attempt in range(1, retries + 1)` loop. Rate-limit errors wait `delay` seconds and retry. Non-rate-limit errors fail immediately.

All cache keys are stored via `normalize_cid()` so lookups are whitespace/case tolerant.

---

```python
def normalize_cid(cid: str) -> str:
```
Strips and normalizes a control ID. Called at both cache-build time (keys) and lookup time (values from Claude output) so a stray space never causes a miss.

---

```python
def update_compliance_status(control_ids: List[str], log_page_url: str):
```
The GRC write-back. After a record is pushed to CPE Tracker, loops through the CMMC control IDs and updates each one in Master Frameworks — stamping it `"Evidence Pending"` and linking back to the source record. This is the audit evidence trail.

---

## 9. The Engine — push_record()

```python
def push_record(record: dict, source_label: str, url: str) -> bool:
```
Takes the parsed record dictionary and builds the full Notion API payload. Returns `True` or `False`.

### Base Properties

```python
props = {
    "Title":        {"title": [{"text": {"content": page_title}}]},
    "url":          {"url": url} if url else {},
    "date_watched": {"date": {"start": date.today().isoformat()}},
    "cpe_credits":  {"number": 0.5},
}
```
These four fields are set identically every run regardless of what's in your `.txt` file.

### Field Routing Loop

```python
for key, val in record.items():
    if key in SKIP_FIELDS or not val: continue
    if str(val).lower() in ("none", "unknown", "empty", "n/a"): continue
```
Two skip conditions: field is in SKIP_FIELDS, OR the value is a placeholder string. `threat_actor:: unknown` will show as **empty** in Notion — intentional, unknown attribution should not appear as a tag.

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

### CMMC Relation

```python
cmmc_raw = (
    record.get("Master Frameworks(CMMC 2.0 / NIST 800-171)", "") or
    record.get("cmmc_mapping", "")
)
```
**Compatibility bridge.** Tries the full Notion column name first, falls back to the short key.

Each control ID is resolved via `normalize_cid()`. IDs that miss the cache are appended to `CMMC_MISSES` for the post-run report.

### Learning Plan Relation

**Three-step auto-detection:**

1. **Explicit override** — if `GRC_Learning_Plan_All_Phases` is set in the record, honor it.
2. **Domain mapping** — splits `control_domains` on commas, looks each up in `DOMAIN_TO_WEEKS`.
3. **Category mapping** — splits `intel_category` on commas, looks each up in `CATEGORY_TO_WEEKS`.

Results deduplicated via `set()`, sorted, and pushed as a multi-relation. A single record can link to 5+ learning weeks automatically.

### Notion Create

```python
response = notion.pages.create(
    parent={"database_id": DATABASE_ID},
    properties=props
)
```

---

## 10. Parser

```python
blocks = re.findall(
    r'===INTEL_RECORD_START===(.*?)===INTEL_RECORD_END===',
    content,
    re.DOTALL
)
```
`.*?` is non-greedy — prevents swallowing multiple records. `re.DOTALL` makes `.` match newlines.

```python
for line in block.strip().split('\n'):
    if '::' in line:
        k, v = line.split('::', 1)
        raw[k.strip()] = v.strip()
```
The `1` argument means "split on the first `::` only" — so URLs and timestamps don't break the parser.

---

## 11. Main — Control Loop

### Banner and mode detection

`main()` opens with a banner that shows the active mode:
- `💡 TEST MODE` — `--test` flag
- `🤖 AUTO MODE` — `--auto` flag
- `🤖 AUTO-OTX` — `--auto-otx` flag
- `🤖 AUTO-BARRICADE` — `--auto-barricade` flag
- `🔴 LIVE MODE` — interactive, no flags

### AUTO_MODE block (`--auto`)

```python
date_str, youtube_url = get_rss_episode_date()
content, url          = get_show_notes(date_str)
```

After `get_show_notes()` returns, word count gate:

```python
word_count = len(content.split())
if word_count < 500:
    # Fall back to YouTube transcript
    content = get_barricade_intel(youtube_url)
    url     = youtube_url
```

If the fallback also fails (no YouTube URL, or transcript unavailable), exits with code 0 — not an error the Task Scheduler should alert on.

### AUTO_OTX_MODE block (`--auto-otx`)

Reads `OTX_API_KEY`, calls `get_otx_pulses()`, loops each pulse through `analyze_with_claude_prompt()` with `OTX_ANALYST_PROMPT`, batch-pushes all records.

### AUTO_BARRICADE_MODE block (`--auto-barricade`)

```python
result = get_barricade_latest()
if result is None:
    return  # already ingested; exit cleanly
video_id, _title = result
url = f"https://www.youtube.com/watch?v={video_id}"
content = get_barricade_intel(url)
...
push_all(records, "Barricade Cyber", url)
BARRICADE_LAST_FILE.write_text(video_id, encoding="utf-8")
```

The dedup file write happens **after** `push_all()` succeeds. A Claude or Notion failure leaves the file unchanged so the next run retries the same video.

### Interactive menu

```
1. Autonomous Pipeline  (Show Notes → Claude → Notion)
2. Manual Pipeline      (governance_input.txt → Notion)
3. Test Pipeline        (Mock data → Notion) ← TEST MODE ONLY
4. OTX Pipeline         (AlienVault → Claude → Notion)
5. RSS Feed Pipeline    (Barricade Cyber → Claude → Notion)
6. Barricade Cyber      (YouTube Transcript → Claude → Notion)
7. Simply Cyber YouTube (YouTube Transcript → Claude → Notion) ← show notes fallback
0. Exit
```

Choice 6 prompts for a YouTube URL → `get_barricade_intel()` → Claude → Notion, source label `"Barricade Cyber"`.

Choice 7 is identical but pushes under source label `"Simply Cyber Daily Threat Brief"`. Use it when the show notes page has insufficient content and you need to pull from the YouTube transcript manually.

### Post-run CMMC miss report

After the menu loop exits:

```python
if CMMC_MISSES:
    print(f"⚠️  CMMC MISS REPORT — {len(CMMC_MISSES)} unresolved ID(s)")
    for entry in CMMC_MISSES:
        print(f"   ✗ {entry}")
else:
    print("✅ All CMMC IDs resolved cleanly.")
```

Common miss causes: Claude output format doesn't match the Notion control name exactly, or the control isn't in the Master Frameworks database yet.

---

## 12. Running The Script

```bash
# Free — debug all day, $0.00
python notion_logger_v7.py --test

# Live — full interactive menu
python notion_logger_v7.py

# Non-interactive (Task Scheduler)
python notion_logger_v7.py --auto
python notion_logger_v7.py --auto-otx
python notion_logger_v7.py --auto-barricade
```

### Live Mode menu
```
⚔️   DARKSWORD — GRC Intelligence Platform V7.0
     🔴 LIVE MODE  |  API Connected

1. Autonomous Pipeline  (Show Notes → Claude → Notion)
2. Manual Pipeline      (governance_input.txt → Notion)
4. OTX Pipeline         (AlienVault → Claude → Notion)
5. RSS Feed Pipeline    (Barricade Cyber → Claude → Notion)
6. Barricade Cyber      (YouTube Transcript → Claude → Notion)
7. Simply Cyber YouTube (YouTube Transcript → Claude → Notion)  <- show notes fallback
0. Exit
```

### Simply Cyber workflow (daily)

Task Scheduler → `run_darksword_auto.ps1` → `--auto`:
1. Polls Transistor RSS for today's episode date and YouTube URL
2. Fetches show notes from `cyberthreatbrief.simplycyber.io`
3. If <500 words → falls back to YouTube transcript via `get_barricade_intel()`
4. Sends content to Claude → writes `governance_input.txt` → pushes to Notion

Or run interactively:
1. `cpe` → **1. Autonomous Pipeline** → enter date (blank = today)
2. Script fetches show notes, runs Claude, pushes to Notion

### OTX workflow

Task Scheduler → `run_darksword_otx.ps1` → `--auto-otx` (daily), or:
1. `cpe` → **4. OTX Pipeline**
2. Fetches last 24hrs of OTX pulses, filters by relevance
3. Each pulse analyzed individually with `OTX_ANALYST_PROMPT`
4. Batch-pushed under source label "AlienVault OTX"

### Barricade workflow

Task Scheduler → `run_darksword_barricade.ps1` → `--auto-barricade` (daily), or:
1. `cpe` → **6. Barricade Cyber** → paste YouTube URL

The `--auto-barricade` flag checks the RSS feed, skips restricted videos, deduplicates against `barricade_last_ingested.txt`, and exits cleanly if nothing is new.

### Manual pipeline workflow (any source)

1. Go to YouTube video → open transcript → toggle timestamps off → copy all text
2. Paste transcript into Claude chat using `prompts/cpe_prompt_claude.txt`
3. Claude generates `===INTEL_RECORD_START===` formatted records
4. Copy records into `governance_input.txt`
5. `cpe` → **2. Manual Pipeline** → enter source URL

---

## 13. Valid Field Values Reference

All multi-select fields must use **exact values** from the Notion dropdown. The script skips values not in the dropdown — they show as empty rather than erroring.

### threat_actor
`unknown`, `unknown financially motivated operators`, `nation-state-unknown`, `ShinyHunters`, `Salt Typhoon (China-linked nation-state)`, `Russian State Actors`, `muddy-water`, `volt-typhoon`, `Lazarus Group`, `Various Ransomware Operators`, `Ransomware Affiliates`, `transnational cybercrime organizations`, `Russia-linked proxy infrastructure operators`, `insider-threat-accidental`, `(no claim of responsibility)`, `Iranian state-nexus actors`, `Konni Group (North Korea-linked)`

> **Note:** `unknown` is skipped by the script's placeholder filter and will show as empty in Notion. This is correct behavior.

### source_show
`Simply Cyber Daily Threat Brief`, `AlienVault OTX`, `Barricade Cyber`

These are the only three canonical values. The `ANALYST_PROMPT` instructs Claude to use only these strings. Use `normalize_source_show.py` to retroactively fix non-canonical values in the database.

### identity_impact
`user-account`, `privileged-account`, `federated-identity`, `Service-Account`, `standard-user`, `non-human-identity`, `customer-data`, `biometric-data`, `corporate-intellectual-property`, `medical-records`, `pii`, `banking-credentials`, `credentials`, `crypto-wallets`, `m365-credentials`, `session-tokens`, `tokens`, `administrative-roles`, `workforce-accounts`, `service-accounts`, `system-administrators`, `security-operations`, `Account Takeover`, `Privilege Escalation`

### impacted_identity_provider
`entra-id`, `on-prem-ad`, `okta`, `aws-iam`, `github-actions`, `mfa-provider`, `microsoft-365`, `google-workspace`, `oauth`, `azure-ad`, `local-system`, `kubernetes-rbac`, `certificates`, `mobile-biometrics`, `aws`, `azure`, `workforce-accounts`, `administrative-roles`, `service-accounts`, `system-administrators`, `developers`, `devops-engineers`, `cloud-administrators`, `ics-ot-security`

### target_sector
`technology`, `healthcare`, `government`, `financial-services`, `critical-infrastructure`, `manufacturing`, `defense`, `education`, `energy`, `defense-industrial-base`, `developers`, `cloud-environments`, `software-development`, `all-sectors`, `enterprise`, `internet-infrastructure`, `retail`, `e-commerce`, `telecommunications`, `operational-technology`

### intel_category
`advisory`, `campaign`, `malware`, `vulnerability`, `supply-chain`, `incident`, `ransomware`, `identity-intelligence`, `phishing`, `social-engineering`, `breach`, `regulatory`, `ai-risk`, `law-enforcement`, `threat-actor`

### control_domains *(used for auto learning plan mapping)*
`System Integrity (SI)`, `Configuration Management (CM)`, `Access Control (AC)`, `Identification and Authentication (IA)`, `Incident Response (IR)`, `Audit and Accountability (AU)`, `Security Awareness and Training (AT)`, `System and Communications Protection (SC)`, `Supply Chain Risk Management (SR)`, `Risk Assessment (RA)`

### kill_chain_phase
`reconnaissance`, `weaponization`, `delivery`, `exploitation`, `installation`, `command-and-control`, `actions-on-objectives`, `initial-access`, `lateral-movement`, `credential-access`, `privilege-escalation`, `exfiltration`, `persistence`, `impact`, `execution`, `none`

### attack_tactic
`initial-access`, `execution`, `persistence`, `privilege-escalation`, `defense-evasion`, `credential-access`, `discovery`, `lateral-movement`, `collection`, `exfiltration`, `command-and-control`, `impact`, `reconnaissance`, `social-engineering`, `none`

---

## 14. Key Concepts Reference

| Concept | What It Is | Where Used |
|---|---|---|
| Dictionary `{}` | Key/value store, like a phone book | LEARNING_CACHE, CMMC_CACHE, DOMAIN_TO_WEEKS, props |
| Set `{}` | Unordered collection, fast membership check | SELECT_FIELDS, SKIP_FIELDS, `linked_weeks` |
| Guard clause | Early exit if conditions aren't met | Top of every function |
| List comprehension | Compact loop that builds a list | `to_multi()`, relation builders |
| Ternary operator | One-line if/else | `claude = ... if not TEST_MODE else None` |
| `sys.argv` | Words typed when running the script | All mode flag detection |
| `.get(key, default)` | Safe dictionary lookup, no crash if missing | Every `record.get()` call |
| `or` chaining | Returns first truthy value | CMMC/Learning Plan compatibility bridge |
| `re.DOTALL` | Makes regex `.` match newlines | `parse_records` block extraction |
| `**kwargs` | Unpacks dictionary as function arguments | Pagination in `load_cmmc_cache()` |
| `break` | Exits a loop immediately | Exit menu option |
| `continue` | Skips current loop iteration to next | SKIP_FIELDS check, TEST_MODE lock |
| Specific exceptions | Catching only expected error types | Number conversion, pipeline errors |
| Non-greedy `.*?` | Regex match as few chars as possible | Block extraction between markers |
| `set()` deduplication | Automatically removes duplicates | `linked_weeks`, OTX pulse dedup |
| `sorted()` | Alphabetical sort | Ensures consistent week ordering in Notion |

---

## 15. Change Log — V6.0 → V6.1

### Field Mapping Fixes
- `impacted_identity_provider` — was missing from all field sets entirely. Added to `MULTI_SELECT_FIELDS`.
- `identity_impact` — confirmed as `MULTI_SELECT_FIELDS`. Values must be short tags, not sentences.
- All multi-select field values validated against live Notion dropdown options via API query.

### Learning Plan — Complete Rewrite
**Before (V6.0):** Single relation, required manual week specification in every record.

**After (V6.1):** Multi-relation auto-detection via three-step engine (explicit → domain → category). Results deduplicated via `set()`. `LEARNING_CACHE` expanded from 3 weeks to 29 weeks.

### CMMC Cache
- `SR.L2-3.15.2` (Supply Chain Risk Management: Notification of Supply Chain Compromise) added to Master Frameworks DB
- Cache now at 128 controls

---

## 16. Change Log — V6.1 → V7.0

### Show Notes Pipeline (`get_show_notes()`)
**Before:** Choice 1 called `get_transcript()` → yt-dlp → Whisper. Blocked at network level for Simply Cyber.

**After:** Choice 1 calls `get_show_notes()` which fetches from `cyberthreatbrief.simplycyber.io` via plain HTTP. No yt-dlp, no Whisper, no FFmpeg. Date-addressable for backfill.

### Per-Source Prompt Tuning (`analyze_with_claude_prompt()`)
New overload that accepts a custom system prompt. Enables different sources to use different extraction instructions.

### OTX Pipeline (Choice 4)
New `get_otx_pulses()` with three-gate filter (time → relevance → deduplication). Uses `OTX_ANALYST_PROMPT`. Each pulse analyzed individually to prevent Claude from conflating content.

### OTX_ANALYST_PROMPT Fix
V6 had a no-op `.replace()` for `impacted_identity_provider` (target string didn't exist in `ANALYST_PROMPT`). V7 fixes by patching the schema itself — pre-filling `content_type`, adding `content_category` and `impacted_identity_provider` to the `===INTEL_RECORD_START===` template.

### `max_tokens` Increased to 16000
V6 used 8000. Dense episodes could cause Claude to truncate mid-record. `write_governance_file()` now warns on marker count mismatch.

### CMMC Cache Retry Loop
`load_cmmc_cache()` now retries up to 3 times with a 15-second delay on rate-limit errors.

---

## 17. Change Log — V7.0 Additions

### RSS Feed Pipeline (Choice 5)
`get_rss_episode_date()` parses the Transistor RSS feed to auto-detect today's episode date — no manual date entry. Choice 5 chains this directly into `get_show_notes()` and Claude.

### Non-Interactive Flags (Task Scheduler)
Three `--auto-*` flags added for unattended operation:

| Flag | Pipeline |
|---|---|
| `--auto` | Simply Cyber: RSS date → show notes → Claude → Notion |
| `--auto-otx` | AlienVault OTX full pipeline |
| `--auto-barricade` | Barricade Cyber: RSS → transcript → Claude → Notion |

Three PS1 wrappers (`run_darksword_auto.ps1`, `run_darksword_otx.ps1`, `run_darksword_barricade.ps1`) set `PYTHONIOENCODING=utf-8` and log to dated files.

### Word Count Gate (`--auto`)
`get_rss_episode_date()` now returns `(date_str, youtube_url)`. After `get_show_notes()`, if word count < 500, automatically falls back to `get_barricade_intel(youtube_url)`. Exits cleanly (code 0) if no YouTube URL or transcript unavailable — not treated as a scheduler error.

### Barricade Cyber Pipeline (Choice 6 + `--auto-barricade`)
`get_barricade_intel(url)` — fetches YouTube transcripts via `YouTubeTranscriptApi().fetch()`. No yt-dlp, no Whisper. Wraps `VideoUnplayable` in a clean `RuntimeError`.

`get_barricade_latest()` — polls YouTube RSS feed for channel `UCLco-g6YIjhPqOBBR6CUXpg`. Loops up to 15 entries, probing each with `ytt.fetch()`. Any exception skips to the next entry. Returns `None` if newest playable entry already matches `barricade_last_ingested.txt`. Dedup file written by caller after successful `push_all()`.

### Simply Cyber YouTube Fallback (Choice 7)
Same flow as Choice 6 but pushes under source label `"Simply Cyber Daily Threat Brief"`. Used manually when the show notes page has insufficient content.

### `normalize_cid()` and `CMMC_MISSES`
`normalize_cid()` strips and normalizes control IDs before cache lookup, preventing whitespace/case misses. `CMMC_MISSES` accumulates unresolved IDs and prints a post-run miss report.

### `source_show` Canonical Values
`ANALYST_PROMPT` updated to enumerate the three permitted `source_show` values explicitly. `normalize_source_show.py` one-off utility retroactively fixes non-canonical values in CPE Tracker.

### `notion-client` Pin
Pinned to `==2.2.1` in `requirements.txt`. SDK async behavior changed in later versions.
