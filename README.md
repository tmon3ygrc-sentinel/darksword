# ⚔️ Project DARKSWORD — GRC Intelligence Platform

**Threat Intelligence → CMMC 2.0 Gap Analysis — Automated**

A multi-source intelligence pipeline that ingests daily security content from show notes, threat feeds, and YouTube, classifies it using Claude AI, maps it against **CMMC 2.0 / NIST 800-171** controls, links records to a live GRC learning plan, and pushes structured records into a Notion GRC repository.

Built as part of the **STAR Project** (Self-Transformation through Adversarial Rigor) — a hands-on vCISO development program. Manual mastery first, automation second.

Current build: `fe2fbe0`

---

## Why DARKSWORD

The asymmetry is real.

Nation-state actors and ransomware operators are already leveraging AI to scale attacks, accelerate reconnaissance, and craft more convincing social engineering — at a pace no human analyst can match alone.

DARKSWORD exists to close that gap.

A solo GRC analyst with a spreadsheet isn't a fair fight against an AI-augmented adversary. But a GRC analyst running an autonomous intelligence pipeline that ingests multiple threat feeds daily, maps every story to CMMC 2.0 controls, maintains a living audit trail, and surfaces critical threat intensity across 131 controls — that's a different posture entirely.

This project is proof that defenders can use the same technology to build leverage. Not to replace analyst judgment — but to amplify it.

The threat actors aren't waiting. Neither should you.

---

## Architecture

```
Simply Cyber (show notes / YouTube)     AlienVault OTX (feed)     Barricade Cyber (YouTube)
              ↓                                   ↓                         ↓
  get_show_notes() [primary]            get_otx_pulses()          get_barricade_latest() [RSS]
  get_barricade_intel() [<500w fallback]         ↓                get_barricade_intel() [transcript]
              ↓                    analyze_with_claude_prompt()             ↓
  analyze_with_claude()              (OTX_ANALYST_PROMPT)        analyze_with_claude()
              ↓                                   ↓                         ↓
              └───────────────────────────────────┘─────────────────────────┘
                                          ↓
                               governance_input.txt
                                          ↓
                               notion_logger_v7.py
                                [DARKSWORD Engine]
                                          ↓
                                   CPE Tracker DB
                                    ↙         ↘
                    Master Frameworks DB     GRC Learning Plan DB
                      (CMMC 2.0)              [Auto-linked by content]
```

### Databases (Notion)

| Database | Script | Source | Purpose |
|---|---|---|---|
| CPE Tracker | `notion_logger_v7.py` | Simply Cyber, AlienVault OTX, Barricade Cyber | Tactical threat intel |
| STAR Strategy | `threat_ingest.py` | Barricade Cyber (legacy engine) | Strategic architecture |
| Master Frameworks | shared | CMMC 2.0 | Control mapping (source of truth) |
| GRC Learning Plan | shared | Internal | Auto-linked from control domains |

---

## Workspace Structure

```
STAR_PROJECT (GRC-OCEG)
└── darksword/
    ├── notion_logger_v7.py           ← DARKSWORD core engine (V7)
    ├── threat_ingest.py              ← Barricade engine (legacy)
    ├── run_darksword_auto.ps1        ← Task Scheduler: Simply Cyber daily
    ├── run_darksword_otx.ps1         ← Task Scheduler: AlienVault OTX
    ├── run_darksword_barricade.ps1   ← Task Scheduler: Barricade Cyber
    ├── gemini_ingest_tool.py         ← Standalone Gemini YouTube transcription tool
    ├── governance_input.txt          ← Working file (gitignored)
    ├── barricade_last_ingested.txt   ← Barricade dedup state (gitignored)
    ├── failed_records.txt            ← Failed push log
    ├── prompts/                      ← Analyst prompt library
    ├── archive/                      ← Legacy scripts
    ├── GRC-Playground/               ← Experimental work
    ├── GovSCH/                       ← Governance scheduler
    ├── .env                          ← API keys (gitignored)
    ├── requirements.txt
    ├── README.md
    └── script_walkthrough_.md        ← Full code walkthrough
```

---

## Pipeline Modes

### DARKSWORD (`notion_logger_v7.py`)

```bash
cpe   # launches via alias
```

#### Interactive menu

| Choice | Description | Source Label |
|---|---|---|
| `1. Autonomous Pipeline` | Show Notes → Claude → Notion (prompts for date) | Simply Cyber Daily Threat Brief |
| `2. Manual Pipeline` | `governance_input.txt` → Notion | *(user-specified)* |
| `3. Test Pipeline` | Mock data → Notion (`$0.00`, `--test` flag only) | — |
| `4. OTX Pipeline` | AlienVault OTX → Claude → Notion | AlienVault OTX |
| `5. RSS Feed Pipeline` | RSS auto-detect date → Show Notes → Claude → Notion | Simply Cyber Daily Threat Brief |
| `6. Barricade Cyber` | YouTube URL → Transcript → Claude → Notion | Barricade Cyber |
| `7. Simply Cyber YouTube` | YouTube URL → Transcript → Claude → Notion | Simply Cyber Daily Threat Brief |
| `8. Gemini YouTube Ingest` | YouTube URL → Gemini transcript → Claude → Notion | *(user-selected)* |

Choice 7 is the show notes fallback — same flow as Choice 6 but tagged as Simply Cyber. Use it when the show notes page hasn't published yet or has insufficient content.

Choice 8 uses the Gemini API (`gemini-2.0-flash`) to transcribe YouTube videos that `YouTubeTranscriptApi` cannot access — restricted, age-gated, or long-form content. Prompts for a canonical source label. Requires `GEMINI_API_KEY` in `.env`. `gemini_ingest_tool.py` is the equivalent standalone script.

#### Non-interactive flags (Task Scheduler)

| Flag | Pipeline | Log file |
|---|---|---|
| `--auto` | RSS date detect → show notes → Claude → Notion (with <500-word YouTube fallback) | `darksword_YYYY-MM-DD.log` |
| `--auto-otx` | AlienVault OTX → Claude → Notion | `darksword_otx_YYYY-MM-DD.log` |
| `--auto-barricade` | Barricade RSS → transcript → Claude → Notion (with restricted-video fallback + dedup) | `darksword_barricade_YYYY-MM-DD.log` |

Flags are mutually exclusive. `--test` is also mutually exclusive with all auto flags.

#### Word count gate (`--auto`)

After `get_show_notes()` returns, the script counts words. If the result is below 500:
1. Prints a warning with the actual word count
2. Extracts the YouTube URL from the same RSS entry
3. Falls back to `get_barricade_intel()` to fetch the YouTube transcript
4. Continues the Claude/Notion pipeline with the transcript as content
5. If no YouTube URL was in the RSS entry, or the transcript fetch fails, exits cleanly (code 0)

---

## Quick Start

```bash
git clone https://github.com/tmon3ygrc-sentinel/darksword.git
cd darksword
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```env
# Core
NOTION_TOKEN=secret_...
DATABASE_ID=...                  # CPE Tracker
CMMC_DATABASE_ID=...             # Master Frameworks
ANTHROPIC_API_KEY=sk-ant-...
OTX_API_KEY=...                  # AlienVault OTX (for Choice 4 / --auto-otx)
GEMINI_API_KEY=...               # Gemini API (for Choice 8 / gemini_ingest_tool.py)

# Learning Plan Weeks
LEARNING_WEEK_1=...
LEARNING_WEEK_2=...
LEARNING_WEEK_3=...
LEARNING_WEEK_5=...
LEARNING_WEEK_6=...
LEARNING_WEEK_7=...
LEARNING_WEEK_8=...
LEARNING_WEEK_10=...
LEARNING_WEEK_11=...
LEARNING_WEEK_12=...
LEARNING_WEEK_13=...
LEARNING_WEEK_14=...
LEARNING_WEEK_15=...
LEARNING_WEEK_17=...
LEARNING_WEEK_18=...
LEARNING_WEEK_19=...
LEARNING_WEEK_20=...
LEARNING_WEEK_21=...
LEARNING_WEEK_23=...
LEARNING_WEEK_24=...
LEARNING_WEEK_25=...
LEARNING_WEEK_26=...
LEARNING_WEEK_27=...
LEARNING_WEEK_28=...
LEARNING_WEEK_29=...
LEARNING_WEEK_30=...
LEARNING_WEEK_33=...
LEARNING_WEEK_35=...
LEARNING_WEEK_36=...
```

Set the `cpe` alias in `~/.bashrc`:

```bash
alias cpe='cd /c/Work/GRC-OCEG/darksword && /c/Work/GRC-OCEG/.venv/Scripts/python.exe notion_logger_v7.py'
```

### Key dependencies

`notion-client` is pinned to `==2.2.1` in `requirements.txt`. The Notion SDK's async behavior changed in later versions in ways that break the synchronous pipeline. Do not upgrade without testing.

`google-genai` is required for Choice 8 and `gemini_ingest_tool.py`. Install with `pip install google-genai`. Uses `gemini-2.0-flash` via `client.models.generate_content()` with `types.Part.from_uri()` for YouTube URL passing.

---

## Intelligence Sources

| Source | Channel | Focus | Status |
|---|---|---|---|
| Simply Cyber | Show Notes | Daily tactical threat briefs | ✅ Live (auto + interactive) |
| AlienVault OTX | Threat Feed | IOC feeds, pulse intelligence | ✅ Live (auto + interactive) |
| Barricade Cyber | YouTube | DFIR, MSP/enterprise ops | ✅ Live (auto + interactive) |
| Cybernews | YouTube | Threat actor profiles, geopolitical | Planned |

---

## Task Scheduler

Three Windows Task Scheduler tasks run `notion_logger_v7.py` non-interactively on a daily schedule:

| Task | Script | Trigger |
|---|---|---|
| DARKSWORD Auto | `run_darksword_auto.ps1` | Weekdays 9 AM |
| DARKSWORD OTX | `run_darksword_otx.ps1` | Daily |
| DARKSWORD Barricade | `run_darksword_barricade.ps1` | Daily |

Each PS1 wrapper sets `PYTHONIOENCODING=utf-8` and `$OutputEncoding` to prevent emoji corruption in log files, then tees stdout+stderr to a dated log file.

---

## CMMC Cache

The script queries the Master Frameworks database at launch and builds an in-memory cache of all CMMC 2.0 controls. Currently loaded: **128 controls**.

`normalize_cid()` strips whitespace and normalizes case before cache lookups. Unresolved IDs are tracked in `CMMC_MISSES` and printed in a post-run miss report so gaps can be investigated without interrupting the push loop.

---

## Learning Plan Auto-Mapping

Every intel record is automatically linked to relevant GRC learning plan weeks based on its `control_domains` and `intel_category` — no manual input required.

**Domain → Week mapping:**

| Control Domain | Learning Weeks |
|---|---|
| Incident Response (IR) | Week 23 |
| Supply Chain Risk Management (SR) | Week 19, Week 29 |
| Risk Assessment (RA) | Week 18, Week 20 |
| Access Control (AC) | Week 13 |
| Identification and Authentication (IA) | Week 13 |
| Configuration Management (CM) | Week 12 |
| System Integrity (SI) | Week 17 |
| System and Communications Protection (SC) | Week 17 |
| Security Awareness and Training (AT) | Week 5 |
| Audit and Accountability (AU) | Week 27, Week 28 |

**Category → Week mapping:**

| Intel Category | Learning Weeks |
|---|---|
| regulatory | Week 25 |
| advisory | Week 26 |
| supply-chain | Week 19, Week 29 |
| incident / ransomware / phishing | Week 23 |
| vulnerability | Week 20, Week 21 |
| malware | Week 19 |
| breach | Week 28 |
| law-enforcement | Week 25 |
| ai-risk | Week 17 |
| identity-intelligence | Week 13 |

---

## Roadmap

- [x] DARKSWORD v6 — Claude-powered tactical intel pipeline
- [x] Manual Pipeline — standard workflow for Simply Cyber content
- [x] CMMC relation mapping (128 controls)
- [x] `SR.L2-3.15.2` added to Master Frameworks
- [x] `impacted_identity_provider` field mapping fixed
- [x] Learning plan auto-detection from `control_domains` and `intel_category`
- [x] Learning plan expanded from 3 weeks to 29 weeks
- [x] DARKSWORD v7 — `get_show_notes()` replaces YouTube scraping for Simply Cyber
- [x] Autonomous Pipeline (Choice 1) live for Simply Cyber via show notes
- [x] OTX Pipeline (Choice 4) — AlienVault threat feed integration with three-gate filter
- [x] `analyze_with_claude_prompt()` — per-source prompt tuning
- [x] `OTX_ANALYST_PROMPT` — `content_type`, `content_category`, `impacted_identity_provider` fixed
- [x] CMMC cache retry loop (3 attempts, rate-limit resilient)
- [x] `max_tokens` increased to 16000
- [x] RSS Feed Pipeline (Choice 5) — auto-detects episode date from Transistor RSS
- [x] `--auto` flag — non-interactive Simply Cyber pipeline for Task Scheduler
- [x] `--auto-otx` flag — non-interactive OTX pipeline for Task Scheduler
- [x] `--auto-barricade` flag — non-interactive Barricade pipeline for Task Scheduler
- [x] Windows Task Scheduler automation (3 tasks, 3 PS1 wrappers)
- [x] Barricade Cyber pipeline (Choice 6) — YouTube transcript via `YouTubeTranscriptApi`
- [x] `get_barricade_latest()` — RSS-driven with restricted-video fallback and deduplication
- [x] Simply Cyber YouTube fallback (Choice 7) — transcript when show notes are thin
- [x] Word count gate in `--auto` — auto-falls back to YouTube transcript if <500 words
- [x] `normalize_cid()` + `CMMC_MISSES` post-run miss report
- [x] `source_show` locked to canonical values in `ANALYST_PROMPT`
- [x] Gemini YouTube Ingest (Choice 8) — `gemini-2.0-flash` transcription for restricted/long-form video
- [x] `gemini_ingest_tool.py` — standalone Gemini transcription script
- [ ] Cybernews threat actor database + relations
- [ ] Phoenix Lab VM environment (attack surface testing)

---

## Known Limitations

**`get_transcript()` still blocked for Simply Cyber** — yt-dlp is blocked at the network/IP level for Simply Cyber content. This is no longer a pipeline limitation: V7's Choice 1 uses `get_show_notes()`, and the `--auto` word count gate falls back to `get_barricade_intel()` (YouTubeTranscriptApi, not yt-dlp). `get_transcript()` is retained for reference but not called by any active pipeline.

**`unknown` threat actor shows empty in Notion** — the script skips placeholder values (`none`, `unknown`, `empty`, `n/a`) to prevent noise in the database. This is intentional behavior.

**Barricade RSS may not include a YouTube URL** — if the Transistor feed entry for a Simply Cyber episode has no `yt_videoid` and no YouTube href in `entry.links`, the `--auto` YouTube fallback cannot trigger. The pipeline exits cleanly with a log message.

---

## License

MIT — Open source. Use it, fork it, build on it.

---

*Built with HardOPS discipline. Manual mastery before automation. Eat your own cooking.* ⚔️💎🦅
identity fix
