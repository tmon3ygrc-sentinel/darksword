# test_push_corrections.py — throwaway verification, delete after
# Confirms the --push-corrections mechanism: corrections-file parsing,
# page-ID lookup (found/not-found), the before/after diff pulling real live
# data, the y/n confirmation gate actually blocking, the out-of-scope-field
# warning banner, and post-write re-verification being a genuine re-query
# (not just an echo of the input new_value).
# See boards/sentinel_update_existing_record_design.md for the design this
# verifies, and boards/verify_push_corrections_build.txt for the AO-facing
# build report this test output feeds into.
#
# No live Notion traffic: notion.databases.query / notion.pages.update /
# input() are all monkeypatched to fakes for the duration of each test
# block, restored immediately after — same convention as test_record_id.py.

import tempfile
from pathlib import Path

import notion_logger_v7 as nl

_ORIG_QUERY  = nl.notion.databases.query
_ORIG_UPDATE = nl.notion.pages.update

failures = 0


def check(label, got, expected):
    global failures
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    if not ok:
        failures += 1
    print(f"{status} {label}: {got!r}  (expect {expected!r})")


def check_true(label, cond):
    check(label, bool(cond), True)


def check_in(label, needle, haystack):
    global failures
    ok = needle in haystack
    status = "PASS" if ok else "FAIL"
    if not ok:
        failures += 1
    print(f"{status} {label}: {needle!r} in captured output -> {ok}")


def check_not_in(label, needle, haystack):
    global failures
    ok = needle not in haystack
    status = "PASS" if ok else "FAIL"
    if not ok:
        failures += 1
    print(f"{status} {label}: {needle!r} NOT in captured output -> {ok}")


# ===================================================================
# Fakes
# ===================================================================

def fake_rich_text_prop(text: str) -> dict:
    return {"rich_text": [{"plain_text": text, "text": {"content": text}}]}


def fake_multi_select_prop(names) -> dict:
    return {"multi_select": [{"name": n} for n in names]}


def make_fake_page(page_id: str, record_id: str, **field_values) -> dict:
    props = {"record_id": fake_rich_text_prop(record_id)}
    for field, val in field_values.items():
        if field in nl.MULTI_SELECT_FIELDS:
            props[field] = fake_multi_select_prop(val if isinstance(val, list) else [val])
        else:
            props[field] = fake_rich_text_prop(val)
    return {"id": page_id, "properties": props}


class FakeQueryByRecordId:
    """Simulates databases.query filtered by record_id `equals`. Backed by a
    mutable dict (record_id -> page) shared with FakePagesUpdate below, so a
    post-write re-query genuinely reflects whatever the fake write actually
    stored — not a value the test pre-baked in advance."""
    def __init__(self, pages: dict):
        self.pages = pages
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        rid = kwargs["filter"]["rich_text"]["equals"]
        page = self.pages.get(rid)
        return {"results": [page] if page else [], "has_more": False}


class FakePagesUpdate:
    """Simulates notion.pages.update. Writes into the SAME page-store the
    query fake reads from, but appends a distinct marker to whatever value
    it stores — so a test proving 'the post-write print is a real re-query'
    can check for the marker, which could only appear if the printed value
    actually came from reading the fake store again, not from echoing the
    new_value string still sitting in a local variable."""
    MARKER = " [VERIFIED]"

    def __init__(self, pages: dict):
        self.pages = pages
        self.calls = 0

    def __call__(self, page_id, properties, **kwargs):
        self.calls += 1
        for page in self.pages.values():
            if page["id"] != page_id:
                continue
            for field, val in properties.items():
                if "rich_text" in val:
                    text = val["rich_text"][0]["text"]["content"] if val["rich_text"] else ""
                    page["properties"][field] = fake_rich_text_prop(text + self.MARKER)
                elif "multi_select" in val:
                    names = [o["name"] + "-V" for o in val["multi_select"]]
                    page["properties"][field] = fake_multi_select_prop(names)
            return {"id": page_id}
        raise RuntimeError(f"fake: page_id {page_id} not found")


class FakeInputQueue:
    """Feeds queued answers to input() in order; raises if exhausted so a
    test that consumes more prompts than expected fails loudly instead of
    hanging (a real input() would hang; this must not)."""
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def __call__(self, prompt=""):
        self.calls += 1
        if not self.answers:
            raise RuntimeError("fake input() queue exhausted")
        return self.answers.pop(0)


def write_corrections_file(path: Path, blocks: list):
    with open(path, "w", encoding="utf-8") as f:
        for b in blocks:
            f.write("===RECORD_CORRECTION_START===\n")
            for k, v in b.items():
                f.write(f"{k}:: {v}\n")
            f.write("===RECORD_CORRECTION_END===\n\n")


import io
import contextlib


def run_push_corrections_capturing(blocks, pages, input_answers):
    """Writes a corrections file, mocks notion.databases.query/pages.update/
    input, runs push_corrections(), restores everything, and returns
    (captured_stdout, query_fake, update_fake)."""
    orig_query   = _ORIG_QUERY
    orig_update  = _ORIG_UPDATE
    orig_input   = nl.input if "input" in nl.__dict__ else None
    orig_corr_file = nl.CORRECTIONS_FILE

    query_fake  = FakeQueryByRecordId(pages)
    update_fake = FakePagesUpdate(pages)
    input_fake  = FakeInputQueue(input_answers)

    nl.notion.databases.query = query_fake
    nl.notion.pages.update    = update_fake
    nl.input                  = input_fake

    buf = io.StringIO()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            nl.CORRECTIONS_FILE = Path(tmpdir) / "record_corrections.txt"
            write_corrections_file(nl.CORRECTIONS_FILE, blocks)
            with contextlib.redirect_stdout(buf):
                nl.push_corrections()
    finally:
        nl.notion.databases.query = orig_query
        nl.notion.pages.update    = orig_update
        if orig_input is None:
            del nl.input
        else:
            nl.input = orig_input
        nl.CORRECTIONS_FILE = orig_corr_file

    return buf.getvalue(), query_fake, update_fake


# ===================================================================
# 1. parse_corrections() — block-delimiter parsing, matches parse_records()
# ===================================================================
with tempfile.TemporaryDirectory() as tmpdir:
    corr_path = Path(tmpdir) / "corrections.txt"
    write_corrections_file(corr_path, [
        {"record_id": "rec-01", "field": "key_takeaways", "new_value": "Fixed text A", "reason": "reason A"},
        {"record_id": "rec-02", "field": "executive_summary", "new_value": "Fixed text B", "reason": "reason B"},
    ])
    # Append one malformed block by hand (missing new_value) to confirm it's dropped.
    with open(corr_path, "a", encoding="utf-8") as f:
        f.write("===RECORD_CORRECTION_START===\nrecord_id:: rec-03\nfield:: title\n===RECORD_CORRECTION_END===\n")

    parsed = nl.parse_corrections(corr_path)
    check("parse_corrections finds exactly 2 well-formed blocks", len(parsed), 2)
    check("block 1 record_id", parsed[0]["record_id"], "rec-01")
    check("block 1 field", parsed[0]["field"], "key_takeaways")
    check("block 1 new_value", parsed[0]["new_value"], "Fixed text A")
    check("block 1 reason", parsed[0]["reason"], "reason A")
    check("block 2 record_id", parsed[1]["record_id"], "rec-02")
    check("malformed block (no new_value) was dropped, not included",
          any(c["record_id"] == "rec-03" for c in parsed), False)

# ===================================================================
# 2. find_record_page() — found and not-found cases
# ===================================================================
pages = {
    "simplycyber-ep1152-2026-06-12-06": make_fake_page(
        "page-abc123", "simplycyber-ep1152-2026-06-12-06",
        executive_summary="The fine was $49M.",
    )
}
nl.notion.databases.query = FakeQueryByRecordId(pages)
found = nl.find_record_page("simplycyber-ep1152-2026-06-12-06")
check_true("find_record_page returns a page for a live record_id", found is not None)
check("find_record_page returns the correct page id", found["id"], "page-abc123")

not_found = nl.find_record_page("simplycyber-does-not-exist-99")
check("find_record_page returns None for an unknown record_id", not_found, None)
nl.notion.databases.query = _ORIG_QUERY  # restore before the next section's helper calls

# ===================================================================
# 3. Diff output reflects current (live) vs. new (file) correctly
# ===================================================================
pages_3 = {
    "rec-diff-01": make_fake_page("page-diff-01", "rec-diff-01",
                                    executive_summary="The fine was $49M.")
}
out, qfake, ufake = run_push_corrections_capturing(
    blocks=[{
        "record_id": "rec-diff-01", "field": "executive_summary",
        "new_value": "The fine was $409M.", "reason": "confirmed via independent sources",
    }],
    pages=pages_3,
    input_answers=["n"],  # decline, we're only checking the diff text here
)
check_in("diff shows the CURRENT live value (not the file's new_value)", "current:  The fine was $49M.", out)
check_in("diff shows the NEW value from the corrections file", "new:      The fine was $409M.", out)
check_in("diff shows the reason line", "reason:   confirmed via independent sources", out)

# ===================================================================
# 4. Confirmation gate actually blocks on 'n' and on blank input
# ===================================================================
for answer, label in [("n", "'n'"), ("", "blank")]:
    pages_4 = {
        "rec-gate-01": make_fake_page("page-gate-01", "rec-gate-01",
                                        key_takeaways="original text")
    }
    out, qfake, ufake = run_push_corrections_capturing(
        blocks=[{"record_id": "rec-gate-01", "field": "key_takeaways",
                  "new_value": "new text", "reason": "test"}],
        pages=pages_4,
        input_answers=[answer],
    )
    check(f"confirmation gate on {label} input: notion.pages.update NOT called", ufake.calls, 0)
    check_in(f"confirmation gate on {label} input: output says Declined", "Declined", out)

# Gate proceeds on 'y' and actually writes + re-verifies (covers #6 too)
pages_5 = {
    "rec-gate-02": make_fake_page("page-gate-02", "rec-gate-02",
                                    key_takeaways="original text")
}
out, qfake, ufake = run_push_corrections_capturing(
    blocks=[{"record_id": "rec-gate-02", "field": "key_takeaways",
              "new_value": "corrected text", "reason": "test"}],
    pages=pages_5,
    input_answers=["y"],
)
check("confirmation gate on 'y': notion.pages.update WAS called exactly once", ufake.calls, 1)
check("confirmation gate on 'y': at least 2 queries ran (initial lookup + post-write re-verify)",
      qfake.calls >= 2, True)

# ===================================================================
# 5. Out-of-scope-field warning: fires for a control_domains-style field,
#    does NOT fire for an in-scope prose field
# ===================================================================
pages_6 = {
    "rec-scope-01": make_fake_page("page-scope-01", "rec-scope-01",
                                     control_domains=["Access Control (AC)"]),
    "rec-scope-02": make_fake_page("page-scope-02", "rec-scope-02",
                                     key_takeaways="original text"),
}
out, qfake, ufake = run_push_corrections_capturing(
    blocks=[
        {"record_id": "rec-scope-01", "field": "control_domains",
          "new_value": "Risk Assessment (RA)", "reason": "vocab fix"},
        {"record_id": "rec-scope-02", "field": "key_takeaways",
          "new_value": "corrected text", "reason": "fact fix"},
    ],
    pages=pages_6,
    input_answers=["n", "n"],
)
out_blocks = out.split("--- Correction")
check_true("out-of-scope warning fires for control_domains block",
           "FIELD OUTSIDE NORMAL SCOPE" in out_blocks[1])
check_true("out-of-scope warning does NOT fire for the in-scope key_takeaways block",
           "FIELD OUTSIDE NORMAL SCOPE" not in out_blocks[2])

# ===================================================================
# 6. Post-write re-verification is a genuine re-query, not an echo of
#    new_value — proven via FakePagesUpdate's distinct MARKER suffix, which
#    can only appear in the output if push_corrections() actually re-read
#    the (mutated) fake store after writing, rather than just re-printing
#    the new_value variable already sitting in memory.
# ===================================================================
pages_7 = {
    "rec-verify-01": make_fake_page("page-verify-01", "rec-verify-01",
                                      executive_summary="stale value")
}
out, qfake, ufake = run_push_corrections_capturing(
    blocks=[{"record_id": "rec-verify-01", "field": "executive_summary",
              "new_value": "The fine was $409M.", "reason": "test"}],
    pages=pages_7,
    input_answers=["y"],
)
check_in("re-verification line present", "Re-verified live value:", out)
check_in("re-verified value carries the fake backend's marker (proves a real re-query happened)",
         "The fine was $409M." + FakePagesUpdate.MARKER, out)
check_not_in("re-verified value is NOT the bare unmarked new_value (would mean no real re-query ran)",
             "Re-verified live value: The fine was $409M.\n", out)

# ===================================================================
# 7. record_id not found in push_corrections() flow (not just find_record_page in isolation)
# ===================================================================
out, qfake, ufake = run_push_corrections_capturing(
    blocks=[{"record_id": "rec-does-not-exist", "field": "key_takeaways",
              "new_value": "whatever", "reason": "test"}],
    pages={},
    input_answers=[],  # should never reach a confirmation prompt
)
check_in("missing record_id reports 'No live record found'", "No live record found", out)
check("missing record_id never reaches notion.pages.update", ufake.calls, 0)

# ===================================================================
# 8. CORRECTION_FIELD_UNAVAILABLE — 'title' is refused with an explanation,
#    never even attempts a lookup
# ===================================================================
out, qfake, ufake = run_push_corrections_capturing(
    blocks=[{"record_id": "rec-title-01", "field": "title",
              "new_value": "New Title Text", "reason": "test"}],
    pages={"rec-title-01": make_fake_page("page-title-01", "rec-title-01")},
    input_answers=[],  # should never reach a confirmation prompt
)
check_in("'title' correction is refused with an explanation", "Cannot correct 'title'", out)
check("'title' correction never queries Notion at all", qfake.calls, 0)
check("'title' correction never reaches notion.pages.update", ufake.calls, 0)

# ===================================================================
# cleanup — restore real Notion query/update (each helper call already does
# this per-test; repeated here as an explicit final safety net)
# ===================================================================
nl.notion.databases.query = _ORIG_QUERY
nl.notion.pages.update    = _ORIG_UPDATE

print()
if failures:
    print(f"❌ {failures} test(s) FAILED")
else:
    print("✅ all push_corrections tests passed")
