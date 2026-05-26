# ⚔️ Project DARKSWORD — GRC Intelligence Platform

**Threat Intelligence → CMMC 2.0 Gap Analysis — Automated**

A multi-source intelligence pipeline that ingests daily security content from YouTube, classifies it using Claude AI, maps it against **CMMC 2.0 / NIST 800-171** controls, links records to a live GRC learning plan, and pushes structured records into a Notion GRC repository.

Built as part of the **STAR Project** (Self-Transformation through Adversarial Rigor) — a hands-on vCISO development program. Manual mastery first, automation second.

---

## Architecture

```
YouTube (Simply Cyber)          YouTube (Barricade Cyber)
        ↓                               ↓
 get_transcript()               get_transcript()
        ↓                               ↓
 analyze_with_claude()          analyze_with_claude()
        ↓                               ↓
 governance_input.txt           barricade_input.txt
        ↓                               ↓
 notion_logger_v.6.py           threat_ingest.py
 [DARKSWORD Engine]             [Barricade Engine]
        ↓                               ↓
 CPE Tracker DB             Strategy & Architecture DB
        ↘                             ↙
         Master Frameworks DB (CMMC 2.0)
              [Source of Truth]
                    ↓
         GRC Learning Plan DB
         [Auto-linked by content]
```

### Databases (Notion)

| Database | Script | Source | Purpose |
|---|---|---|---|
| CPE Tracker | `notion_logger_v.6.py` | Simply Cyber | Tactical threat intel |
| STAR Strategy | `threat_ingest.py` | Barricade Cyber | Strategic architecture |
| Master Frameworks | shared | CMMC 2.0 | Control mapping (source of truth) |
| GRC Learning Plan | shared | Internal | Auto-linked from control domains |
| Cybernews Intel | *(planned)* | Cybernews | Threat actor profiles |

---

## Workspace Structure

This project spans two VS Code workspaces:

```
STAR_PROJECT (GRC-OCEG)
└── darksword/
    ├── notion_logger_v.6.py     ← DARKSWORD core engine
    ├── threat_ingest.py         ← Barricade engine
    ├── governance_input.txt     ← Simply Cyber working file (gitignored)
    ├── barricade_input.txt      ← Barricade working file (gitignored)
    ├── failed_records.txt       ← Failed push log
    ├── prompts/                 ← Analyst prompt library
    ├── archive/                 ← Legacy scripts
    ├── GRC-Playground/          ← Experimental work
    ├── GovSCH/                  ← Governance scheduler
    ├── .env                     ← API keys (gitignored)
    ├── requirements.txt
    ├── README.md
    └── script_walkthrough_.md   ← Full code walkthrough (V6.1)

PHOENIX_LAB_INFRA (AdminOps)
└── scripts/python/
    └── ...                      ← Lab automation scripts
```

---

## Pipeline Modes

### DARKSWORD (`notion_logger_v.6.py`)

```bash
cpe   # launches via alias
```

| Option | Description |
|---|---|
| `1. Autonomous Pipeline` | YouTube URL → Claude → Notion (blocked for Simply Cyber — network restricted) |
| `2. Manual Pipeline` | `governance_input.txt` → Notion |
| `3. Test Pipeline` | Mock data → Notion (`$0.00`, `--test` flag) |

### Current Standard Workflow (Manual Pipeline)

1. Go to YouTube video → open transcript → toggle timestamps off → copy all text
2. Paste transcript into Claude chat
3. Claude generates `===INTEL_RECORD_START===` formatted records
4. Copy records into `governance_input.txt`
5. Run `cpe` → select **2. Manual Pipeline** → enter real YouTube URL
6. Records push to Notion with CMMC linking and auto learning plan mapping

### Barricade Engine (`threat_ingest.py`)

```bash
python threat_ingest.py
```

Handles Barricade Cyber content ingestion into the STAR Strategy database.

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
alias cpe='cd /c/Work/GRC-OCEG/darksword && /c/Work/GRC-OCEG/.venv/Scripts/python.exe notion_logger_v.6.py'
```

---

## Intelligence Sources

| Source | Channel | Focus | Status |
|---|---|---|---|
| Simply Cyber | YouTube | Daily tactical threat briefs | ✅ Live (Manual Pipeline) |
| Barricade Cyber | YouTube | DFIR, MSP/enterprise ops | ✅ Live |
| Cybernews | YouTube | Threat actor profiles, geopolitical | 📋 Planned |

---

## CMMC Cache

The script queries the Master Frameworks database at launch and builds an in-memory cache of all CMMC 2.0 controls. Currently loaded: **128 controls**.

Notable controls added during development:
- `SR.L2-3.15.2` — Supply Chain Risk Management: Notification of Supply Chain Compromise

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
- [x] Barricade engine (`threat_ingest.py`) active
- [ ] RSS/YouTube feed auto-detection (no manual URL input)
- [ ] Windows Task Scheduler automation
- [ ] Cybernews threat actor database + relations
- [ ] Claude-powered Barricade pipeline (replace hardcoded items)
- [ ] Phoenix Lab VM environment (attack surface testing)

---

## Known Limitations

**Autonomous Pipeline blocked for Simply Cyber** — yt-dlp and YouTubeTranscriptApi are blocked at the network/IP level for Simply Cyber content specifically. Other channels work fine. The Manual Pipeline is the current standard for Simply Cyber content.

**`unknown` threat actor shows empty in Notion** — the script skips placeholder values (`none`, `unknown`, `empty`, `n/a`) to prevent noise in the database. This is intentional behavior.

---

## License

MIT — Open source. Use it, fork it, build on it.

---

*Built with HardOPS discipline. Manual mastery before automation. Eat your own cooking.* ⚔️💎🦅