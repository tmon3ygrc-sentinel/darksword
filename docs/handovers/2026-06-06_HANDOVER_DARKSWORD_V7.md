# Handover Document — DARKSWORD GRC Intelligence Platform V7.0

**Project:** DARKSWORD  
**Engine:** `notion_logger_v7.py`  
**Handover Date:** 2026-06-06  
**Supersedes:** `2026-05-25_HANDOVER_GRC_OCEG_Logging.md` (V6 — retired)  
**Build ref:** `0f5f96c`  
**Status:** Production — all 8 choices operational

---

## 1. What This Document Is

The 2025-05-25 handover described V6 (`notion_logger_v.6.py`) and a VS Code workspace stabilisation session. That file is now historical. V7 is a complete rewrite and replacement. This document is the authoritative state record for the V7.0 pipeline as of 2026-06-06.

---

## 2. Pipeline Architecture

The V7 pipeline has a fixed four-stage shape regardless of which input source is used:

```
Source (show notes / RSS / YouTube / OTX feed)
  │
  ▼
scrub()                      — strips timestamps, removes injection markers
  │
  ▼
analyze_with_claude()        — or analyze_with_claude_prompt() for OTX
  │  (claude-sonnet-4-6, max_tokens=16000, ANALYST_PROMPT system prompt)
  ▼
write_governance_file()      — writes raw Claude output → governance_input.txt
  │
  ▼
parse_records()              — splits on ===INTEL_RECORD_START/END=== markers
  │
  ▼
push_record()  ×N            — pushes each record to Notion CPE Tracker DB
      │
      ├─► update_compliance_status()   — writes back to CMMC Master Frameworks DB
      └─► Learning plan auto-link      — relations to GRC Learning Plan DB
```

**Key structural decision in V7:** `get_show_notes()` replaced `get_transcript()` as the primary fetch path for Simply Cyber content. The YouTube audio pipeline (yt-dlp + Whisper + FFmpeg) is blocked at the network/IP level for Simply Cyber. `get_show_notes()` fetches the text-based show notes directly from `cyberthreatbrief.simplycyber.io` — zero audio, zero transcription cost, date-addressable.

### Notion Databases

| Database | Variable | UUID |
|----------|----------|------|
| CPE Tracker | `DATABASE_ID` | `30755ed7-4038-8039-a64e-c0eab4d4a06a` |
| CMMC Master Frameworks | `CMMC_DATABASE_ID` | *(env only — scrubbed from history)* |
| GRC Learning Plan | *(relation target)* | `2d655ed7-4038-8116-93c4-e0202647f640` |
| STAR Strategy | `DS_ID` in `threat_ingest.py` | `33855ed7-4038-80f6-a615-000b4bf49a40` |

### CMMC Cache

At startup, `load_cmmc_cache()` paginates `databases.query()` against `CMMC_DATABASE_ID` and loads all control IDs into `CMMC_CACHE` (dict: normalised CID → Notion page ID). If the cache is empty at push time, CMMC relation linking silently skips — check startup logs. Cache currently holds ~128 controls.

### Learning Plan Auto-Link

`push_record()` runs a three-step detect to auto-relate records to the GRC Learning Plan:

1. Explicit: reads `GRC_Learning_Plan_All_Phases` or `learning_phase` from the record.
2. Domain-map: matches `control_domains` values against `DOMAIN_TO_WEEKS`.
3. Category-map: matches `intel_category` values against `CATEGORY_TO_WEEKS`.

All three passes are deduplicated via `set()`. 29 weeks (non-consecutive; Week 1 through Week 36 with gaps) are loaded from `.env` as `LEARNING_WEEK_N` variables.

### Record Format

Records are delimited by `===INTEL_RECORD_START===` / `===INTEL_RECORD_END===` markers. Fields use `fieldname:: value` syntax (split on first `::` only — URLs with `://` do not break parsing). Multi-value fields are comma-separated. Placeholder values (`none`, `unknown`, `empty`, `n/a`) are silently skipped at push time — this is intentional, not a bug.

### Placeholder Skips (Silent — Not Bugs)

`push_record()` drops any field whose value (lowercased) is `none`, `unknown`, `empty`, or `n/a`. These are expected Claude outputs for fields where no information was available. Do not flag them as pipeline failures.

---

## 3. Pipeline Modes — All 8 Choices

The interactive menu is presented when `notion_logger_v7.py` is run with no flags (or with `--test`). The `--auto`, `--auto-otx`, and `--auto-barricade` flags bypass the menu entirely for scheduler use.

| Choice | Name | Data path | Notes |
|--------|------|-----------|-------|
| 1 | Autonomous Pipeline | `get_show_notes()` → Claude → Notion | Prompts for date (blank = today). Date-addressable: enter any past `YYYY-MM-DD` to backfill. Disabled in `--test` mode. |
| 2 | Manual Pipeline | `governance_input.txt` → Notion | User pastes AI output into `governance_input.txt` first, then presses ENTER. No Claude API call. |
| 3 | Test Pipeline | `governance_input.txt` → Notion | Only available when launched with `--test` flag. Reads existing `governance_input.txt` as mock data. $0.00 cost. Tests full Notion push path without any API call. |
| 4 | OTX Pipeline | AlienVault OTX API → Claude → Notion | Three-gate filter: time (last 24hrs), relevance tag set, deduplication. Requires `OTX_API_KEY` in `.env`. Uses `OTX_ANALYST_PROMPT` (derived from `ANALYST_PROMPT` with OTX-specific overrides). |
| 5 | RSS Feed Pipeline | Transistor RSS → `get_show_notes()` → Claude → Notion | Fetches pubDate from `feeds.transistor.fm/simply-cyber`, derives the episode date, then runs Choice 1 logic. Zero date prompts. |
| 6 | Barricade Cyber | YouTube URL → `get_barricade_intel()` → Claude → Notion | Manual URL entry. Uses `YouTubeTranscriptApi` (not yt-dlp/Whisper). Prompts for a Barricade Cyber YouTube URL. |
| 7 | Simply Cyber YouTube | YouTube URL → `get_barricade_intel()` → Claude → Notion | Same path as Choice 6 but labels records as "Simply Cyber Daily Threat Brief". Use when show notes are unavailable or too short. |
| 8 | Gemini YouTube Ingest | YouTube URL → `get_gemini_transcript()` → Claude → Notion | Sends URL directly to Gemini 2.0 Flash (no audio download). For restricted or long-form videos that `YouTubeTranscriptApi` cannot access. Requires `GEMINI_API_KEY`. Prompts for source label. |

### `--auto` Flag Behaviour (Choice 5 Logic)

`--auto` is the Task Scheduler entry point. It runs the Choice 5 flow non-interactively:

1. `get_rss_episode_date()` — reads pubDate from Transistor RSS feed.
2. `get_show_notes(date_str)` — fetches show notes for that date.
3. Word count gate: if show notes < 500 words, falls back to `get_barricade_intel()` using YouTube URL from RSS feed. If no YouTube URL in feed, scrapes episode page. If that also fails, exits cleanly (not an error).
4. `analyze_with_claude()` → `write_governance_file()` → `parse_records()` → `push_all()`.

All `--auto-*` flags follow the same non-interactive pattern with their respective source logic.

---

## 4. Task Scheduler Tasks (Three)

All three scripts live in the repo root and follow the same structure: set `$ScriptDir` and `$Python` as hardcoded paths, configure UTF-8 encoding three ways (`$env:PYTHONIOENCODING`, `$OutputEncoding`, `[Console]::OutputEncoding`), then invoke the Python engine with a mode flag.

**⚠️ Path dependency:** All three scripts hardcode `C:\Work\GRC-OCEG\darksword` and `C:\Work\GRC-OCEG\.venv`. If the parent directory is renamed, all three scripts must be updated before the next scheduler run.

### `run_darksword_auto.ps1` — Simply Cyber Daily (weekdays, 9 AM)

```
Flag:    --auto
Log:     darksword_YYYY-MM-DD.log
Source:  Simply Cyber via Transistor RSS + cyberthreatbrief.simplycyber.io
```

Primary scheduled task. Runs Choice 5 logic. On a clean run: RSS date detect → show notes fetch → Claude analysis → Notion push. On show notes failure: falls back to YouTube transcript. Exits 0 on success; exits non-zero on unhandled exception (Task Scheduler will mark the task as failed).

### `run_darksword_barricade.ps1` — Barricade Cyber

```
Flag:    --auto-barricade
Log:     darksword_barricade_YYYY-MM-DD.log
Source:  Barricade Cyber YouTube channel RSS
```

Polls the Barricade Cyber YouTube channel RSS feed (up to 15 entries). Compares latest video ID against `barricade_last_ingested.txt`. If the newest ingestable entry matches the stored ID, exits cleanly with no push. On a new video: fetches transcript via `YouTubeTranscriptApi`, runs Claude analysis, pushes to Notion, then writes the new video ID to `barricade_last_ingested.txt`. Schedule is separate from `run_darksword_auto.ps1`.

### `run_darksword_otx.ps1` — AlienVault OTX

```
Flag:    --auto-otx
Log:     darksword_otx_YYYY-MM-DD.log
Source:  AlienVault OTX API (subscribed pulses, last 24hrs)
```

Fetches OTX pulses modified in the last 24 hours, applies the three-gate filter (time, relevance tags, deduplication), then runs each pulse through Claude using `OTX_ANALYST_PROMPT`. All records from all pulses are batched and pushed together. If no relevant pulses are found, exits cleanly. Requires `OTX_API_KEY` in `.env`.

---

## 5. Agent Roster

Five agent briefings live in `.claude/` and are committed to git (`.gitignore` has a `!.claude/*.md` exception). Each briefing contains a "Current System State" section that should be updated when described behaviour changes.

| Agent | Briefing File | Primary Responsibility |
|-------|--------------|----------------------|
| **ARCHITECT** | `CLAUDE.md` (repo root) | System design, all 8 choices, record schema, Notion DB mapping, cross-cutting decisions, new features. Default agent identity. |
| **SENTINEL** | `.claude/SENTINEL.md` | Runtime error diagnosis, log analysis, `failed_records.txt` triage, Notion API error tracing, `--auto` anomalies. First responder when the pipeline breaks. |
| **AUDITOR** | `.claude/AUDITOR.md` | `.gitignore`, `.env`/`.env.example` hygiene, `requirements.txt` CVE review, git history secrets scan, commit signing, pre-push checklist. |
| **SCRIBE** | `.claude/SCRIBE.md` | `README.md`, `script_walkthrough_.md`, session handovers (this file), agent briefing prose updates. Does not debug or make security judgments. |
| **RECON** | `.claude/RECON.md` | External endpoint health, GitHub attack surface, dependency CVE enumeration, API key exposure audit. Passive/assessment only — does not fix. |

### Handoff Logic (Summary)

The Architect is the default and tie-breaker. Route to agents as follows:

- Pipeline raises an exception or produces wrong output → **SENTINEL**
- New dependency, `.env` change, pre-push review → **AUDITOR**
- New external endpoint or dependency CVE scan → **RECON**
- New pipeline choice, README update, end-of-session handover → **SCRIBE**
- Any agent finds a structural fix needed → return to **ARCHITECT**

---

## 6. Dependencies

`requirements.txt` (as of this handover):

```
notion-client>=2.2.1
python-dotenv>=1.0.1
feedparser>=6.0.8
google-generativeai>=0.7.0    ← ⚠️  WRONG PACKAGE (see Known Gaps)
```

**Additional runtime imports** (used conditionally, not in `requirements.txt`):

| Package | Used by | Required for |
|---------|---------|-------------|
| `requests` | `notion_logger_v7.py` | Show notes HTTP fetch (Choices 1, 5, 7) |
| `beautifulsoup4` | `notion_logger_v7.py` | HTML parsing of show notes pages |
| `anthropic` | `notion_logger_v7.py` | Claude API client (all live choices) |
| `OTXv2` | `notion_logger_v7.py` | AlienVault OTX API (Choice 4) |
| `youtube-transcript-api` | `notion_logger_v7.py` | YouTube transcript fetch (Choices 6, 7, `--auto-barricade`) |
| `google-genai` | `notion_logger_v7.py`, `gemini_ingest_tool.py` | Gemini API client (Choice 8) |
| `yt-dlp` | `notion_logger_v7.py` | Legacy `get_transcript()` — blocked for Simply Cyber, retained for future sources |
| `openai-whisper` | `notion_logger_v7.py` | Legacy Whisper transcription — same caveat as yt-dlp |

**Venv:** `C:\Work\GRC-OCEG\.venv` — shared across all projects under `C:\Work\GRC-OCEG\`.

---

## 7. Key Files

| File | Role |
|------|------|
| `notion_logger_v7.py` | Main engine — all 8 choices, `--auto`/`--auto-otx`/`--auto-barricade` flags, all pipeline logic |
| `gemini_ingest_tool.py` | Standalone Gemini transcription tool; also called internally by Choice 8 |
| `threat_ingest.py` | One-off STAR Strategy DB ingest; writes to STAR Strategy Notion DB (`DS_ID`) |
| `governance_input.txt` | Working file — parser reads from here; overwritten each run (gitignored) |
| `failed_records.txt` | Append-only failure log — check first on any Notion push error (gitignored) |
| `barricade_last_ingested.txt` | Stores last-ingested Barricade video ID; prevents duplicate pushes (gitignored) |
| `run_darksword_auto.ps1` | Task Scheduler wrapper — Simply Cyber daily |
| `run_darksword_barricade.ps1` | Task Scheduler wrapper — Barricade Cyber |
| `run_darksword_otx.ps1` | Task Scheduler wrapper — AlienVault OTX |
| `prompts/cpe_prompt_claude.txt` | Canonical prompt for manual Claude chat sessions (not used by the automated pipeline) |
| `prompts/cpe_prompt_gemini.txt` | Canonical prompt for manual Gemini chat sessions |
| `good_example_template.txt` | Gold-standard record examples + valid field values; reference for prompt tuning |
| `script_walkthrough_.md` | Code walkthrough — V6.1 core + V7 addenda per session |
| `.env` | Live secrets — never commit, never log |
| `.env.example` | Safe template — placeholders only; real `CMMC_DATABASE_ID` scrubbed from history (`git filter-repo`, 2026-05-30) |
| `Scheduled/darksword-daily-status/SKILL.md` | Claude scheduled task — reads today's log and produces a daily ops digest |

---

## 8. Known Gaps and Pending Actions

### Critical

**`requirements.txt` lists wrong Google SDK.** Line 4 reads `google-generativeai>=0.7.0`. The SDK was migrated to `google-genai` at commit `2a35fa4`. The engine imports `from google import genai` which requires `google-genai`, not `google-generativeai`. This should be corrected to `google-genai>=0.3.0` (verify installed version with `pip show google-genai` in the venv). Delegate to AUDITOR.

### Hygiene

**`notion_logger_v.6.py` is still git-tracked.** V6 is entirely superseded by V7. The file should be removed with `git rm notion_logger_v.6.py`. Confirm with Architect before executing — AUDITOR owns the git operation.

**`arch_update.txt` on disk is stale.** Describes V5 architecture (filter_dtb_transcript.py, "AI Strike Team"). Not tracked but present. Safe to delete.

**`prompts/cpe_prompt_chatgpt.txt` is dead weight.** No V7 pipeline choice invokes a ChatGPT path. Safe to delete.

**`strategy_import.csv` appears to be a one-time import artifact.** Not referenced by any active script. Confirm data is in Notion before deleting.

### Path Risk

All three PS1 scheduler scripts and `Scheduled/darksword-daily-status/SKILL.md` hardcode `C:\Work\GRC-OCEG\`. If the parent directory is ever renamed, these will break immediately at the next scheduled run. `.claude/settings.local.json` (gitignored, local only) also contains 10+ Bash allowlist entries with the same path — must be updated manually on the machine.

### Known Pipeline Limitations

- `get_transcript()` (yt-dlp + Whisper) is blocked at the network/IP level for Simply Cyber. Use `get_show_notes()` (Choice 1/5) or `get_barricade_intel()` (Choice 7) instead.
- Show notes are published after episode release. Early AM `--auto` runs (within ~30 min of episode drop) may find no episode page yet and exit with a `RuntimeError`. This is expected; the scheduler will catch it on the next run or the word count gate will fall back to YouTube.
- `CMMC_DATABASE_ID` is not in `.env.example`. Any new machine setup requires the real UUID to be added to `.env` manually. The value was scrubbed from git history on 2026-05-30 via `git filter-repo`. Backup bundle: `C:\Work\GRC-OCEG\darksword_backup_before_filterrepo_20260530.bundle` (local only).
- `threat_ingest.py` is a standalone script with hardcoded example items — it is not integrated into the main menu. Run manually to push STAR Strategy entries.

### What's Next (Architect Backlog)

- Fix `requirements.txt`: replace `google-generativeai` with `google-genai`.
- `git rm notion_logger_v.6.py` after Architect confirmation.
- Evaluate whether Barricade and OTX scheduler tasks need consolidated logging (currently three separate log filename patterns).
- Consider a retry mechanism for the `--auto` word count gate to avoid missed episodes on early-morning runs.

---

*Produced by SCRIBE — 2026-06-06*
