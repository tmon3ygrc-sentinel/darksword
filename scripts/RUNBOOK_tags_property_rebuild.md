# RUNBOOK — CPE Tracker `tags` (+ converted fields) property rebuild

**Status:** PARKED — destructive. Do NOT run on momentum / when tired.
**Owner:** ARCHITECT (executes on local machine — has Notion token + network).
**Cowork/this assistant:** analysis only; no Notion egress from the sandbox.
**Drafted:** 2026-06-13 (after retry confirmed orphaned-options root cause).

---

## 0. Why this runbook exists (root cause, one paragraph)

Notion stores a multi_select's option vocabulary in the database **schema**, and
**never garbage-collects it**. Converting the property type multi_select → text
(GUI or API) *relabels* the property but does **not** evict the option history
from Notion's internal schema-size ledger. That ledger is **invisible to the API**
(`databases.retrieve` shows the converted property as ~89 bytes), but Notion still
enforces it: `tags` (id `YbSu`) = **208,877 bytes**, ~= the entire ~209,597 cap.
Result: any write that would add a new option to *any* multi_select is rejected,
naming `tags` as the largest offender. **Only deleting the property evicts the
orphaned options.** Class of problem: *relabel ≠ reclaim* (soft vs hard delete;
logical vs physical reclamation; tombstones that still count against quota).

Empirically confirmed (2026-06-13 retry): 1/6 records pushed (the one that added
no new options); 5/6 failed citing `tags YbSu 208877`.

---

## 1. Scope — which properties

Convert-didn't-evict is **general**, not tags-specific. Anything migrated via
type-conversion still carries internal orphans. Candidates:

| Property | id | Tonight's state | Likely action |
|---|---|---|---|
| `tags` | `YbSu` | converted→text (orphans remain) | **delete + recreate as rich_text** |
| `identity_impact` | `As:Z` | converted→text tonight (orphans likely remain) | **delete + recreate as rich_text** |
| `detection_opportunities` | (see diag) | converted→text tonight (orphans likely remain) | **delete + recreate as rich_text** |
| `control_domains`, `target_sector`, `threat_actor`, `attack_techniques`, `impacted_identity_provider`, `intel_category` | — | still multi_select, unbounded | **DECISION NEEDED** (keep enum vs convert→text) — run cardinality script first |

> Run `diag_option_cardinality.py` (read-only) FIRST. Any "enum" field with
> hundreds+ options is leaking freeform values and should become rich_text too.
> Low-cardinality, genuinely-bounded fields (e.g. `kill_chain_phase`,
> `source_show`) can stay multi_select/select.

---

## 2. Preconditions (gates — do not skip)

1. **FRESH backup, this session.** The 06-13 CSV predates record `04` and anything
   pushed since; it cannot be the sole backfill source.
   - Re-export CPE Tracker as Markdown & CSV (unfiltered view → all rows).
   - Verify with the same checks as Phase 1: row count, 40 columns, tags column
     comma-separated intact. (Reuse the verification approach from the sealed bundle.)
   - Record SHA-256. This CSV is BOTH rollback and backfill source.
2. **Full-fidelity rollback confirmed.** The Notion Duplicate
   "CPE Tracker — ROLLBACK pre-tags-migration 2026-06-13" exists and predates all
   conversions. If unsure it covers the fields in scope, make a NEW Duplicate now.
3. **Dependency check.** Confirm nothing (rollup, formula, or the `[STAR]` relation)
   references the properties being deleted. Deleting a property referenced by a
   rollup/formula breaks it. CLAUDE.md flags this migration touches
   views + `[STAR]` relation.
4. **Note current views** that show the in-scope columns (screenshot the column
   sets) so you can re-add them after recreate.
5. **Quiesce writers.** Ensure no `--auto` scheduler run or STAR Logger write can
   fire mid-operation (weekday-noon scheduler; today is Sat — fine. If running on a
   weekday, disable the Task Scheduler entry first).

---

## 3. Procedure (per property, one at a time)

Do tags first as the canary; confirm the mechanism before batching the rest.

1. **DRY RUN** `fix_recreate_property.py --field tags` (default: read-only).
   - Confirms current type/id, prints the exact delete + recreate payloads, and
     verifies the fresh backup hash. NO writes.
2. **DELETE** `... --field tags --execute` → sends `{"properties":{"tags":null}}`.
3. **VERIFY EVICTION** — re-run `diag_tags_schema.py`. The API total schema bytes
   should drop, and (the real test) the orphan weight is gone. **If schema size
   does NOT drop, STOP** — API-delete is not evicting (Notion trash/retention);
   escalate before proceeding.
4. **RECREATE** `... --field tags --recreate --execute` →
   `{"properties":{"tags":{"rich_text":{}}}}`. New property, new id, 0 options.
5. **BACKFILL** `fix_backfill_tags.py --csv <fresh.csv> --field tags`
   - Maps `record_id` → page_id (paginated query), writes tags rich_text per row.
   - DRY-RUN default; `--execute` to write. Idempotent (re-running is safe).
6. **VERIFY** — spot-check 3–5 rows in Notion show comma-separated tags text.
7. **RE-ADD TO VIEWS** (GUI) — re-add the `tags` column to the views noted in §2.4.
8. Repeat 1–7 for `identity_impact`, `detection_opportunities`, and any field the
   cardinality script flagged.

---

## 4. Final validation

1. Re-run `diag_tags_schema.py` — total schema comfortably under cap, no single
   property near it.
2. **Retry the queued records** via the pipeline (Choice 2). Expect all to push;
   `record_exists` keeps it dedup-safe. Capture output.
3. `failed_records.txt` drains; prune any stale entries (e.g. `04`, already logged).
4. Update `CLAUDE.md` ## Known Issues: close the BLOCKER, record the fix +
   root cause (relabel ≠ reclaim) so future-you doesn't re-walk this. (SCRIBE.)

---

## 5. Rollback

- **Data of a single column lost / backfill wrong:** re-run backfill from the
  fresh CSV (idempotent), or fix the CSV and re-run.
- **Property structure botched:** delete the bad property, recreate from this
  runbook.
- **Catastrophic (DB-level):** the full-fidelity Notion **Duplicate** is the
  restore. The CSV is content/audit only — it does NOT restore relations,
  page identity, or schema typing.

---

## 6. Phase 4 (separate, not this runbook) — fix the SOURCE

Deleting + recreating reclaims space but does **not** stop the bucket refilling.
The generation layer emits novel freeform values into enum fields (that's how
`identity_impact` reached ~140KB). Until the analyst prompt / parser constrains
those fields to a closed vocabulary — or they're permanently rich_text — options
will re-accrete. This is an ARCHITECT schema-design decision; do it deliberately,
separate from the reclamation work above.

---

## Files in this bundle
- `fix_recreate_property.py` — guarded delete + recreate (dry-run default).
- `fix_backfill_tags.py` — backfill rich_text from CSV by record_id (dry-run default).
- `diag_tags_schema.py`, `diag_option_cardinality.py` — read-only diagnostics.
- `cpe_tracker_rollback_2026-06-13_*.zip` — Phase 1 sealed CSV backup (superseded
  as backfill source by the FRESH export taken at run time; keep as audit trail).
