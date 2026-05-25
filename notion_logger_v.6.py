"""
⚔️  DARKSWORD — GRC Intelligence Platform V6.0
Autonomous Intelligence Pipeline
YouTube → Transcript → Claude Analysis → Notion

MODES:
  Live Mode  — Full autonomous pipeline (requires ANTHROPIC_API_KEY)
  Test Mode  — Bypasses API entirely, uses saved governance_input.txt
               Run 100 times for $0.00 until pipeline is bulletproof.

CHANGELOG v6.0:
  + Autonomous YouTube transcript fetching
  + Claude API analysis pipeline
  + --test flag for $0.00 debugging
  + Pagination in CMMC cache (handles >100 controls)
  + scrub() cleans transcript artifacts without destroying intel
  + Specific exception handling
  + Dual-key compatibility (Notion names + short names both work)
"""

import os
import re
import sys
import json
import time
import anthropic
from datetime import date
from pathlib import Path
from typing import List, Dict
from notion_client import Client
from dotenv import load_dotenv

# ===================================================================
# 1. CONFIGURATION & MODE DETECTION
# ===================================================================
SCRIPT_DIR = Path(__file__).parent.absolute()
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

# Run with: python notion_logger_v.6.py --test
TEST_MODE = "--test" in sys.argv

NOTION_TOKEN      = os.getenv("NOTION_TOKEN")
DATABASE_ID       = os.getenv("DATABASE_ID")
CMMC_DB_ID        = os.getenv("CMMC_DATABASE_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError("❌ Missing NOTION_TOKEN or DATABASE_ID in .env")

if not TEST_MODE and not ANTHROPIC_API_KEY:
    raise ValueError(
        "❌ Missing ANTHROPIC_API_KEY in .env\n"
        "   💡 Free debug mode: python notion_logger_v.6.py --test"
    )

notion = Client(auth=NOTION_TOKEN)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if not TEST_MODE else None

if TEST_MODE:
    print("⚠️  TEST MODE ACTIVE — Anthropic API will NOT be called. $0.00 cost.")
else:
    print("✅ Notion + Claude clients initialized")

# ===================================================================
# 2. CACHES
# ===================================================================
LEARNING_CACHE = {
    "Week 25": os.getenv("LEARNING_WEEK_25", ""),
    "Week 26": os.getenv("LEARNING_WEEK_26", ""),
    "Week 27": os.getenv("LEARNING_WEEK_27", ""),
}

CMMC_CACHE: Dict[str, str] = {}
CMMC_MISSES: List[str] = []

# ===================================================================
# 3. FIELD MAPPINGS
# ===================================================================
SELECT_FIELDS = {
    "content_category", "exploit_maturity", "source", "story_type",
    "response_urgency", "asset_criticality", "active_exploitation",
    "confidence", "cisa_kev", "intel_type", "source_show"
}

MULTI_SELECT_FIELDS = {
    "detection_opportunities", "attack_tactic",
    "content_type", "cpe_category", "tags", "kill_chain_phase",
    "identity_impact", "attack_techniques", "target_sector",
    "threat_actor", "priority_level", "intel_category", "control_domains",
    "dfir_phase", "investigation_type"
}

RICH_TEXT_FIELDS = {"key_takeaways", "executive_summary", "operational_relevance", "record_id"}
DATE_FIELDS      = {"intel_date", "intel_timestamp"}
NUMBER_FIELDS    = {"risk_severity_score"}

SKIP_FIELDS = {
    "url", "title", "cpe_credits",
    "cmmc_mapping", "learning_phase",
    "GRC_Learning_Plan_All_Phases",
    "Master Frameworks(CMMC 2.0 / NIST 800-171)"
}

# ===================================================================
# 4. ANALYST SYSTEM PROMPT
# ===================================================================
ANALYST_PROMPT = """
### MISSION OBJECTIVE
You are a Senior Intelligence Analyst for CPE logging.
Convert security transcripts into COMPLETE, Parser-Ready Intel Records with vCISO-grade intelligence value.
You MUST populate ALL fields. Use "Unknown" or "None" if data is unavailable.
DO NOT use markdown formatting in the output.
DO NOT use bullet points in field values.
DO NOT omit any fields.

### OUTPUT FORMAT RULES
- Format: fieldname:: value
- Multi-value: value1, value2 (no bullet points)
- Boundaries: ===INTEL_RECORD_START=== and ===INTEL_RECORD_END===
- NO markdown, NO conversational filler, NO bolding in values.

### PROCESSING GATE
If the message ends with: [END OF PART 1 - DO NOT ANALYZE YET]
Respond ONLY with: "Part received. Awaiting remaining transcript."
Do not perform analysis until you receive: [END OF TRANSCRIPT - BEGIN ANALYSIS]

### REQUIRED OUTPUT SCHEMA
===INTEL_RECORD_START===
record_id::
intel_date::
intel_timestamp::
date_watched::
source::
source_show::
url::
title::
cpe_category::
cpe_credits::
content_type::
threat_actor::
target_sector::
intel_category::
cisa_kev::
active_exploitation::
exploit_maturity::
kill_chain_phase::
attack_tactic::
attack_techniques::
risk_severity_score::
confidence::
priority_level::
asset_criticality::
identity_impact::
intel_type::
response_urgency::
identity_impact::
detection_opportunities::
control_domains::
Master Frameworks(CMMC 2.0 / NIST 800-171)::
GRC_Learning_Plan_All_Phases::
tags::
key_takeaways::
story_type::
operational_relevance::
executive_summary::
dfir_phase::
investigation_type::
===INTEL_RECORD_END===

### FIELD DEFINITIONS (STRICT)
- **record_id**: source-epNNNN-YYYY-MM-DD-## (e.g., simplycyber-ep1075-2026-02-24-01)
- **intel_date**: Date of the threat/event (YYYY-MM-DD).
- **intel_timestamp**: ISO 8601. If time unknown, DEFAULT TO T14:00:00Z.
- **date_watched**: Date content was consumed (YYYY-MM-DD).
- **source**: Full name of source channel (e.g., Simply Cyber).
- **source_show**: The specific show or program name (e.g., Simply Cyber Daily Threat Brief).
- **url**: Direct link to the source/video.
- **title**: Concise, professional title of the specific threat event.
- **cpe_category**: Always "Technical" unless specified.
- **cpe_credits**: Always "0.5" per record.
- **content_type**: Always "Podcast/Video".
- **intel_category**: malware, vulnerability, campaign, advisory, breach, tooling, threat-actor, governance, risk-management, identity-intelligence, strategic-intelligence, dfir, compliance. Select closest match(es). Do NOT invent new categories.
- **kill_chain_phase**: reconnaissance, weaponization, delivery, exploitation, installation, command-and-control, actions-on-objectives.
- **attack_tactic**: MITRE ATT&CK tactics (lowercase, hyphenated).
- **attack_techniques**: MITRE ATT&CK technique IDs (UPPERCASE, e.g., T1190, T1059).
- **intel_type**: tactical, strategic, or operational.
- **asset_criticality**: tier-zero, high, medium, low.
- **identity_impact**: Write 1-2 analyst sentences describing which identity types are impacted and how. Focus on blast radius and authentication context.
- **response_urgency**: immediate-action, scheduled, monitor, strategic-review.
- **cisa_kev**: Explicitly "yes", "no", or "unknown".
- **confidence**: High, Medium, or Low.
- **priority_level**: Critical, High, Medium, or Low.
- **exploit_maturity**: poc, functional, weaponized, living-off-the-land, automated, theoretical, unknown.
- **risk_severity_score**: 0-10.
- **detection_opportunities**: Specific technical indicators or SOC triggers (comma-separated).
- **control_domains**: Access Control (AC), Identification and Authentication (IA), Endpoint Security, Malware Protection, Logging and Monitoring (AU), Incident Response (IR), Threat Intelligence, Secure Configuration Management (CM), Cloud Security, API Security, Data Protection, Privacy and Compliance, Security Awareness and Training (AT), Risk Assessment (RA), Supply Chain Risk Management (SR), System Integrity (SI). Use full names exactly as shown.
- **Master Frameworks(CMMC 2.0 / NIST 800-171)**: CMMC 2.0 / NIST 800-171 Control IDs (comma-separated). Use "None" if no clear mapping.
- **GRC_Learning_Plan_All_Phases**: Map to the most relevant week: "Week ## - [title]". Options: Week 25 - Developing security policies, Week 26 - Building compliance programs, Week 27 - Risk management frameworks. Leave blank if no match.
- **identity_impact**: Who is impacted (comma-separated). Values: workforce-accounts, administrative-roles, system-administrators, security-operations, service-accounts, non-human-identities, executive-accounts, third-party-vendors, none, unknown.
- **tags**: ALL MITRE IDs (lowercase) AND descriptive keywords (lowercase-hyphenated).
- **story_type**: MUST be exactly one of: incident, vulnerability, advisory, strategic, legal-regulatory.
- **executive_summary**: Exactly 3 sentences.
- **dfir_phase**: initial-triage, containment, eradication, recovery. Use "None" if not active incident.
- **investigation_type**: threat-hunt, incident-response, vulnerability-assessment, compliance-review. Use "None" if not applicable.
- **content_category**: Threat Intelligence, AI Governance / Privacy Law, Technical, Management, DFIR, Compliance, Strategic, Legal-Regulatory. Select closest match. Do NOT invent new categories.

### INTELLIGENCE ANALYSIS GUIDELINES
1. Be Intelligence-Driven: Focus on threats, vulnerabilities, and defensive opportunities.
2. Use Analyst Judgment: Infer reasonable values when data is partial.
3. Prioritize Detection: Always think "how would a SOC catch this?"
4. Map to Frameworks: Always include MITRE ATT&CK mappings when possible.
5. Score Consistently: Use the defined 0-10 scale strictly.
6. Identity-First: Modern attacks target identity — always assess identity_impact.
7. CMMC Mapping: Always attempt to map to CMMC 2.0 controls. Priority: AC, IA, SI, AU, SC.

### STORY IDENTIFICATION RULES (MANDATORY)
A record MUST be created if ANY of the following are present:
- Named organization with security impact
- Mention of breach, data exposure, ransomware, or compromise
- Mention of vulnerability or active exploitation
- Mention of threat actor activity or campaign
- Security advisory tied to a specific technology or control failure
- Credentials, admin accounts, tenant access, or authentication mentioned
If uncertain, CREATE the record and mark confidence:: Low.

### EXTRACTION BIAS RULE
Prefer over-extraction. Missing a story is a failure.

### PRE-OUTPUT VALIDATION STEP (MANDATORY)
Before finalizing output:
1. Enumerate total stories identified
2. Verify one complete record exists per story
3. Confirm no qualifying story was omitted
4. If mismatch — regenerate before output
"""

# ===================================================================
# 5. UTILITY FUNCTIONS
#    Taken from Librarian's rewrite — cleaner property builders
# ===================================================================

def to_text(val: str) -> list:
    """Builds a Notion rich_text block from a string."""
    return [{"text": {"content": str(val)[:2000]}}] if val else []

def to_select(val: str) -> dict:
    """Builds a Notion select block from a string."""
    return {"name": str(val).strip()} if val else None

def to_multi(val: str) -> list:
    """Splits a comma-separated string into Notion multi_select blocks."""
    items = [x.strip() for x in str(val).split(",")]
    return [{"name": i} for i in items if i]

def scrub(text: str) -> str:
    """
    Cleans YouTube auto-caption artifacts from transcript text.

    SAFE removals (caption noise):
      - Timestamps: "0:00", "12:34"
      - Excess whitespace

    NOT removed (would destroy intel):
      - Brackets like [MITRE T1190], [CVE-2024-1234], [CISA KEV]
      - Any content that could be threat intelligence
    """
    text = re.sub(r'===INTEL_RECORD_(?:START|END)===', '', text)  # Injection defense pre-flight 
    text = re.sub(r'\b\d+:\d{2}\b', '', text)                     # Blade across the sky
    text = re.sub(r'\s+', ' ', text).strip()                      # Records markers fall silent 
    return text                                                   # No ghost in the shell
def normalize_cid(cid: str) -> str:
    """
    Canonical form for CMMC / NIST 800-171 control IDs.
    Uppercases, strips whitespace, collapses internal spaces to hyphens.

    Examples that all resolve to the same key:
      'SI.L2-3.14.1'  →  'SI.L2-3.14.1'
      'si.l2-3.14.1'  →  'SI.L2-3.14.1'
      ' SI.L2-3.14.1' →  'SI.L2-3.14.1'
      'SI.L2 3.14.1'  →  'SI.L2-3.14.1'
    """
    # Remove spaces around hyphens first, then strip remaining whitespace
    cid = cid.strip().upper()
    cid = re.sub(r'\s*-\s*', '-', cid)   # "SI.L2 - 3.14.1" → "SI.L2-3.14.1"
    cid = re.sub(r'\s+', '-', cid)        # any remaining spaces → hyphen
    return cid
# ===================================================================
# 6. PIPELINE FUNCTIONS
# ===================================================================

def extract_video_id(url: str) -> str:
    """Handles all common YouTube URL formats."""
    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:live/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"❌ Could not extract video ID from: {url}")


def get_transcript(url: str) -> str:
    """Fetches YouTube audio and transcribes using OpenAI Whisper."""
    import tempfile
    import whisper
    import yt_dlp

    print("📡 Downloading audio for transcription...")
    video_id = extract_video_id(url)

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = f"{tmpdir}/{video_id}.mp3"
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_path,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }],
            "quiet": True,
            "js_runtimes": {"node": {}},
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        print("🎙️ Transcribing with Whisper (this may take 1-2 minutes)...")
        model = whisper.load_model("base")
        result = model.transcribe(audio_path + ".mp3")
        raw_text = result["text"]

    clean_text = scrub(raw_text)
    print(f"✅ Transcript ready: {len(clean_text.split()):,} words")
    return clean_text

# ===================================================================
# 7. NOTION FUNCTIONS
# ===================================================================

def load_cmmc_cache():
    """
    Loads CMMC Control IDs into memory for instant relation mapping.
    Uses pagination to handle databases larger than 100 records.
    Credit: pagination logic from Librarian's rewrite.
    """
    if not CMMC_DB_ID:
        print("⚠️  CMMC_DB_ID not configured — skipping cache")
        return
    print("📡 Loading CMMC cache...")
    try:
        has_more = True
        cursor   = None
        while has_more:
            kwargs = {"database_id": CMMC_DB_ID, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            res = notion.databases.query(**kwargs)
            for page in res.get("results", []):
                title_props = page["properties"].get("Name", {}).get("title", [])
                if title_props:
                    cid = title_props[0].get("plain_text", "").strip()
                    if cid:
                        CMMC_CACHE[normalize_cid(cid)] = page["id"]
            has_more = res.get("has_more", False)
            cursor   = res.get("next_cursor")
        print(f"✅ CMMC cache loaded: {len(CMMC_CACHE)} controls")
    except Exception as e:
        print(f"❌ CMMC cache failed: {e}")


def update_compliance_status(control_ids: List[str], log_page_url: str):
    """Writes back to CMMC database to mark evidence."""
    for cid in control_ids:
        if normalize_cid(cid) in CMMC_CACHE:
            try:
                notion.pages.update(
                    page_id=CMMC_CACHE[normalize_cid(cid)],
                    properties={
                        "Status":        {"select": {"name": "Evidence Pending"}},
                        "Last Evidence": {"url": log_page_url}
                    }
                )
                print(f"📡 GRC UPDATE: {cid} → Evidence Pending")
            except Exception as e:
                print(f"⚠️  GRC update failed for {cid}: {e}")

# ===================================================================
# 8. THE ENGINE (PUSH_RECORD)
# ===================================================================

def push_record(record: dict, source_label: str, url: str) -> bool:
    record_id  = record.get("record_id", "unknown")
    page_title = f"{source_label} - {record_id}"

    # Hardcoded base properties — same every run
    props = {
        "Title":        {"title": [{"text": {"content": page_title}}]},
        "url":          {"url": url} if url else {},
        "date_watched": {"date": {"start": date.today().isoformat()}},
        "cpe_credits":  {"number": 0.5},
    }

    # Route each field to the correct Notion property format
    for key, val in record.items():
        if key in SKIP_FIELDS or not val:
            continue
        if str(val).lower() in ("none", "unknown", "empty", "n/a"):
            continue
        if key in SELECT_FIELDS:
            props[key] = {"select": to_select(val)}
        elif key in MULTI_SELECT_FIELDS:
            props[key] = {"multi_select": to_multi(val)}
        elif key in RICH_TEXT_FIELDS:
            props[key] = {"rich_text": to_text(val)}
        elif key in DATE_FIELDS:
            val_str = str(val).strip()
            # Guard: Notion requires a real date, not a bare time string
            if val_str and not val_str.startswith('T'):
                props[key] = {"date": {"start": val_str}}
        elif key in NUMBER_FIELDS:
            try:
                props[key] = {"number": float(val)}
            except (ValueError, TypeError):
                pass

    # === CMMC / Master Frameworks Relation ===
    # Accepts both key formats for compatibility with manual and autonomous flows
    cmmc_raw = (
        record.get("Master Frameworks(CMMC 2.0 / NIST 800-171)", "") or
        record.get("cmmc_mapping", "")
    )
    if cmmc_raw and str(cmmc_raw).lower() not in ("none", "unknown"):
        cids_raw = [x.strip() for x in cmmc_raw.split(",") if x.strip()]
        rels  = []
        missed = []
        for cid in cids_raw:
            norm = normalize_cid(cid)
            if norm in CMMC_CACHE:
                rels.append({"id": CMMC_CACHE[norm]})
            else:
                missed.append(cid)
        if rels:
            props["Master Frameworks(CMMC 2.0 / NIST 800-171)"] = {"relation": rels}
            print(f"    🔗 Linked {len(rels)} CMMC control(s)")
        if missed:
            print(f"    ⚠️  Unresolved CMMC IDs: {missed}")
            CMMC_MISSES.extend(f"{record_id}: {m}" for m in missed)
        

    # === Learning Plan Relation ===
    # Accepts both key formats for compatibility
    learning_raw = (
        record.get("GRC_Learning_Plan_All_Phases", "") or
        record.get("learning_phase", "")
    )
    if learning_raw:
        phase_key = re.split(r'\s[–-]\s', learning_raw)[0].strip()
        if phase_key in LEARNING_CACHE:
            props["GRC_Learning_Plan_All_Phases"] = {
                "relation": [{"id": LEARNING_CACHE[phase_key]}]
            }
            print(f"    🔗 Linked Learning Plan: {phase_key}")
        else:
            print(f"    ⚠️  No cache match for: '{phase_key}'")

    try:
        response = notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=props
        )
        log_url = response.get("url")
        if cmmc_raw and log_url:
            update_compliance_status(
                [x.strip() for x in cmmc_raw.split(",") if x.strip()],
                log_url
            )
        print(f"✅ Logged: {record_id}")
        return True
    except Exception as e:
        print(f"❌ Failed: {record_id} | {e}")
        return False

# ===================================================================
# 9. PARSER
# ===================================================================

def parse_records(file_path: Path) -> List[dict]:
    """Extracts all intel records from a governance_input.txt file."""
    if not file_path.exists():
        return []
    content = file_path.read_text(encoding="utf-8")
    blocks  = re.findall(
        r'===INTEL_RECORD_START===(.*?)===INTEL_RECORD_END===',
        content,
        re.DOTALL
    )
    records = []
    for block in blocks:
        raw = {}
        current_key = None
        for line in block.strip().split('\n'):
            if '::' in line:
                k, v = line.split('::', 1)
                current_key = k.strip()
                raw[current_key] = v.strip()
            elif current_key and line.strip():
                # continuation line — append to the current field
                raw[current_key] += ' ' + line.strip()
        if raw.get('record_id'):
            records.append(raw)
    return records
def push_all(records: list, source_label: str, url: str):
    """Pushes all records and saves any failures for retry."""
    failed = []
    for r in records:
        success = push_record(r, source_label, url)
        if not success:
            failed.append(r)
        time.sleep(0.4)

    if failed:
        fail_path = SCRIPT_DIR / "failed_records.txt"
        with open(fail_path, "a", encoding="utf-8") as f:
            for r in failed:
                f.write("===INTEL_RECORD_START===\n")
                for k, v in r.items():
                    f.write(f"{k}:: {v}\n")
                f.write("===INTEL_RECORD_END===\n\n")
        print(f"⚠️  {len(failed)} record(s) failed — saved to failed_records.txt")
    else:
        print(f"✅ All {len(records)} record(s) pushed successfully.")

# ===================================================================
# 10. MAIN
# ===================================================================

def main():
    print("\n" + "="*60)
    print("⚔️   DARKSWORD — GRC Intelligence Platform V6.0")
    if TEST_MODE:
        print("     💡 TEST MODE  |  $0.00  |  API Disconnected")
    else:
        print("     🔴 LIVE MODE  |  API Connected")
    print("="*60)

    load_cmmc_cache()

    while True:
        print("\n1. Autonomous Pipeline  (YouTube → Claude → Notion)")
        print("2. Manual Pipeline      (governance_input.txt → Notion)")
        if TEST_MODE:
            print("3. Test Pipeline        (Mock data → Notion) ← YOU ARE HERE")
        print("0. Exit")

        choice = input("\nSelection: ").strip()

        if choice == "0":
            break

        elif choice == "1":
            if TEST_MODE:
                print("❌ Autonomous mode disabled in --test. Run without --test flag.")
                continue
            url = input("YouTube URL: ").strip()
            if not url:
                print("❌ URL cannot be empty.")
                continue
            try:
                transcript = get_transcript(url)
                raw_output = analyze_with_claude(transcript, url, date.today().isoformat())
                write_governance_file(raw_output)
            except (RuntimeError, ValueError) as e:
                print(f"❌ Pipeline failed: {e}")
                continue
            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            print(f"\n📋 Pushing {len(records)} record(s) to Notion...")
            push_all(records, "Daily Threat Brief", url)

        elif choice == "2":
            url = input("Source URL: ").strip()
            input("Save AI output to governance_input.txt then press ENTER...")
            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            push_all(records, "Daily Threat Brief", url)

        elif choice == "3" and TEST_MODE:
            url = input("Source URL (for metadata): ").strip()
            raw_output = load_mock_data()
            write_governance_file(raw_output)
            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            print(f"\n📋 Pushing {len(records)} record(s) to Notion...")
            # REPLACE WITH:
            push_all(records, "Daily Threat Brief", url)

    # ── Post-run audit ─────────────────────────────────────────
    if CMMC_MISSES:
        print(f"\n{'='*60}")
        print(f"⚠️  CMMC MISS REPORT — {len(CMMC_MISSES)} unresolved ID(s)")
        print(f"{'='*60}")
        for entry in CMMC_MISSES:
            print(f"   ✗ {entry}")
        print("   Check: Claude output format vs Notion control name spelling.")
    else:
        print("\n✅ All CMMC IDs resolved cleanly.")

if __name__ == "__main__":
    main()