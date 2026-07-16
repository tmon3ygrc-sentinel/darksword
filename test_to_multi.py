# test_to_multi.py — throwaway verification, delete after
# Confirms to_multi() is paren-aware: commas inside (...) are no longer
# treated as multi_select delimiters. See BOARD.md threat_actor ticket.
from notion_logger_v7 import to_multi, split_top_level

failures = 0

def check(label, val, expected):
    global failures
    got = to_multi(val)
    got_names = [g["name"] for g in got]
    ok = got_names == expected
    status = "PASS" if ok else "FAIL"
    if not ok:
        failures += 1
    print(f"{status} {label}: {got_names}  (expect {expected})")

# 1. THE ACTUAL REPRO — the exact string from the SENTINEL diagnosis.
check(
    "repro (parenthetical qualifier)",
    "APT41 (unconfirmed, sanctioned, multiple subscribers)",
    ["APT41 (unconfirmed, sanctioned, multiple subscribers)"],
)

# 2. NORMAL CASE — real clean control_domains value, must still split
#    correctly (no regression on the common, already-working case).
check(
    "clean multi-value (control_domains)",
    "Access Control (AC), Identification and Authentication (IA), System Integrity (SI)",
    ["Access Control (AC)", "Identification and Authentication (IA)", "System Integrity (SI)"],
)

# 3. SINGLE VALUE, NO COMMAS — trivial case.
check("single value", "unknown", ["unknown"])

# 4. NESTED PARENS — no real example found in the live corrupted-record
#    sweep on the board (all confirmed cases were single-level unmatched
#    parens), but a nested case is cheap to guard against regardless.
check(
    "nested parens",
    "Foo ((bar), baz), Bar",
    ["Foo ((bar), baz)", "Bar"],
)

# 5. UNBALANCED / UNCLOSED PAREN — must not crash or hang; degrades to
#    keeping the whole tail as one token rather than shredding it further.
check(
    "unclosed paren",
    "Foo (bar, baz",
    ["Foo (bar, baz"],
)

# 6. ORPHAN CLOSING PAREN (no matching open) — depth must clamp at 0,
#    not go negative; still splits on the comma outside it.
check(
    "orphan close paren",
    "foo), bar",
    ["foo)", "bar"],
)

# 7. Empty / falsy input — to_multi historically returns [] for "".
check("empty string", "", [])

print()
if failures:
    print(f"❌ {failures} test(s) FAILED")
else:
    print("✅ all to_multi() tests passed")
