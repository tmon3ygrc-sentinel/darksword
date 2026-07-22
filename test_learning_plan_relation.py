# test_learning_plan_relation.py — throwaway verification, delete after
# Confirms the 2026-07-21 Linked CPE Records fanout fix: the explicit
# GRC_Learning_Plan_All_Phases/learning_phase -> LEARNING_CACHE path still
# fires exactly as before, and the removed DOMAIN_TO_WEEKS/CATEGORY_TO_WEEKS
# bucket-union path no longer sets any relation when a record only carries
# control_domains/intel_category tags.
#
# No live Notion traffic: notion.databases.query and notion.pages.create are
# both monkeypatched for the duration of the test, restored immediately after.
# LEARNING_CACHE is monkeypatched too (real values come from .env, usually
# empty in a test environment) so relation_ids has something non-empty to
# resolve against.

import notion_logger_v7 as nl

failures = 0


def check(label, got, expected):
    global failures
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    if not ok:
        failures += 1
    print(f"{status} {label}: {got!r}  (expect {expected!r})")


class FakeQueryCounter:
    """Every call succeeds, always returning `count` fake results — used
    for both the prefix-count query (seeds seq_cache) and the exists-check
    query (0 results = record doesn't exist yet, matches test_record_id.py's
    convention)."""
    def __init__(self, count):
        self.count = count
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        return {"results": [{"id": f"fake-{i}"} for i in range(self.count)], "has_more": False}


class FakePagesCreate:
    """Captures the properties a real notion.pages.create call would have
    received, without touching live Notion."""
    def __init__(self):
        self.calls = 0
        self.last_properties = {}

    def __call__(self, **kwargs):
        self.calls += 1
        self.last_properties = kwargs.get("properties", {})
        return {"url": "https://fake.notion.example/page"}


_orig_query = nl.notion.databases.query
_orig_create = nl.notion.pages.create
_orig_learning_cache = dict(nl.LEARNING_CACHE)

# Give "Week 13" and "Week 23" real-looking cache entries for the duration
# of this test — real LEARNING_CACHE values come from .env and are usually
# empty strings in a test environment, which would make relation_ids empty
# even on a legitimate hit and mask what we're actually trying to verify.
nl.LEARNING_CACHE["Week 13"] = "fake-notion-page-id-week13"
nl.LEARNING_CACHE["Week 23"] = "fake-notion-page-id-week23"

# ===================================================================
# 1. Explicit single-field path still fires — this is the doctrine-
#    compliant path (canonical_schema_v1.md) and must be untouched.
# ===================================================================
nl.notion.databases.query = FakeQueryCounter(0)
fake_create = FakePagesCreate()
nl.notion.pages.create = fake_create

record_explicit = {
    "GRC_Learning_Plan_All_Phases": "Week 13 – Role of governance in audit and control",
    "title": "explicit-path test record",
}
push_record_success, _ = nl.push_record(
    record_explicit, "Simply Cyber Daily Threat Brief", "https://example.com/test-explicit",
    {}, "2026-07-21", None,
)
check("explicit-path push_record() succeeds", push_record_success, True)
check("explicit-path sets GRC_Learning_Plan_All_Phases relation",
      fake_create.last_properties.get("GRC_Learning_Plan_All_Phases"),
      {"relation": [{"id": "fake-notion-page-id-week13"}]})

# ===================================================================
# 2. Bucket path (control_domains/intel_category -> DOMAIN_TO_WEEKS/
#    CATEGORY_TO_WEEKS) no longer fires. Before the fix, this record would
#    have linked Week 23 via BOTH dicts (Incident Response (IR) and
#    ransomware both map to Week 23) with zero relevance check.
# ===================================================================
nl.notion.databases.query = FakeQueryCounter(0)
fake_create2 = FakePagesCreate()
nl.notion.pages.create = fake_create2

record_bucket_only = {
    "control_domains": "Incident Response (IR)",
    "intel_category": "ransomware",
    "title": "bucket-path test record — no explicit learning-phase field",
}
push_record_success2, _ = nl.push_record(
    record_bucket_only, "Simply Cyber Daily Threat Brief", "https://example.com/test-bucket",
    {}, "2026-07-21", None,
)
check("bucket-only push_record() succeeds", push_record_success2, True)
check("bucket-only record sets NO Learning Plan relation",
      "GRC_Learning_Plan_All_Phases" in fake_create2.last_properties,
      False)

# ===================================================================
# cleanup — restore real Notion query/create + real LEARNING_CACHE
# ===================================================================
nl.notion.databases.query = _orig_query
nl.notion.pages.create = _orig_create
nl.LEARNING_CACHE.clear()
nl.LEARNING_CACHE.update(_orig_learning_cache)

print()
if failures:
    print(f"❌ {failures} test(s) FAILED")
else:
    print("✅ all Learning Plan relation tests passed")
