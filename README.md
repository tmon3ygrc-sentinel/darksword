# ⚔️ Project DARKSWORD — GRC Intelligence Platform

**Threat Intelligence → CMMC 2.0 Gap Analysis — Automated**

A multi-source intelligence pipeline that ingests daily security content from YouTube, classifies it using Claude AI, maps it against **CMMC 2.0 / NIST 800-171** controls, and pushes structured records into a live Notion GRC repository.

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
 governance_input.txt           star_threat_ingest payload
        ↓                               ↓
 notion_logger_v.6.py           star_threat_ingest.py
 [DARKSWORD Engine]             [STAR/Barricade Engine]
        ↓                               ↓
 CPE Tracker DB             Strategy & Architecture DB
        ↘                             ↙
         Master Frameworks DB (CMMC 2.0)
              [Source of Truth]
```

### Databases (Notion)

| Database | Script | Source | Purpose |
|---|---|---|---|
| CPE Tracker | `notion_logger_v.6.py` | Simply Cyber | Tactical threat intel |
| STAR Strategy | `star_threat_ingest.py` | Barricade Cyber | Strategic architecture |
| Master Frameworks | shared | CMMC 2.0 | Control mapping (source of truth) |
| Cybernews Intel | *(planned)* | Cybernews | Threat actor profiles |

---

## Workspace Structure

This project spans two VS Code workspaces:

```
STAR_PROJECT (GRC-OCEG)
└── cpe-logger-tool/
    ├── notion_logger_v.6.py     ← DARKSWORD core engine
    ├── governance_input.txt     ← Working file (gitignored)
    ├── failed_records.txt       ← Failed push log
    ├── .env                     ← API keys (gitignored)
    └── requirements.txt

PHOENIX_LAB_INFRA (AdminOps)
└── scripts/python/
    ├── star_threat_ingest.py    ← STAR/Barricade engine (active)
    ├── star_threat_ingest_v2.py ← v2 with non-repudiation
    └── barricade_ingest.py      ← v1 (legacy)
```

---

## Pipeline Modes

### DARKSWORD (`notion_logger_v.6.py`)

```bash
cpe   # launches via alias
```

| Option | Description |
|---|---|
| `1. Autonomous Pipeline` | YouTube URL → Claude → Notion |
| `2. Manual Pipeline` | `governance_input.txt` → Notion |
| `3. Test Pipeline` | Mock data → Notion (`$0.00`) |

### STAR / Barricade (`star_threat_ingest.py`)

```bash
python star_threat_ingest.py
```

Features non-repudiation (SHA256 fingerprinting), deduplication, and operator audit trail.

---

## Quick Start

```bash
git clone https://github.com/tmon3ygrc-sentinel/cpe-logger.git
cd cpe-logger
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```
NOTION_TOKEN=secret_...
NOTION_DATABASE_ID=...      # CPE Tracker
CMMC_DATABASE_ID=...        # Master Frameworks
STAR_DS_ID=...              # STAR Strategy DB
ANTHROPIC_API_KEY=sk-ant-...
```

Set the `cpe` alias in `~/.bashrc`:

```bash
alias cpe='cd /c/Work/GRC-OCEG/cpe-logger-tool && c:/Work/GRC-OCEG/.venv/Scripts/python.exe notion_logger_v.6.py'
```

---

## Roadmap

- [x] DARKSWORD v6 — Claude-powered tactical intel pipeline
- [x] STAR engine — strategic architecture ingestion
- [x] CMMC relation mapping across both databases
- [x] Non-repudiation + deduplication (STAR engine)
- [ ] Claude-powered Barricade pipeline (replace hardcoded ITEMS)
- [ ] RSS/YouTube feed auto-detection (no manual URL input)
- [ ] Windows Task Scheduler automation
- [ ] Cybernews threat actor database + relations
- [ ] Phoenix Lab VM environment (attack surface testing)

---

## Intelligence Sources

| Source          | Channel | Focus                               | Status                          |
|-----------------|---------|-------------------------------------|---------------------------------|
| Simply Cyber    | YouTube | Daily tactical threat briefs        | ✅ Live                         |
| Barricade Cyber | YouTube | DFIR, MSP/enterprise ops            | 🔧 Hardcoded → Claude pending   |
| Cybernews       | YouTube | Threat actor profiles, geopolitical | 📋 Planned                      |

---

## License

MIT — Open source. Use it, fork it, build on it.

---

*Built with HardOps discipline. Manual mastery before automation. Eat your own cooking.* ⚔️💎🦅