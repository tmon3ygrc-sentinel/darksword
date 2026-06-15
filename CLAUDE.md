# CLAUDE.md — DARKSWORD Operations Brief

## Roles

**AO ("The Smith")** — Human operator. Reviews, approves, and accepts risk at every gate. No destructive or ambiguous action proceeds without AO sign-off. Per-action approval only — never blanket.

**OPS** — Claude Code (this session). Ground-level execution: file edits, commits, dependency installs, running scripts and pipeline choices. Executes on AO approval; does not self-authorize.

**Cowork personas** — Analysis, design, and documentation layer; no execution authority. They produce findings, plans, and prose; OPS executes on their output after AO approves.

**Routing:**
- One-liner / file edit / commit / script run → **OPS**
- Investigation / log analysis → **SENTINEL** or **AUDITOR**
- Schema / pipeline design → **ARCHITECT**
- Docs / handovers → **SCRIBE**
- Intel gathering / CVE / endpoint health → **RECON**
- Every gate → **AO** approves

**ARCHITECT design scope** (decisions land here; OPS executes):
- `notion_logger_v7.py` — all choices (1-8) and `--auto` flag
- `gemini_ingest_tool.py` — Gemini YouTube ingest (Choice 8)
- `threat_ingest.py` — Barricade Cyber engine (STAR Strategy DB)
- Notion DB schema and field routing (`push_record`, `parse_records`, prompt design)
- Sub-project architecture: `GRC-Playground/`, `GovSCH/`

---

## System State (as of 2026-06-14)

**Active engine:** `notion_logger_v7.py`

**Pipeline modes:**

| Choice | Name | Notes |
|--------|------|-------|
| 1 | Autonomous | Show notes → Claude → Notion. Prompts for date. |
| 2 | Manual | Paste output to `governance_input.txt` → Notion |
| 3 | Test | `governance_input.txt` → Notion, no API cost |
| 4 | OTX | AlienVault OTX → Claude → Notion. Requires `OTX_API_KEY`. |
| 5 | RSS Auto | Transistor RSS pubDate → show notes → Claude → Notion. Zero prompts. |
| 6 | Barricade RSS | Barricade Cyber RSS → transcript → Claude → Notion |
| 7 | YouTube Fallback | Simply Cyber YouTube → transcript → Claude → Notion |
| 8 | Gemini YouTube | YouTube → Gemini Flash → `gemini_ingest_tool.py` → Notion |

`--auto` flag: Skips menu, runs Choice 5 logic, exits. Task Scheduler entry point.

**Notion DBs:**

| Database | Variable | UUID |
|----------|----------|------|
| CPE Tracker | `DATABASE_ID` | `30755ed7-4038-8039-a64e-c0eab4d4a06a` |
| CMMC Master Frameworks | `CMMC_DATABASE_ID` | *(env only — scrubbed from history)* |
| GRC Learning Plan | *(relation target)* | `2d655ed7-4038-8116-93c4-e0202647f640` |
| STAR Strategy | `DS_ID` in `threat_ingest.py` | `33855ed7-4038-80f6-a615-000b4bf49a40` |

**Record format:** `===INTEL_RECORD_START===` / `===INTEL_RECORD_END===` blocks with `fieldname:: value` lines. Multi-value fields are comma-separated. Placeholder values (`none`, `unknown`, `empty`, `n/a`) are silently skipped — intentional.

**Venv:** `C:\Work\GRC\.venv` (shared across projects)

**Task Scheduler:** `run_darksword_auto.ps1` → `notion_logger_v7.py --auto` — weekdays at 14:00 (changed from noon 2026-06-14: noon raced episode publish — ep1152 dropped at 12:18, triggering prior-day re-ingest; 2pm gives margin past typical publish). Logs to `darksword_YYYY-MM-DD.log`.

---

## Agent Roster

| Layer | Agent | Home | Trigger |
|-------|-------|------|---------|
| Human | **AO ("The Smith")** | — | Approval gate; risk acceptance |
| Execution | **OPS** | `CLAUDE.md` (this session) | File edits, commits, installs, script/pipeline runs |
| Cowork | **ARCHITECT** | Cowork | System design, pipeline architecture, schema decisions, cross-cutting judgment |
| Cowork | **SENTINEL** | `.claude/SENTINEL.md` | Runtime errors, log analysis, data flow failures, Notion API errors |
| Cowork | **AUDITOR** | `.claude/AUDITOR.md` | `.gitignore`, `.env`, `requirements.txt`, git history, secrets, dependencies |
| Cowork | **SCRIBE** | `.claude/SCRIBE.md` | `README.md`, `script_walkthrough_.md`, changelogs, handover notes |
| Cowork | **RECON** | `.claude/RECON.md` | URL validation, endpoint health, GitHub attack surface, dependency CVEs |

---

## Handoff Protocol

AO routes work to the appropriate layer. Cowork personas analyze and recommend; OPS executes only after AO approval.

**Route to SENTINEL when:**
- The pipeline raises an unhandled exception or produces wrong output
- `failed_records.txt` has new entries that need root-cause analysis
- `--auto` scheduler run produced no records or wrong word count

**Route to AUDITOR when:**
- Adding a new dependency (update `requirements.txt`, check for CVEs)
- Any change to `.env.example`, `.gitignore`, or commit signing behavior
- Before any destructive git operation

**Route to RECON when:**
- A new external endpoint or API integration is added
- A dependency is added or upgraded (CVE surface check)
- Suspicion that a secret may have been committed or is exposed in a log
- Pre-release audit of the public GitHub repo footprint

**Route to SCRIBE when:**
- A new pipeline choice or flag is added (README + walkthrough need updates)
- Session ends and a handover note is needed
- Any user-facing behavior change that isn't reflected in docs

**Route to ARCHITECT when:**
- A structural change, new feature, or schema decision is needed
- A cross-persona conflict needs a design-layer judgment call

**Return to OPS when:**
- A persona's analysis is complete and AO has approved the action plan
- OPS executes; it does not self-route or self-authorize

---

## Known Operational Patterns

**Simply Cyber Monday streams — thin show notes when Gerald Auger is traveling:**
When Gerald Auger is away from his home studio, Monday episode show notes are frequently too thin (~230 words) to produce clean records via Choice 1 (Autonomous) or the `--auto` scheduler. Standard fallback is Choice 2 (Manual Pipeline): use Librarian to generate records from the episode content, paste output into `governance_input.txt`, then run Choice 2 to push. Affected episodes to date: ep1145, ep1147, ep1148.

**IA.L2-3.5.1 — manually backfilled 2026-06-08:**
Control was missing from Master Frameworks (only the L1 variant `IA.L1-3.5.1` was present). Added via one-off script. Practice Title: "Use multifactor authentication for local and network access to privileged and non-privileged accounts." NIST 800-171 Ref: 3.5.3. `load_cmmc_cache()` now loads 136 controls at startup (verified 2026-06-11).

**`TranscriptsDisabled` added to `get_barricade_intel()` catch block — 2026-06-11 (commit 3d19dc9):**
Previously, videos with captions disabled (common on thin Monday episodes) raised an unhandled `TranscriptsDisabled` exception → exit code 1 crash. Now caught alongside `VideoUnplayable` and re-raised as a clean `RuntimeError` → exit code 0.

**Vetting note (ep1151, 2026-06-11): Verify entity *relationships*, not just entity existence.**
Real proper nouns can be welded into false linkages — in ep1151, the ConsentFix OAuth technique (real) was incorrectly fused with the CalPhishing .ics delivery vector (real) into a single false relationship. Both entities were legitimate; the link between them was fabricated. AUDITOR verification against primary sources caught it; generation-layer self-verification is not a control.

**Claude Code Update Failure — Windows File Lock (2026-06-11):**
Symptom: "✘ Auto-update failed: claude.exe in use". Root cause: Windows locks a running executable; Claude Code can't overwrite its own binary while any CLI session holds it. Repeats every launch because using the tool is the condition that blocks the update.

CRITICAL — two different programs share the name: Claude Desktop at `C:\Program Files\WindowsApps\Claude_...` (MSIX, multi-process Electron tree) — Cowork, leave it alone — and Claude Code CLI at `C:\Users\darke\AppData\Roaming\npm\` (npm-global), the updater's target. Identify by PATH, never image name. `taskkill /IM claude.exe` hits BOTH and will kill a live Cowork session.

Fix (from cold state, no CLI sessions running):
```
npm i -g @anthropic-ai/claude-code
claude --version    # target >= 2.0.65 (closes CVE-2026-21852)
```

Hygiene: exit CLI with `/exit`, not by closing the terminal window — closing orphans the process and keeps the lock. Security tie-in: the npm allow-scripts/postinstall warning on update is the same vector as npm supply-chain worms (Miasma). Approve scripts deliberately; never blanket-allow.

---

## Phase 2

**STAR_STRATEGY_DB_V2 — identity resolution (architectural debt):**
This DB is carrying three overlapping identities and needs a canonical purpose decided before further manual writes:
1. ORIGINAL: Barricade Cyber log tracker feeding the (now-wiped) VM lab.
2. CURRENT CONTENT: strategic threat synthesis — entries with Strategic Pillar + vCISO Hot Take (macOS Tahoe, Axios NPM). Different cognitive product than CPE Tracker's raw intel feed.
3. LIVE: STAR Logger is still actively connected and may auto-write.

Risks: manual rows may collide with STAR Logger's schema/write expectations — do not hand-add entries until the logger's write behavior (fields, cadence, triggers) is mapped. "V2" implies a V1 exists — confirm/locate. Name (STRATEGY) no longer matches origin (lab-log). Drift unresolved.

Decision needed (gated on VM lab rebuild): (a) remains strategic-synthesis DB → migrate lab-log schema + STAR Logger connection OUT to a dedicated lab-tracking DB; or (b) reverts to lab-tracking on rebuild → migrate strategic entries (macOS Tahoe, Axios) OUT to a dedicated Strategy DB. Endgame vision: faux VM lab + live-threat pentest in semi-sandboxed env — the lab-tracking DB should be scoped to that from the start, cleanly separated from strategic synthesis.

Until resolved: park operational runbooks in CLAUDE.md, not this DB.

---

## Key Files

| File | Role |
|------|------|
| `notion_logger_v7.py` | Main engine — all active development |
| `gemini_ingest_tool.py` | Gemini ingest module (Choice 8) |
| `governance_input.txt` | Working file — parser reads from here |
| `failed_records.txt` | Failed push log — check first on Notion errors |
| `run_darksword_auto.ps1` | Task Scheduler wrapper |
| `prompts/cpe_prompt_claude.txt` | Canonical prompt for manual chat |
| `good_example_template.txt` | Gold-standard record examples + valid field values |
| `script_walkthrough_.md` | Code walkthrough (V6.1 core, V7 addenda) |
| `.env` | Live secrets — never commit |
| `.env.example` | Safe template — placeholders only |
| `requirements.txt` | Dependency manifest — tracked in git |

---

## Known Issues

- **RESOLVED (2026-06-14): Notion schema-size cap exceeded — all 8 ep1152 records now pushed.** Root cause was cumulative multi-select schema weight, NOT `tags` alone. The error named `tags` as a symptom (largest property at ~208KB), but the real culprits were prose-content fields wrongly typed as multi-select — `identity_impact` (~140KB) and `detection_opportunities` (~49KB) — that accreted unbounded options over time. Fix: delete + recreate those two properties as fresh `rich_text` (GUI type-conversion does NOT reclaim orphaned options; only delete evicts them from Notion's internal schema ledger). `tags` was NOT deleted — evicting the two prose fields dropped total schema to ~164KB, under cap, and all 6 queued ep1152 records (03-08) pushed clean; `record_exists` dedup guard correctly skipped the 1 already present. Lesson: Notion's schema cap is cumulative across all properties; the error names a symptom not the root cause; when a "fixed" field still blocks, re-measure the whole system. Resolved 2026-06-14.

**Phase 2 watch-list — remaining categorical multi-selects will accrete toward cap over time:**
`control_domains` (32KB), `target_sector` (30KB), `threat_actor` (28KB), `attack_techniques` (24KB). Revisit cardinality via `diag_option_cardinality.py` if total schema trends up. Decision needed per runbook §1: keep as enum (closed vocabulary, constrained prompt) or convert to `rich_text` permanently.

---

## Working Style

Operator is an aspiring GRC engineer building this as a working tool and a portfolio piece. Engage low-level: explain mechanisms, name the class of problem, tie fixes to transferable principles. Expect frequent "why" questions — that's intentional learning, not confusion.

**Discipline (enforce these):**
- Verify before trust; read-only before destructive; back up before irreversible ops.
- Show diffs / plans before executing. Operator is the approval gate. Per-action approval only — never blanket allow-all.
- Hold the read-vs-run line: Cowork personas (ARCHITECT/SENTINEL/AUDITOR/SCRIBE/RECON) analyze; OPS executes on AO approval.
- Don't initiate new work when operator is fatigued; park non-urgent, non-blocking items deliberately.
