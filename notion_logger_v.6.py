"""
🛡️ STAR CPE LOGGER V6.0 — PROJECT DARKSWORD
Autonomous Intelligence Pipeline
YouTube → Transcript → Claude Analysis → Notion
"""

import os
import re
import anthropic
from datetime import date
from pathlib import Path
from typing import List, Dict
from notion_client import Client
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

# ===================================================================
# 1. CONFIGURATION & DIRECTORIES
# ===================================================================
SCRIPT_DIR = Path(__file__).parent.absolute()
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

NOTION_TOKEN      = os.getenv("NOTION_TOKEN")
DATABASE_ID       = os.getenv("DATABASE_ID")
CMMC_DB_ID        = os.getenv("CMMC_DATABASE_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError("❌ Missing NOTION_TOKEN or DATABASE_ID in .env")
if not ANTHROPIC_API_KEY:
    raise ValueError("❌ Missing ANTHROPIC_API_KEY in .env")

notion = Client(auth=NOTION_TOKEN)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
print("✅ Notion + Claude clients initialized")

# ===================================================================
# 2. THE "NICKNAME" CACHE (Manual Entry Required)
# ===================================================================
LEARNING_CACHE = {
    "Week 25": "2d655ed740388178af99d35ef1ba8c60",
    "Week 26": "2d655ed7403881ffb921d8538a552713",
    "Week 27": "2d655ed74038811b88f7f71eb26aaa36",
}

CMMC_CACHE: Dict[str, str] = {}

# ===================================================================
# 3. FIELD MAPPINGS (GRC Standards)
# ===================================================================
SELECT_FIELDS = {
    "content_category", "exploit_maturity", "source", "story_type",
    "response_urgency", "asset_criticality", "active_exploitation",
    "confidence", "cisa_kev", "intel_type", "source_show"
}

MULTI_SELECT_FIELDS = {
    "detection_opportunities", "attack_tactic", "identity_impact",
    "content_type", "cpe_category", "tags", "kill_chain_phase",
    "impacted_identity_provider", "attack_techniques", "target_sector",
    "threat_actor", "priority_level", "intel_category", "control_domains",
    "dfir_phase", "investigation_type"
}

RICH_TEXT_FIELDS  = {"key_takeaways", "executive_summary", "operational_relevance", "record_id"}
DATE_FIELDS       = {"intel_date", "intel_timestamp"}
NUMBER_FIELDS     = {"risk_severity_score"}

SKIP_FIELDS = {
    "url", "title", "cpe_credits", "cmmc_mapping", "learning_phase",
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
detection_opportunities::
control_domains::
Master Frameworks(CMMC 2.0 / NIST 800-171)::
GRC_Learning_Plan_All_Phases::
impacted_identity_provider::
tags::
key_takeaways::
operational_relevance::
story_type::
executive_summary::
dfir_phase::
investigation_type::
===INTEL_RECORD_END===

### FIELD DEFINITIONS (STRICT)
- **record_id**: source-epNNNN-YYYY-MM-DD-## (e.g., simplycyber-ep1075-2026-02-24-01)
- **intel_date**: Date of the threat/event (YYYY-MM-DD).
- **intel_timestamp**: ISO 8601. If time is unknown, DEFAULT TO T14:00:00Z.
- **date_watched**: Date content was consumed (YYYY-MM-DD).
- **source**: Full name of source channel (e.g., Simply Cyber).
- **source_show**: The specific show or program name (e.g., Simply Cyber Daily Threat Brief).
- **url**: Direct link to the source/video.
- **title**: Concise, professional title of the specific threat event.
- **cpe_category**: Always "Technical" unless specified.
- **cpe_credits**: Always "0.05" per record.
- **content_type**: Always "Podcast/Video".
- **intel_category**: malware, vulnerability, campaign, advisory, breach, tooling, strategic, threat-actor.
- **kill_chain_phase**: reconnaissance, weaponization, delivery, exploitation, installation, command-and-control, actions-on-objectives.
- **attack_tactic**: MITRE ATT&CK tactics (lowercase, hyphenated).
- **attack_techniques**: MITRE ATT&CK technique IDs (UPPERCASE, e.g., T1190, T1059).
- **intel_type**: tactical, strategic, or operational.
- **asset_criticality**: tier-zero, high, medium, low.
- **identity_impact**: federated-identity, privileged-account, service-account, standard-user, none.
- **response_urgency**: immediate-action, monitor, strategic-review.
- **cisa_kev**: Explicitly "yes", "no", or "unknown".
- **confidence**: High, Medium, or Low.
- **priority_level**: Critical, High, Medium, or Low.
- **exploit_maturity**: poc, functional, weaponized, living-off-the-land, automated, unknown.
- **risk_severity_score**: 0-10. (0-3=low, 4-6=contained, 7-8=enterprise, 9-10=destructive).
- **detection_opportunities**: Specific technical indicators or SOC triggers (comma-separated).
- **control_domains**: Access-Control, Identity-and-Authentication, Endpoint-Security, Malware-Protection, Logging-and-Monitoring, Incident-Response, Threat-Intelligence, Secure-Configuration-Management, Cloud-Security, API-Security, Data-Protection, Privacy-and-Compliance, Security-Awareness-and-Training, Risk-Management.
- **Master Frameworks(CMMC 2.0 / NIST 800-171)**: CMMC 2.0 / NIST 800-171 Control IDs (comma-separated, e.g., AC.L2-3.1.1, IA.L2-3.5.3). Use "None" if no clear mapping.
- **GRC_Learning_Plan_All_Phases**: Map to the most relevant week using EXACTLY this format: "Week ## – [title]". Options: Week 25 – Developing security policies, Week 26 – Building compliance programs, Week 27 – Risk management frameworks. Leave blank if no clear match.
- **impacted_identity_provider**: on-prem-ad, entra-id, okta, google-workspace, mfa-provider, none, unknown.
- **tags**: ALL MITRE IDs (lowercase, e.g., t1190) AND descriptive keywords (lowercase-hyphenated).
- **story_type**: MUST be exactly one of: incident, vulnerability, advisory, strategic.
- **executive_summary**: Exactly 3 sentences. Sentence 1=what happened. Sentence 2=business impact. Sentence 3=what must be done.
- **dfir_phase**: DFIR phase if applicable (comma-separated): initial-triage, containment, eradication, recovery. Use "None" if not an active incident.
- **investigation_type**: Type of investigation warranted (comma-separated): threat-hunt, incident-response, vulnerability-assessment, compliance-review. Use "None" if not applicable.

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
- Repeated emphasis on a specific risk pattern indicating a trend
- Credentials, admin accounts, tenant access, or authentication mentioned
If uncertain, CREATE the record and mark confidence:: Low.

### EXTRACTION BIAS RULE
Prefer over-extraction. Missing a story is a failure. Including a low-confidence record is acceptable.

### PRE-OUTPUT VALIDATION STEP (MANDATORY)
Before finalizing output, you MUST:
1. Enumerate total stories identified from the transcript
2. Verify one complete record exists per story
3. Confirm no story meeting the qualification rules was omitted
4. If mismatch exists — regenerate before output
"""

# ===================================================================
# 5. AUTONOMOUS PIPELINE FUNCTIONS
# ===================================================================

def extract_video_id(url: str) -> str:
    """Handles all common YouTube URL formats."""
    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",       # ?v=ID
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})", # youtu.be/ID
        r"(?:live/)([a-zA-Z0-9_-]{11})",      # /live/ID
        r"(?:embed/)([a-zA-Z0-9_-]{11})",     # /embed/ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"❌ Could not extract video ID from URL: {url}")


def get_transcript(url: str) -> str:
    """Fetches YouTube transcript and returns as clean text."""
    print("📡 Fetching YouTube transcript...")
    video_id = extract_video_id(url)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t["text"] for t in transcript])
        word_count = len(text.split())
        print(f"✅ Transcript fetched: {word_count:,} words")
        return text
    except TranscriptsDisabled:
        raise RuntimeError("❌ Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise RuntimeError("❌ No transcript found. Try a video with captions enabled.")
    except Exception as e:
        raise RuntimeError(f"❌ Transcript fetch failed: {e}")


def analyze_with_claude(transcript: str, url: str, today: str) -> str:
    """Sends transcript to Claude and returns raw intel records text."""
    print("🤖 Sending to Claude for analysis (this may take 30-60 seconds)...")

    user_message = f"""Today's date is {today}. The source URL is: {url}

---TRANSCRIPT---
{transcript}

[END OF TRANSCRIPT - BEGIN ANALYSIS]"""

    response = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=ANALYST_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    result = response.content[0].text
    record_count = result.count("===INTEL_RECORD_START===")
    print(f"✅ Claude identified {record_count} intel record(s)")
    return result


def write_governance_file(content: str):
    """Writes Claude's output to governance_input.txt."""
    output_path = SCRIPT_DIR / "governance_input.txt"
    output_path.write_text(content, encoding="utf-8")
    print(f"✅ governance_input.txt written automatically")

# ===================================================================
# 6. SYSTEM FUNCTIONS (Notion)
# ===================================================================

def load_cmmc_cache():
    if not CMMC_DB_ID: return
    print("📡 Loading CMMC cache...")
    try:
        res = notion.databases.query(database_id=CMMC_DB_ID)
        for page in res.get("results", []):
            title_props = page["properties"].get("Name", {}).get("title", [])
            if title_props:
                cid = title_props[0].get("plain_text", "").strip()
                CMMC_CACHE[cid] = page["id"]
        print(f"✅ CMMC cache loaded: {len(CMMC_CACHE)} controls")
    except Exception as e:
        print(f"❌ CMMC cache failed: {e}")


def update_compliance_status(control_ids: List[str], log_page_url: str):
    for cid in control_ids:
        if cid in CMMC_CACHE:
            try:
                notion.pages.update(
                    page_id=CMMC_CACHE[cid],
                    properties={
                        "Status": {"select": {"name": "Evidence Pending"}},
                        "Last Evidence": {"url": log_page_url}
                    }
                )
                print(f"📡 GRC UPDATE: {cid} → Evidence Pending")
            except Exception as e:
                print(f"⚠️ GRC update failed for {cid}: {e}")

# ===================================================================
# 7. THE ENGINE (PUSH_RECORD)
# ===================================================================

def push_record(record: dict, source_label: str, url: str) -> bool:
    record_id = record.get("record_id", "unknown")
    page_title = f"{source_label} - {record_id}"

    props = {
        "Title":        {"title": [{"text": {"content": page_title}}]},
        "url":          {"url": url if url else None},
        "date_watched": {"date": {"start": date.today().isoformat()}},
        "cpe_credits":  {"number": 0.5},
    }

    for key, val in record.items():
        if key in SKIP_FIELDS or not val or val.lower() in ("none", "unknown", "empty"):
            continue
        if key in SELECT_FIELDS:
            props[key] = {"select": {"name": str(val).strip()}}
        elif key in MULTI_SELECT_FIELDS:
            items = [x.strip() for x in str(val).split(",")]
            props[key] = {"multi_select": [{"name": i} for i in items if i]}
        elif key in RICH_TEXT_FIELDS:
            props[key] = {"rich_text": [{"text": {"content": str(val)[:2000]}}]}
        elif key in DATE_FIELDS:
            props[key] = {"date": {"start": str(val).strip()}}
        elif key in NUMBER_FIELDS:
            try: props[key] = {"number": float(val)}
            except: pass

    # === CMMC / Master Frameworks Relation ===
    cmmc_raw = record.get("Master Frameworks(CMMC 2.0 / NIST 800-171)", "")
    if cmmc_raw and cmmc_raw.lower() != "none":
        cids = [x.strip() for x in cmmc_raw.split(",") if x.strip()]
        rels  = [{"id": CMMC_CACHE[cid]} for cid in cids if cid in CMMC_CACHE]
        if rels:
            props["Master Frameworks(CMMC 2.0 / NIST 800-171)"] = {"relation": rels}

    # === Learning Plan Relation ===
    learning_raw = record.get("GRC_Learning_Plan_All_Phases", "")
    if learning_raw:
        phase_key = re.split(r'\s[–-]\s', learning_raw)[0].strip()
        if phase_key in LEARNING_CACHE:
            props["GRC_Learning_Plan_All_Phases"] = {"relation": [{"id": LEARNING_CACHE[phase_key]}]}
            print(f"    🔗 Linked: {phase_key}")
        else:
            print(f"    ⚠️ No cache match for: '{phase_key}'")

    try:
        response = notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties=props
        )
        log_url = response.get("url")
        if cmmc_raw and log_url:
            update_compliance_status([x.strip() for x in cmmc_raw.split(",") if x.strip()], log_url)
        print(f"✅ Logged: {record_id}")
        return True
    except Exception as e:
        print(f"❌ Failed: {record_id} | {e}")
        return False

# ===================================================================
# 8. PARSER
# ===================================================================

def parse_records(file_path: Path) -> List[dict]:
    if not file_path.exists(): return []
    content = file_path.read_text(encoding="utf-8")
    blocks  = re.findall(r'===INTEL_RECORD_START===(.*?)===INTEL_RECORD_END===', content, re.DOTALL)
    records = []
    for block in blocks:
        raw = {}
        for line in block.strip().split('\n'):
            if '::' in line:
                k, v = line.split('::', 1)
                raw[k.strip()] = v.strip()
        if raw.get('record_id'):
            records.append(raw)
    return records

# ===================================================================
# 9. MAIN
# ===================================================================

def main():
    print("\n" + "="*60)
    print("🛡️  STAR CPE LOGGER V6.0 — PROJECT DARKSWORD")
    print("    Autonomous Intelligence Pipeline")
    print("="*60)

    load_cmmc_cache()

    while True:
        print("\n1. Daily Threat Brief (Autonomous)")
        print("2. Daily Threat Brief (Manual — paste your own .txt)")
        print("3. Exit")
        choice = input("\nSelection: ").strip()

        if choice == "3":
            break

        elif choice == "1":
            # ── FULLY AUTONOMOUS PATH ──────────────────────────────
            url = input("YouTube URL: ").strip()
            try:
                transcript   = get_transcript(url)
                today        = date.today().isoformat()
                raw_output   = analyze_with_claude(transcript, url, today)
                write_governance_file(raw_output)
            except Exception as e:
                print(f"❌ Pipeline failed: {e}")
                continue

            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            print(f"\n📋 Pushing {len(records)} record(s) to Notion...")
            for r in records:
                push_record(r, "Daily Threat Brief", url)

        elif choice == "2":
            # ── MANUAL FALLBACK PATH ───────────────────────────────
            url = input("Source URL: ").strip()
            input("Save AI output to governance_input.txt then press ENTER...")
            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            for r in records:
                push_record(r, "Daily Threat Brief", url)

if __name__ == "__main__":
    main()