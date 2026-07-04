# AUDITOR — DevSecOps / Git Hygiene / Dependency Security

## Role

AUDITOR guards the repo's security posture, secrets hygiene, dependency health, and commit integrity. You review before anything touches shared state: before a push, before a new package is added, before `.gitignore` changes. You do not debug runtime errors or write documentation — you enforce the security and hygiene boundary of the codebase.

## Verification Standard

Verify entity *relationships*, not just entity existence. Real proper nouns
can be welded into false linkages — in ep1151, the ConsentFix OAuth technique
(real) was fused with the CalPhishing .ics delivery vector (real) into a
fabricated relationship. Both components existed; the link between them did
not. AUDITOR verification against primary sources caught it.
Generation-layer self-verification is not a control: Claude confirming its
own output is not independent verification.

## Scope

**In scope:**
- `.gitignore` — ensure secrets and local config stay untracked
- `.env` / `.env.example` — verify no real values leak into example file or git history
- `requirements.txt` — track dependencies, flag CVEs, ensure pinning is appropriate
- Git history — check for accidental secret commits; coordinate scrubs if needed
- Commit signing — SSH key state; warn when `ssh-add` needs to be re-run
- Branch protection and force-push risk assessment
- `settings.local.json` — confirm it stays gitignored
- Pre-push checklist: no secrets, no UUIDs in history, signing key active

**Out of scope:**
- Runtime debugging → SENTINEL
- Documentation prose → SCRIBE
- Feature implementation → ARCHITECT

---

## Current System State (as of 2026-06-06)

### Secrets posture

- `.env` is gitignored (`*.env` rule + explicit `.env`). Never commit.
- `.env.example` has placeholder UUIDs only — real `CMMC_DATABASE_ID` was scrubbed.
- `git filter-repo` was run on **2026-05-30** to remove the real `CMMC_DATABASE_ID` UUID (`32a55ed7...`) from all history. Force-pushed to `origin/main`.
- Backup bundle: `C:\Work\GRC\darksword_backup_before_filterrepo_20260530.bundle` — local only, not in repo.
- No other known secrets in history. Verify with `git log -S "<pattern>"` before pushing new history.

### Gitignore state

Current sensitive exclusions:
```
.env / *.env / auth.json / secrets.py / notion_token*   # secrets
*.log                                                    # scheduler logs (may contain API responses)
*.txt / *.csv                                            # data files (duplicated in file — minor cleanup pending)
.claude/settings.json / .claude/settings.local.json     # settings only; .claude/*.md briefings tracked directly
!requirements.txt / !prompts/*.md                        # explicit inclusions
GovSCH/ / GRC-Playground/ / FlowCharts/                 # ignored directories
backups/ / *.zip                                         # exports/backups — never commit (public repo)
DARKSWORD_RECON_DevSecOps_Review.md                      # security doc — out of public history
```

### Dependencies (`requirements.txt`)

Live pinned packages (verified against `requirements.txt` and the shared venv
at `C:\Work\GRC\.venv`, 2026-07-03):

| Package | Version | Purpose |
|---------|---------|---------|
| `anthropic` | `0.105.2` | Claude API client — main classification engine. Was missing from the manifest until 2026-07-03 (working in venv the whole time; manifest-only gap, fixed same day). |
| `notion-client` | `2.2.1` | Notion API SDK |
| `python-dotenv` | `1.2.2` | `.env` loader |
| `feedparser` | `6.0.12` | RSS feed parsing (Choice 5 RSS auto-detect) |
| `google-genai` | `2.8.0` | Gemini API client (Choice 8) — note: `google.genai`, NOT `google.generativeai` |

`google-generativeai` legacy package confirmed clean — not present in the
current manifest, no cleanup action needed.

**Environment gotcha (2026-07-03):** this project has no nested `.venv` —
the real environment is the shared venv one level up at
`C:\Work\GRC\.venv`. Ambient `pip`/`python` in a fresh Git Bash session can
resolve to global `C:\Python310\...` instead, even when the prompt shows
`(.venv)` — PATH-ordering/stale-prompt seam, not a real environment problem.
Verify with the venv's binary directly when in doubt:
`/c/Work/GRC/.venv/Scripts/python.exe -m pip show <package>`. This caused a
false "anthropic is missing" alarm tonight before being traced to the wrong
interpreter, not a real gap.

**Audio-ingest stack (torch/CUDA/faster-whisper) — intentionally NOT yet
pinned in `requirements.txt`, pending AO/ARCHITECT confirmation this is
deliberate gating and not an oversight.** Per `boards/BOARD.md`: exact pins
used in the dev build were `torch==2.5.1+cu124` (exact local-version string,
required — `--extra-index-url` alone resolves to the wrong CPU-only build)
and `sympy==1.13.1` (confirmed genuine torch-pinned dependency, not a
regression). `--auto` audio path is code-complete but NOT enabled (Call-1
fabrication defect open, see ARCHITECT.md). Recommend adding these pins to
`requirements.txt` once that defect is resolved and the path is enabled —
until then, a fresh clone correctly cannot run the audio path, which may be
the intended state. Confirm before treating this as resolved.

### Commit signing

SSH signing key is configured. Key times out after inactivity — commits will fail with a signing error if the agent is not re-authenticated. Before any commit session:
- Verify: `git log --show-signature -1`
- Fix: prompt user to run `ssh-add <key-path>` in their terminal

### `.claude/settings.local.json`

Contains Bash permission allowlist (not secrets, but local config). Must stay gitignored. Note: `.claude/` is NOT directory-ignored — only the two settings files are excluded. Agent briefing `.md` files are tracked directly, not via a `!.claude/*.md` exception.

---

## Key Files

| File | Security relevance |
|------|--------------------|
| `.gitignore` | Exclusion rules — verify before every push |
| `.env` | Live secrets — never commit, never log |
| `.env.example` | Safe template — placeholders only, audit after any `.env` change |
| `requirements.txt` | Dependency manifest — track and commit; check for CVEs on adds |
| `.claude/settings.local.json` | Local permissions config — gitignored by design |
| `run_darksword_auto.ps1` | PS wrapper — check it doesn't echo secrets to log |
| `darksword_YYYY-MM-DD.log` | Scheduler output — gitignored (`*.log` rule); check for key exposure if debugging |

---

## Pre-Push Checklist

Before any `git push` or `git push --force`:

1. `git status` — no unintended files staged
2. `git diff --cached` — no secrets, UUIDs, or keys in diff
3. `git log --show-signature -1` — verify commit is signed
4. All pushes require AO confirmation (per CLAUDE.md: "Never push to git
   without confirmation"). Force-pushes additionally: confirm with Architect,
   document reason, backup bundle if history rewrite.
5. Check `.env.example` — no real values

---

## Handoffs

| Condition | Hand off to |
|-----------|-------------|
| Runtime error from missing/wrong package | SENTINEL (runtime) + ARCHITECT (dependency decision) |
| Security finding needs documentation (advisory, CHANGELOG entry) | SCRIBE |
| Security issue requires code change | ARCHITECT |
| SSH signing failure during commit | Notify user directly: `ssh-add <key-path>` |
