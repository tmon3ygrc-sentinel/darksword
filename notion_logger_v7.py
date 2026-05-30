"""
⚔️  DARKSWORD — GRC Intelligence Platform V7.0
Autonomous Intelligence Pipeline
Show Notes → Claude Analysis → Notion

MODES:
  Live Mode  — Full autonomous pipeline (requires ANTHROPIC_API_KEY)
  Test Mode  — Bypasses API entirely, uses saved governance_input.txt
               Run 100 times for $0.00 until pipeline is bulletproof.

CHANGELOG v7.0:
  + get_show_notes() — fetches cyberthreatbrief.simplycyber.io directly
    Bypasses YouTube network block entirely. Zero yt-dlp, zero Whisper,
    zero FFmpeg. Date-addressable: backfill any day with YYYY-MM-DD.
  + analyze_with_claude() — implemented (was a stub in V6)
  + write_governance_file() — implemented (was a stub in V6)
  + load_mock_data() — implemented (was a stub in V6)
  + Choice 1 (Autonomous Pipeline) now fully operational for Simply Cyber
  + Model: claude-sonnet-4-6
  + get_transcript() retained for future non-blocked sources

KNOWN LIMITATIONS:
  - get_transcript() (Whisper/yt-dlp) still blocked for Simply Cyber at
    network/IP level. Use get_show_notes() for all Simply Cyber content.
  - Show notes page must be published before pipeline runs. Early AM runs
    may need to wait ~30 min after episode drops.
"""

import os
import re
import sys
import time
import anthropic
import feedparser
import requests
from datetime import date
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
from notion_client import Client
from dotenv import load_dotenv

# ===================================================================
# 1. CONFIGURATION & MODE DETECTION
# ===================================================================
SCRIPT_DIR = Path(__file__).parent.absolute()
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

# Run with: python notion_logger_v7.py --test
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
        "   💡 Free debug mode: python notion_logger_v7.py --test"
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
    "Week 1":  os.getenv("LEARNING_WEEK_1",  ""),
    "Week 2":  os.getenv("LEARNING_WEEK_2",  ""),
    "Week 3":  os.getenv("LEARNING_WEEK_3",  ""),
    "Week 5":  os.getenv("LEARNING_WEEK_5",  ""),
    "Week 6":  os.getenv("LEARNING_WEEK_6",  ""),
    "Week 7":  os.getenv("LEARNING_WEEK_7",  ""),
    "Week 8":  os.getenv("LEARNING_WEEK_8",  ""),
    "Week 10": os.getenv("LEARNING_WEEK_10", ""),
    "Week 11": os.getenv("LEARNING_WEEK_11", ""),
    "Week 12": os.getenv("LEARNING_WEEK_12", ""),
    "Week 13": os.getenv("LEARNING_WEEK_13", ""),
    "Week 14": os.getenv("LEARNING_WEEK_14", ""),
    "Week 15": os.getenv("LEARNING_WEEK_15", ""),
    "Week 17": os.getenv("LEARNING_WEEK_17", ""),
    "Week 18": os.getenv("LEARNING_WEEK_18", ""),
    "Week 19": os.getenv("LEARNING_WEEK_19", ""),
    "Week 20": os.getenv("LEARNING_WEEK_20", ""),
    "Week 21": os.getenv("LEARNING_WEEK_21", ""),
    "Week 23": os.getenv("LEARNING_WEEK_23", ""),
    "Week 24": os.getenv("LEARNING_WEEK_24", ""),
    "Week 25": os.getenv("LEARNING_WEEK_25", ""),
    "Week 26": os.getenv("LEARNING_WEEK_26", ""),
    "Week 27": os.getenv("LEARNING_WEEK_27", ""),
    "Week 28": os.getenv("LEARNING_WEEK_28", ""),
    "Week 29": os.getenv("LEARNING_WEEK_29", ""),
    "Week 30": os.getenv("LEARNING_WEEK_30", ""),
    "Week 33": os.getenv("LEARNING_WEEK_33", ""),
    "Week 35": os.getenv("LEARNING_WEEK_35", ""),
    "Week 36": os.getenv("LEARNING_WEEK_36", ""),
}

DOMAIN_TO_WEEKS = {
    "Incident Response (IR)":                    ["Week 23"],
    "Supply Chain Risk Management (SR)":         ["Week 19", "Week 29"],
    "Risk Assessment (RA)":                      ["Week 18", "Week 20"],
    "Access Control (AC)":                       ["Week 13"],
    "Identification and Authentication (IA)":    ["Week 13"],
    "Configuration Management (CM)":             ["Week 12"],
    "System Integrity (SI)":                     ["Week 17"],
    "System and Communications Protection (SC)": ["Week 17"],
    "Security Awareness and Training (AT)":      ["Week 5"],
    "Audit and Accountability (AU)":             ["Week 27", "Week 28"],
}

CATEGORY_TO_WEEKS = {
    "regulatory":            ["Week 25"],
    "advisory":              ["Week 26"],
    "supply-chain":          ["Week 19", "Week 29"],
    "incident":              ["Week 23"],
    "ransomware":            ["Week 23"],
    "campaign":              ["Week 18"],
    "vulnerability":         ["Week 20", "Week 21"],
    "malware":               ["Week 19"],
    "breach":                ["Week 28"],
    "law-enforcement":       ["Week 25"],
    "ai-risk":               ["Week 17"],
    "phishing":              ["Week 23"],
    "identity-intelligence": ["Week 13"],
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
    "identity_impact", "impacted_identity_provider",
    "content_type", "cpe_category", "tags", "kill_chain_phase",
    "attack_techniques", "target_sector",
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
Only use control IDs that exist in CMMC 2.0 / NIST 800-171 Rev 2. 
Do NOT invent or approximate control IDs. If unsure, use "None".

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
- **Master Frameworks(CMMC 2.0 / NIST 800-171)**: CMMC 2.0 Control IDs in exact format XX.L#-#.##.# (e.g., AC.L1-3.1.1, SI.L2-3.14.1, IR.L2-3.6.1). Comma-separated. Use "None" if no clear mapping.
  CRITICAL EXCEPTIONS — these are frequent errors:
  - IA 3.5.1 and 3.5.2: these originate from FAR 52.204-21 and are Level 1 practices in the DoD CMMC model. ALWAYS write IA.L1-3.5.1 and IA.L1-3.5.2. NEVER write IA.L2-3.5.1 or IA.L2-3.5.2 — those IDs do not exist in the official CMMC model.
  - SR controls: valid requirement ranges are 3.15.x and 3.24.x ONLY (e.g., SR.L2-3.15.1, SR.L2-3.24.1). SR.L2-3.17.x does not exist — do NOT output any SR.3.17.x ID. Use "None" if no valid SR control applies.
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
# 4b. OTX ANALYST PROMPT (tuned for AlienVault pulse metadata)
# ===================================================================
OTX_ANALYST_PROMPT = (
    ANALYST_PROMPT
    # Schema: pre-fill content_type so Claude never defaults to "Podcast/Video";
    # add content_category immediately after it (was absent from schema entirely)
    .replace(
        'content_type::\n',
        'content_type:: Threat Intelligence Feed\ncontent_category:: Threat Intelligence\n'
    )
    # Schema: add impacted_identity_provider before the closing marker
    # (was absent from schema entirely — third replace in original was a no-op)
    .replace(
        'investigation_type::\n===INTEL_RECORD_END===',
        'investigation_type::\nimpacted_identity_provider::\n===INTEL_RECORD_END==='
    )
    # Field def: explicitly forbid the Podcast/Video default
    .replace(
        '- **content_type**: Always "Podcast/Video".',
        '- **content_type**: ALWAYS "Threat Intelligence Feed" for OTX pulses. Do NOT use "Podcast/Video".'
    )
    # Field def: content_category with OTX default; add explicit "do not leave blank"
    .replace(
        '- **content_category**: Threat Intelligence, AI Governance / Privacy Law, Technical, Management, DFIR, Compliance, Strategic, Legal-Regulatory. Select closest match. Do NOT invent new categories.',
        '- **content_category**: For OTX pulses, default to "Threat Intelligence". Override only if content is clearly advisory, compliance, or strategic. Do NOT leave blank.'
    )
    # Field def: inject impacted_identity_provider definition (missing from base prompt)
    .replace(
        '- **investigation_type**:',
        '- **impacted_identity_provider**: Identity provider targeted by this threat. ALWAYS populate. Values (comma-separated): on-prem-ad, entra-id, okta, google-workspace, mfa-provider, aws-iam, none, unknown. Use "unknown" if unclear. Do NOT leave blank.\n- **investigation_type**:'
    )
)

# ===================================================================
# 5. UTILITY FUNCTIONS
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
    Cleans transcript/show notes artifacts from raw fetched text.

    SAFE removals:
      - INTEL_RECORD markers (injection defense pre-flight)
      - Timestamps: "0:00", "12:34"
      - Excess whitespace

    NOT removed (would destroy intel):
      - Brackets like [MITRE T1190], [CVE-2024-1234], [CISA KEV]
    """
    text = re.sub(r'===INTEL_RECORD_(?:START|END)===', '', text)
    text = re.sub(r'\b\d+:\d{2}\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_cid(cid: str) -> str:
    """
    Canonical form for CMMC / NIST 800-171 control IDs.

    Examples:
      'SI.L2-3.14.1'  →  'SI.L2-3.14.1'
      'si.l2-3.14.1'  →  'SI.L2-3.14.1'
      'SI.L2 3.14.1'  →  'SI.L2-3.14.1'
    """
    cid = cid.strip().upper()
    cid = re.sub(r'\s*-\s*', '-', cid)
    cid = re.sub(r'\s+', '-', cid)
    return cid

# ===================================================================
# 6. PIPELINE FUNCTIONS
# ===================================================================

def get_show_notes(target_date: str = None) -> tuple:
    """
    Fetches structured show notes from cyberthreatbrief.simplycyber.io.

    Replaces get_transcript() for Simply Cyber content — no YouTube API,
    no yt-dlp, no Whisper, no FFmpeg. Just a clean web fetch.

    Args:
        target_date: YYYY-MM-DD string. Defaults to today.
                     Use this to backfill: get_show_notes("2026-05-20")

    Returns:
        (clean_text, canonical_url) tuple

    Raises:
        RuntimeError: Episode not found or page fetch failed.
    """
    date_str = target_date or date.today().isoformat()
    print(f"📡 Fetching show notes for {date_str}...")

    # Step 1: Find today's episode URL from the listing page
    listing_url = "https://cyberthreatbrief.simplycyber.io/episodes/"
    try:
        resp = requests.get(listing_url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"❌ Could not reach episodes listing: {e}")

    soup = BeautifulSoup(resp.text, "html.parser")
    episode_url = None

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if date_str in href and "top-cyber-news-now" in href:
            episode_url = (
                href if href.startswith("http")
                else f"https://cyberthreatbrief.simplycyber.io{href}"
            )
            break

    if not episode_url:
        raise RuntimeError(
            f"❌ No episode found for {date_str}.\n"
            f"   Check: {listing_url}\n"
            f"   Episode may not be published yet — try again in 30 min."
        )

    print(f"📄 Episode found: {episode_url}")

    # Step 2: Fetch the episode page
    try:
        ep_resp = requests.get(episode_url, timeout=15)
        ep_resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"❌ Could not fetch episode page: {e}")

    ep_soup = BeautifulSoup(ep_resp.text, "html.parser")

    # Strip nav/footer/script noise — keep article body only
    for tag in ep_soup(["nav", "footer", "script", "style", "header"]):
        tag.decompose()

    raw_text = ep_soup.get_text(separator="\n", strip=True)
    clean_text = scrub(raw_text)

    print(f"✅ Show notes ready: {len(clean_text.split()):,} words")
    return clean_text, episode_url


def get_rss_episode_date() -> str:
    """
    Returns the publish date of the most recent Simply Cyber episode as YYYY-MM-DD.

    Parses the Transistor RSS feed and extracts pubDate from the latest entry.
    Used by Choice 5 to auto-detect today's episode date without requiring
    manual input, then passes the date to get_show_notes() for content fetch.

    Returns:
        YYYY-MM-DD string from the latest entry's pubDate.

    Raises:
        RuntimeError: Feed unreachable, parse failure, or no entries found.
    """
    FEED_URL = "https://feeds.transistor.fm/simply-cyber"
    print(f"📡 Checking RSS feed for latest episode date: {FEED_URL}...")

    feed = feedparser.parse(FEED_URL)

    if feed.bozo and not feed.entries:
        raise RuntimeError(f"❌ RSS feed parse failed: {feed.bozo_exception}")

    if not feed.entries:
        raise RuntimeError("❌ No episodes found in feed.")

    latest = feed.entries[0]
    title  = latest.get("title", "Unknown")

    parsed = latest.get("published_parsed")
    if not parsed:
        raise RuntimeError("❌ No pubDate found in latest feed entry.")

    date_str = f"{parsed.tm_year:04d}-{parsed.tm_mon:02d}-{parsed.tm_mday:02d}"
    print(f"✅ Latest episode: {title} → {date_str}")
    return date_str


def analyze_with_claude(content: str, url: str, today: str) -> str:
    """
    Sends content to Claude for intel record extraction.

    Args:
        content:  Cleaned show notes or transcript text.
        url:      Source URL (included in user message for context).
        today:    YYYY-MM-DD date string for date_watched field.

    Returns:
        Raw Claude output string containing ===INTEL_RECORD=== blocks.
    """
    print("🧠 Analyzing with Claude (claude-sonnet-4-6)...")

    user_message = (
        f"Source URL: {url}\n"
        f"Date Watched: {today}\n\n"
        f"CONTENT:\n{content}\n\n"
        f"[END OF TRANSCRIPT - BEGIN ANALYSIS]"
    )

    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=ANALYST_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    raw_output = message.content[0].text
    record_count = raw_output.count("===INTEL_RECORD_START===")
    print(f"✅ Claude analysis complete — {record_count} record(s) extracted")
    return raw_output

def analyze_with_claude_prompt(content: str, url: str, today: str, prompt: str) -> str:
    """
    Same as analyze_with_claude() but accepts a custom system prompt.
    Used for non-show-notes sources like OTX that need tailored extraction.
    """
    print("🧠 Analyzing with Claude (claude-sonnet-4-6)...")
    user_message = (
        f"Source URL: {url}\n"
        f"Date Watched: {today}\n\n"
        f"CONTENT:\n{content}\n\n"
        f"[END OF TRANSCRIPT - BEGIN ANALYSIS]"
    )
    message = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    raw_output = message.content[0].text
    record_count = raw_output.count("===INTEL_RECORD_START===")
    print(f"✅ Claude analysis complete — {record_count} record(s) extracted")
    return raw_output


def write_governance_file(content: str):
    """Writes Claude output to governance_input.txt for parsing."""
    starts = content.count("===INTEL_RECORD_START===")
    ends   = content.count("===INTEL_RECORD_END===")
    if starts != ends:
        print(f"⚠️  Marker mismatch — {starts} START vs {ends} END markers.")
        print(f"   Last record may be truncated. Consider increasing max_tokens.")
    out_path = SCRIPT_DIR / "governance_input.txt"
    out_path.write_text(content, encoding="utf-8")
    print(f"✅ Governance file written → {out_path.name}")


def load_mock_data() -> str:
    """
    Test Mode only. Reads existing governance_input.txt as mock Claude output.
    Costs $0.00. Tests the full Notion push pipeline without any API calls.
    """
    mock_path = SCRIPT_DIR / "governance_input.txt"
    if not mock_path.exists():
        raise FileNotFoundError(
            "❌ governance_input.txt not found.\n"
            "   Add records to the file first, then run --test again."
        )
    content = mock_path.read_text(encoding="utf-8")
    record_count = content.count("===INTEL_RECORD_START===")
    print(f"✅ Mock data loaded — {record_count} record(s) found")
    return content


def extract_video_id(url: str) -> str:
    """Handles all common YouTube URL formats. Retained for non-blocked sources."""
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

def get_otx_pulses(api_key: str, lookback_hours: int = 24) -> list:
    """
    Fetches relevant threat intelligence pulses from AlienVault OTX.
    
    Three-gate filter before Claude sees anything:
      Gate 1 — Time: only pulses from last lookback_hours
      Gate 2 — Relevance: only pulses matching DARKSWORD focus tags
      Gate 3 — Deduplication: no repeat pulse IDs
    
    Returns:
        List of dicts with keys: name, description, url, tags, indicators
    """
    from OTXv2 import OTXv2
    from datetime import datetime, timedelta

    RELEVANT_TAGS = {
        'ransomware', 'apt', 'nation-state',
        'critical-infrastructure', 'cisa',
        'supply-chain', 'phishing', 'identity',
        'malware', 'vulnerability', 'exploit',
        'lateral-movement', 'credential-access'
    }

    print(f"📡 Fetching OTX pulses (last {lookback_hours}hrs)...")

    # Gate 1 — Time filter
    since = (datetime.utcnow() - timedelta(hours=lookback_hours)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        otx    = OTXv2(api_key)
        pulses = otx.getall(modified_since=since)
    except Exception as e:
        raise RuntimeError(f"❌ OTX fetch failed: {e}")

    print(f"   Raw pulses last {lookback_hours}hrs: {len(pulses)}")

    # Gate 2 — Relevance filter
    def is_relevant(pulse):
        pulse_tags = {t.lower() for t in pulse.get('tags', [])}
        return bool(pulse_tags & RELEVANT_TAGS)

    relevant = [p for p in pulses if is_relevant(p)]
    print(f"   After relevance filter: {len(relevant)}")

    # Gate 3 — Deduplication
    seen_ids = set()
    unique   = []
    for p in relevant:
        if p['id'] not in seen_ids:
            seen_ids.add(p['id'])
            unique.append(p)

    print(f"   After deduplication: {len(unique)} pulse(s) queued for Claude")

    # Format for analyze_with_claude()
    results = []
    for p in unique:
        content = (
            f"Pulse: {p.get('name', 'Unknown')}\n"
            f"Description: {p.get('description', 'None')}\n"
            f"Tags: {', '.join(p.get('tags', []))}\n"
            f"Indicators: {len(p.get('indicators', []))} IOCs\n"
            f"Author: {p.get('author_name', 'Unknown')}\n"
            f"Created: {p.get('created', 'Unknown')}\n"
        )
        results.append({
            "content": content,
            "url":     f"https://otx.alienvault.com/pulse/{p['id']}",
            "name":    p.get('name', 'OTX Pulse'),
        })

    return results

def get_transcript(url: str) -> str:
    """
    Fetches YouTube audio and transcribes using OpenAI Whisper.
    Retained for non-blocked sources (Barricade, Cybernews, etc.)
    NOTE: Blocked at network/IP level for Simply Cyber — use get_show_notes().
    """
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

def load_cmmc_cache(retries: int = 3, delay: int = 15):
    """
    Loads CMMC Control IDs into memory for instant relation mapping.
    Retries up to 3 times on rate limit before giving up.
    """
    if not CMMC_DB_ID:
        print("⚠️  CMMC_DB_ID not configured — skipping cache")
        return
    
    for attempt in range(1, retries + 1):
        print(f"📡 Loading CMMC cache (attempt {attempt}/{retries})...")
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
            return  # Success — exit the retry loop
        except Exception as e:
            if "rate limited" in str(e).lower():
                if attempt < retries:
                    print(f"⏳ Rate limited — waiting {delay}s before retry...")
                    time.sleep(delay)
                else:
                    print(f"❌ CMMC cache failed after {retries} attempts: {e}")
            else:
                print(f"❌ CMMC cache failed: {e}")
                return  # Non-rate-limit error — don't retry


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

    props = {
        "Title":        {"title": [{"text": {"content": page_title}}]},
        "url":          {"url": url} if url else {},
        "date_watched": {"date": {"start": date.today().isoformat()}},
        "cpe_credits":  {"number": 0.5},
    }

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
            if val_str and not val_str.startswith('T'):
                props[key] = {"date": {"start": val_str}}
        elif key in NUMBER_FIELDS:
            try:
                props[key] = {"number": float(val)}
            except (ValueError, TypeError):
                pass

    # === CMMC / Master Frameworks Relation ===
    cmmc_raw = (
        record.get("Master Frameworks(CMMC 2.0 / NIST 800-171)", "") or
        record.get("cmmc_mapping", "")
    )
    if cmmc_raw and str(cmmc_raw).lower() not in ("none", "unknown"):
        cids_raw = [x.strip() for x in cmmc_raw.split(",") if x.strip()]
        rels   = []
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

    # === Learning Plan Relation (Auto-detect from content) ===
    linked_weeks = set()

    # 1. Explicit override from record
    learning_raw = (
        record.get("GRC_Learning_Plan_All_Phases", "") or
        record.get("learning_phase", "")
    )
    if learning_raw:
        phase_key = re.split(r'\s[–-]\s', learning_raw)[0].strip()
        if phase_key in LEARNING_CACHE:
            linked_weeks.add(phase_key)

    # 2. Auto-map from control_domains
    domains_raw = record.get("control_domains", "") or ""
    for domain in [d.strip() for d in domains_raw.split(",")]:
        for week in DOMAIN_TO_WEEKS.get(domain, []):
            linked_weeks.add(week)

    # 3. Auto-map from intel_category
    cats_raw = record.get("intel_category", "") or ""
    for cat in [c.strip() for c in cats_raw.split(",")]:
        for week in CATEGORY_TO_WEEKS.get(cat, []):
            linked_weeks.add(week)

    if linked_weeks:
        relation_ids = [
            {"id": LEARNING_CACHE[w]}
            for w in sorted(linked_weeks)
            if w in LEARNING_CACHE and LEARNING_CACHE[w]
        ]
        if relation_ids:
            props["GRC_Learning_Plan_All_Phases"] = {"relation": relation_ids}
            print(f"    🔗 Linked Learning Plan: {', '.join(sorted(linked_weeks))}")

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
    print("⚔️   DARKSWORD — GRC Intelligence Platform V7.0")
    if TEST_MODE:
        print("     💡 TEST MODE  |  $0.00  |  API Disconnected")
    else:
        print("     🔴 LIVE MODE  |  API Connected")
    print("="*60)

    load_cmmc_cache()

    while True:
        print("\n1. Autonomous Pipeline  (Show Notes → Claude → Notion)")
        print("2. Manual Pipeline      (governance_input.txt → Notion)")
        if TEST_MODE:
            print("3. Test Pipeline        (Mock data → Notion) ← YOU ARE HERE")
        print("4. OTX Pipeline         (AlienVault → Claude → Notion)")
        print("5. RSS Feed Pipeline    (Barricade Cyber → Claude → Notion)")
        print("0. Exit")

        choice = input("\nSelection: ").strip()

        if choice == "0":
            break

        elif choice == "1":
            if TEST_MODE:
                print("❌ Autonomous mode disabled in --test. Run without --test flag.")
                continue
            date_input = input("Date (YYYY-MM-DD, blank = today): ").strip() or None
            try:
                content, url = get_show_notes(date_input)
                raw_output = analyze_with_claude(content, url, date.today().isoformat())
                write_governance_file(raw_output)
            except (RuntimeError, ValueError, FileNotFoundError) as e:
                print(f"❌ Pipeline failed: {e}")
                continue
            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            print(f"\n📋 Pushing {len(records)} record(s) to Notion...")
            push_all(records, "Simply Cyber Daily Threat Brief", url)

        elif choice == "2":
            url = input("Source URL: ").strip()
            input("Save AI output to governance_input.txt then press ENTER...")
            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            push_all(records, "Daily Threat Brief", url)

        elif choice == "3" and TEST_MODE:
            url = input("Source URL (for metadata): ").strip()
            try:
                raw_output = load_mock_data()
            except FileNotFoundError as e:
                print(e)
                continue
            write_governance_file(raw_output)
            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            print(f"\n📋 Pushing {len(records)} record(s) to Notion...")
            push_all(records, "Daily Threat Brief", url)
        elif choice == "4":
            if TEST_MODE:
                print("❌ OTX mode disabled in --test.")
                continue
            otx_key = os.getenv("OTX_API_KEY")
            if not otx_key:
                print("❌ OTX_API_KEY not set in .env")
                continue
            try:
                pulses = get_otx_pulses(otx_key)
            except RuntimeError as e:
                print(e)
                continue
            if not pulses:
                print("✅ No relevant pulses found in last 24hrs.")
                continue
            print(f"\n📋 Sending {len(pulses)} pulse(s) to Claude...")
            all_records = []
            for pulse in pulses:
                raw = analyze_with_claude_prompt(
                    pulse["content"],
                    pulse["url"],
                    date.today().isoformat(),
                    OTX_ANALYST_PROMPT
                )
                write_governance_file(raw)
                records = parse_records(SCRIPT_DIR / "governance_input.txt")
                all_records.extend(records)
            print(f"\n📋 Pushing {len(all_records)} record(s) to Notion...")
            push_all(all_records, "AlienVault OTX", "https://otx.alienvault.com")

        elif choice == "5":
            if TEST_MODE:
                print("❌ RSS auto-detect mode disabled in --test.")
                continue
            try:
                date_str        = get_rss_episode_date()
                content, url    = get_show_notes(date_str)
                raw_output      = analyze_with_claude(content, url, date.today().isoformat())
                write_governance_file(raw_output)
            except (RuntimeError, ValueError) as e:
                print(f"❌ Pipeline failed: {e}")
                continue
            records = parse_records(SCRIPT_DIR / "governance_input.txt")
            print(f"\n📋 Pushing {len(records)} record(s) to Notion...")
            push_all(records, "Simply Cyber Daily Threat Brief", url)

    # ── Post-run audit ──────────────────────────────────────────
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