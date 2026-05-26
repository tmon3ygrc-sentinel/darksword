# ⚔️ DARKSWORD — Script Walkthrough
**notion_logger_v.6.py — Complete Reference**

> This document explains every section of the DARKSWORD pipeline so you own the code, not just run it.
> Last updated: V6.1 — Post-Backlog Session (Auto Learning Plan Mapping + Field Validation)

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
13. [Valid Field Values Reference](#13-valid-field-values-reference)
14. [Key Concepts Reference](#14-key-concepts-reference)
15. [Change Log — V6.0 → V6.1](#15-change-log--v60--v61)

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

### LEARNING_CACHE

```python
LEARNING_CACHE = {
    "Week 1":  os.getenv("LEARNING_WEEK_1",  ""),
    "Week 2":  os.getenv("LEARNING_WEEK_2",  ""),
    ...
    "Week 36": os.getenv("LEARNING_WEEK_36", ""),
}
```
A **dictionary** mapping week labels to Notion page IDs. Keys are what gets matched during auto-detection (`"Week 23"`), values are the Notion page IDs stored in `.env`. Loaded from environment variables so IDs stay out of source code.

**Current weeks loaded:** 1, 2, 3, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 33, 35, 36

---

### DOMAIN_TO_WEEKS *(new in V6.1)*

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
Maps each CMMC control domain to the most relevant learning plan week(s). A single domain can map to multiple weeks — `"Supply Chain Risk Management (SR)"` maps to both Week 19 (Threat Modeling) and Week 29 (Continuous Compliance Monitoring).

---

### CATEGORY_TO_WEEKS *(new in V6.1)*

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

### CMMC_CACHE

```python
CMMC_CACHE: Dict[str, str] = {}
```
An **empty dictionary** that starts empty and gets filled at runtime by `load_cmmc_cache()`. Dynamic because Notion won't give you page IDs automatically — it has to query them fresh each session. Currently holds 128 controls. The `: Dict[str, str]` type hint says it maps strings to strings.

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

> **Important:** `identity_impact` and `impacted_identity_provider` are both in `MULTI_SELECT_FIELDS`. Values must be short tags from the Notion dropdown — not sentences. See Section 13 for valid values.

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
Fields the main loop **completely ignores** — either hardcoded in the `props` block, or handled separately in the relation logic below the loop. Without this, the loop would try to process them as regular fields and format them incorrectly.

---

## 5. Analyst System Prompt

```python
ANALYST_PROMPT = """
### MISSION OBJECTIVE
...
"""
```
A multi-line string sent to Claude as the **system message** — the standing orders that shape every response. It defines the output schema, field definitions, story identification rules, valid field values, and validation steps. Claude reads this before it sees any transcript.

This is what makes Claude output perfectly structured `fieldname:: value` records instead of prose. The prompt is the contract between your script and the AI.

**Key prompt rules:**
- `identity_impact` and `impacted_identity_provider` must use **short comma-separated tags** from the Notion dropdown, not sentences
- `GRC_Learning_Plan_All_Phases` can now be left blank — the script auto-detects it
- `threat_actor` set to `unknown` will show as empty in Notion (skipped by the skip filter on line 412)

---

## 6. Utility Functions

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

**What it deliberately keeps:** anything in brackets like `[CVE-2024-1234]`, `[MITRE T1190]`, `[CISA KEV]`. An earlier version stripped all bracket content with `re.sub(r'\[.*?\]', '', text)` which destroyed threat intelligence. That regex was removed.

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

> **Known limitation:** Some channels (including Simply Cyber) block automated transcript access at the network/IP level. yt-dlp and cookie-based workarounds were attempted and confirmed blocked. The Manual Pipeline exists specifically for this reason.

---

```python
def analyze_with_claude(transcript: str, url: str, today: str) -> str:
```
Sends the cleaned transcript to Claude with the `ANALYST_PROMPT` as the system message. `max_tokens=8000` gives Claude enough room to generate multiple full intel records. Returns the raw text output.

---

```python
def load_mock_data() -> str:
```
**Test Mode only.** Reads your existing `governance_input.txt` and returns it as if it just came from Claude. Costs $0.00. The entire point is to let you test the Notion push logic independently from the API call.

---

```python
def write_governance_file(content: str):
```
Writes Claude's output to `governance_input.txt`. This is the handoff point between the Claude pipeline and the Notion push pipeline.

---

## 8. Notion Functions

```python
def load_cmmc_cache():
```
Queries your CMMC Notion database and builds `CMMC_CACHE` in memory. Currently loads **128 controls**.

**Pagination:** Notion returns max 100 results per query. The `while has_more` loop keeps fetching pages until it has all of them.

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
The GRC write-back. After a record is pushed to the CPE Tracker, this loops through the CMMC control IDs and updates each one in your CMMC Master Frameworks database — stamping it as `"Evidence Pending"` and linking back to the source record. This is your audit evidence trail.

---

## 9. The Engine — push_record()

```python
def push_record(record: dict, source_label: str, url: str) -> bool:
```
Takes the parsed record dictionary and builds the full Notion API payload. Returns `True` or `False` so the caller knows if it succeeded.

---

### Base Properties

```python
props = {
    "Title":        {"title": [{"text": {"content": page_title}}]},
    "url":          {"url": url} if url else {},
    "date_watched": {"date": {"start": date.today().isoformat()}},
    "cpe_credits":  {"number": 0.5},
}
```
These four fields are set identically every run regardless of what's in your `.txt` file. Note `{"url": url} if url else {}` — passing an empty dict instead of `None` prevents the Notion API from rejecting a null URL value.

---

### Field Routing Loop

```python
for key, val in record.items():
    if key in SKIP_FIELDS or not val: continue
    if str(val).lower() in ("none", "unknown", "empty", "n/a"): continue
```
Two skip conditions: field is in SKIP_FIELDS, OR the value is a placeholder string. This prevents pushing `"None"` or `"Unknown"` into Notion as real data.

> **Side effect:** `threat_actor:: unknown` will show as **empty** in Notion. This is intentional and acceptable behavior — unknown attribution should not appear as a tag.

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
Routes each field to the correct Notion format. The `except (ValueError, TypeError)` on number conversion is **specific** — it only catches bad number conversions, not everything.

---

### CMMC Relation

```python
cmmc_raw = (
    record.get("Master Frameworks(CMMC 2.0 / NIST 800-171)", "") or
    record.get("cmmc_mapping", "")
)
```
**Compatibility bridge.** Tries the full Notion column name first, falls back to the short key. The `or` operator returns the first truthy value — if the first `.get()` returns empty string (falsy), it tries the second. Supports both pipeline modes.

---

### Learning Plan Relation *(rewritten in V6.1)*

```python
# === Learning Plan Relation (Auto-detect from content) ===
linked_weeks = set()

# 1. Explicit override from record
learning_raw = (
    record.get("GRC_Learning_Plan_All_Phases", "") or
    record.get("learning_phase", "")
)
if learning_raw:
    phase_key = re.split(r'\s[–-]\s', learning_raw)[0].strip()
    if phase_key in LEARNING_CACHE:
        linked_weeks.add(phase_key)

# 2. Auto-map from control_domains
domains_raw = record.get("control_domains", "") or ""
for domain in [d.strip() for d in domains_raw.split(",")]:
    for week in DOMAIN_TO_WEEKS.get(domain, []):
        linked_weeks.add(week)

# 3. Auto-map from intel_category
cats_raw = record.get("intel_category", "") or ""
for cat in [c.strip() for c in cats_raw.split(",")]:
    for week in CATEGORY_TO_WEEKS.get(cat, []):
        linked_weeks.add(week)

# Push all matched weeks as relations
if linked_weeks:
    relation_ids = [
        {"id": LEARNING_CACHE[w]}
        for w in sorted(linked_weeks)
        if w in LEARNING_CACHE and LEARNING_CACHE[w]
    ]
    if relation_ids:
        props["GRC_Learning_Plan_All_Phases"] = {"relation": relation_ids}
```

**Three-step auto-detection logic:**

1. **Explicit override** — if `GRC_Learning_Plan_All_Phases` is set in the record, honor it. Parses `"Week 27 – Audit trails"` into just `"Week 27"` using the em dash split.

2. **Domain mapping** — splits `control_domains` on commas, looks each one up in `DOMAIN_TO_WEEKS`, adds all matched weeks to the set.

3. **Category mapping** — splits `intel_category` on commas, looks each one up in `CATEGORY_TO_WEEKS`, adds all matched weeks to the set.

The result is a **deduplicated set** of week labels. The final list comprehension filters out any weeks not in `LEARNING_CACHE` or with empty IDs, then pushes all of them as a multi-relation to Notion. A single record can link to 5+ learning weeks automatically.

---

### Notion Create

```python
response = notion.pages.create(
    parent={"database_id": DATABASE_ID},
    properties=props
)
```
The actual Notion API call. `parent={"database_id": DATABASE_ID}` is the correct format — not `"data_source_id"`, not `"type"`. This creates the record in your CPE Tracker database.

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
Splits each record into lines, then splits each line on `::`. The `1` argument means "split on the first `::` only" — so values that contain `::` (like URLs or timestamps) don't break the parser.

---

## 11. Main — Control Loop

```python
while True:
```
**Infinite loop** — keeps the menu alive until you explicitly choose Exit.

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
Option 1 is double-locked. `continue` skips back to the top of the loop without running the rest of the block.

---

```python
except (RuntimeError, ValueError) as e:
    print(f"❌ Pipeline failed: {e}")
    continue
```
Only catches `RuntimeError` (from `get_transcript()`) and `ValueError` (from `extract_video_id()`). Fails gracefully and returns to the menu.

---

## 12. Running The Two Modes

```bash
# Free — debug all day, $0.00
python notion_logger_v.6.py --test

# Live — full pipeline
python notion_logger_v.6.py
```

### Test Mode menu
```
⚔️   DARKSWORD — GRC Intelligence Platform V6.0
     💡 TEST MODE  |  $0.00  |  API Disconnected

1. Autonomous Pipeline  ← disabled
2. Manual Pipeline
3. Test Pipeline
0. Exit
```

### Live Mode menu
```
⚔️   DARKSWORD — GRC Intelligence Platform V6.0
     🔴 LIVE MODE  |  API Connected

1. Autonomous Pipeline  (YouTube → Claude → Notion)
2. Manual Pipeline      (governance_input.txt → Notion)
0. Exit
```

### Manual Pipeline workflow
1. Go to YouTube video → open transcript → toggle timestamps off → copy all text
2. Paste transcript into Claude chat
3. Claude generates `===INTEL_RECORD_START===` formatted records
4. Copy records into `governance_input.txt`
5. Run `cpe` → select **2. Manual Pipeline** → enter real YouTube URL
6. Records push to Notion CPE Tracker with CMMC linking and auto learning plan mapping

---

## 13. Valid Field Values Reference

All multi-select fields must use **exact values** from the Notion dropdown. The script skips values not in the dropdown — they show as empty rather than erroring.

### threat_actor
`unknown`, `unknown financially motivated operators`, `nation-state-unknown`, `ShinyHunters`, `Salt Typhoon (China-linked nation-state)`, `Russian State Actors`, `muddy-water`, `volt-typhoon`, `Lazarus Group`, `Various Ransomware Operators`, `Ransomware Affiliates`, `transnational cybercrime organizations`, `Russia-linked proxy infrastructure operators`, `insider-threat-accidental`, `(no claim of responsibility)`, `Iranian state-nexus actors`, `Konni Group (North Korea-linked)`

> **Note:** `unknown` is skipped by the script's placeholder filter and will show as empty in Notion. This is correct behavior.

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
| `sys.argv` | Words typed when running the script | `--test` flag detection |
| `.get(key, default)` | Safe dictionary lookup, no crash if missing | Every `record.get()` call |
| `or` chaining | Returns first truthy value | CMMC/Learning Plan compatibility bridge |
| `re.DOTALL` | Makes regex `.` match newlines | `parse_records` block extraction |
| `**kwargs` | Unpacks dictionary as function arguments | Pagination in `load_cmmc_cache()` |
| `break` | Exits a loop immediately | Exit menu option |
| `continue` | Skips current loop iteration to next | SKIP_FIELDS check, TEST_MODE lock |
| Specific exceptions | Catching only expected error types | Number conversion, pipeline errors |
| Non-greedy `.*?` | Regex match as few chars as possible | Block extraction between markers |
| `set()` deduplication | Automatically removes duplicates | `linked_weeks` — prevents duplicate week relations |
| `sorted()` | Alphabetical sort | Ensures consistent week ordering in Notion |

---

## 15. Change Log — V6.0 → V6.1

### Field Mapping Fixes
- `impacted_identity_provider` — was missing from all field sets entirely. Added to `MULTI_SELECT_FIELDS`. Previously caused silent failures with no Notion output.
- `identity_impact` — confirmed as `MULTI_SELECT_FIELDS`. Values must be short tags, not sentences.
- All multi-select field values validated against live Notion dropdown options via API query.

### Learning Plan — Complete Rewrite
**Before (V6.0):** Single relation. Read `GRC_Learning_Plan_All_Phases` field from record, looked up one week in `LEARNING_CACHE`, pushed one relation ID. Required manual week specification in every record.

**After (V6.1):** Multi-relation auto-detection. Three-step engine:
1. Honor explicit field value if present
2. Auto-map from `control_domains` using `DOMAIN_TO_WEEKS`
3. Auto-map from `intel_category` using `CATEGORY_TO_WEEKS`

Results deduplicated via `set()`, sorted, and pushed as a multi-relation. A single record now links to 3–6 relevant learning weeks automatically with zero manual input.

`LEARNING_CACHE` expanded from 3 weeks (25, 26, 27) to 29 weeks covering the full GRC learning journey.

### CMMC Cache
- `SR.L2-3.15.2` (Supply Chain Risk Management: Notification of Supply Chain Compromise) added to Master Frameworks Notion DB
- Cache now at 128 controls

### Database IDs

| Database | Script Variable | Notion ID |
|---|---|---|
| CPE Tracker | `DATABASE_ID` | `30755ed7-4038-8039-a64e-c0eab4d4a06a` |
| CMMC Master Frameworks | `CMMC_DB_ID` | `32a55ed7-4038-80b3-96e0-de9386a76ff7` |
| GRC Learning Plan | *(relation target)* | `2d655ed7-4038-8116-93c4-e0202647f640` |

### Learning Plan Week IDs

| Week | Topic | Notion Page ID |
|---|---|---|
| Week 1 | What is GRC? | `2d655ed7-4038-81b3-83f0-c4f0697d18da` |
| Week 2 | Roles of a GRC Analyst | `2d655ed7-4038-8159-9453-ec60768b5a9e` |
| Week 3 | Maturity Models | `2d655ed7-4038-819a-9a12-e0eea331349d` |
| Week 5 | Org Structures & Stakeholders | `2d655ed7-4038-81c9-92b6-ddcb3452c4b2` |
| Week 6 | Strategic Alignment | `2d655ed7-4038-8163-806c-e374048b9e33` |
| Week 7 | GRC Terminology | `2d655ed7-4038-815b-9fd6-e8c99e997a3f` |
| Week 8 | NIST CSF | `2d655ed7-4038-8167-b496-d84986183bc7` |
| Week 10 | Defining Governance Objectives | `2d655ed7-4038-81fa-97aa-d98b6972cf52` |
| Week 11 | Governance Maturity Self-Assessment | `2d655ed7-4038-8143-90a9-c9ccd5334ddc` |
| Week 12 | Policies and Procedures (P&P) Lifecycle | `2d655ed7-4038-8142-9a13-c126048dd3b2` |
| Week 13 | Role of Governance in Audit and Control | `2d655ed7-4038-81ac-afa7-e5e568d0ed7b` |
| Week 14 | Leadership and Decision-Making | `2d655ed7-4038-81a9-a860-f3651e4bc48d` |
| Week 15 | Aligning Governance to Business Goals | `2d655ed7-4038-816d-a96b-f808e0eb3561` |
| Week 17 | Risk Management Principles (ISO 31000) | `2d655ed7-4038-8185-af2c-ec30f79da226` |
| Week 18 | Risk Identification & Categorization | `2d655ed7-4038-81f8-b1d4-eedeaf9b6370` |
| Week 19 | Threat Modeling & Business Impact Analysis | `2d655ed7-4038-8178-aed7-c43a9a04f447` |
| Week 20 | Risk Analysis: Qualitative vs. Quantitative | `2d655ed7-4038-815a-92f5-ead7acef3e2d` |
| Week 21 | Risk Response & Mitigation Planning | `2d655ed7-4038-81b5-ada3-c3187c2043be` |
| Week 23 | Incident Detection & Investigation | `2d655ed7-4038-8136-9d0b-e30d7fb0d347` |
| Week 24 | Risk Maturity Assessment | `2d655ed7-4038-819c-862d-fda30747c460` |
| Week 25 | Regulatory Landscape: Laws & Frameworks | `2d655ed7-4038-8178-af99-d35ef1ba8c60` |
| Week 26 | Building Compliance Programs | `2d655ed7-4038-81ff-b921-d8538a552713` |
| Week 27 | Audit Trails & Documentation Practices | `2d655ed7-4038-811b-88f7-f71eb26aaa36` |
| Week 28 | Internal vs. External Audits | `2d655ed7-4038-8196-aea2-f2b1977bf0f3` |
| Week 29 | Continuous Compliance Monitoring | `2d655ed7-4038-81d4-9ab2-fafcf661c040` |
| Week 30 | Reporting & Stakeholder Engagement | `2d655ed7-4038-8127-b8ac-f84e5235ade2` |
| Week 33 | What is Integrated GRC? | `2d655ed7-4038-81d1-aadd-e7533308bb3d` |
| Week 35 | Building GRC Roadmaps | `2d655ed7-4038-818b-a731-c3f7b76383cd` |
| Week 36 | Developing Metrics & KPIs | `2d655ed7-4038-8171-9018-fe8f3fd34e73` |