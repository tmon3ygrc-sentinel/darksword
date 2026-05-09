"""
🛡️ STAR CPE LOGGER V5.4 — PROJECT DARKSWORD
Standardized for GRC & 50-Week Learning Plan Integration
"""

import os
import re
from datetime import date
from pathlib import Path
from typing import List, Dict
from notion_client import Client
from dotenv import load_dotenv

# ===================================================================
# 1. CONFIGURATION & DIRECTORIES
# ===================================================================
SCRIPT_DIR = Path(__file__).parent.absolute()
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID  = os.getenv("DATABASE_ID") # Daily Threat Brief DB
CMMC_DB_ID   = os.getenv("CMMC_DATABASE_ID")

if not NOTION_TOKEN or not DATABASE_ID:
    raise ValueError("❌ Critical Environment Variables missing from .env")

notion = Client(auth=NOTION_TOKEN)
print("✅ Notion client initialized")

# ===================================================================
# 2. THE "NICKNAME" CACHE (Manual Entry Required)
# ===================================================================
# Paste the Page IDs for your Learning Plan weeks here. 
# You only have to do this once!
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
    "confidence", "cisa_kev", "intel_type"
}

MULTI_SELECT_FIELDS = {
    "detection_opportunities", "attack_tactic", "identity_impact",
    "content_type", "cpe_category", "tags", "kill_chain_phase", 
    "impacted_identity_provider", "attack_techniques", "target_sector", 
    "threat_actor", "priority_level", "intel_category", "control_domains"
}

RICH_TEXT_FIELDS = {"key_takeaways", "executive_summary", "operational_relevance"}
SKIP_FIELDS = {"record_id", "url", "title", "cpe_credits", "cmmc_mapping", "learning_phase"}

# ===================================================================
# 4. SYSTEM FUNCTIONS
# ===================================================================

def load_cmmc_cache():
    """Loads CMMC Control IDs into memory for instant mapping."""
    if not CMMC_DB_ID: return
    print("📡 Loading CMMC cache...")
    try:
        # Standardized Database Query (Fixes 'Invalid Request URL')
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
    """Writes back to the CMMC database to mark evidence."""
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
# 5. THE ENGINE (PUSH_RECORD)
# ===================================================================

def push_record(record: dict, source_label: str, url: str) -> bool:
    record_id = record.get("record_id", "unknown")
    page_title = f"{source_label} - {record_id}"

    # Build Base Properties
    props = {
        "Title": {"title": [{"text": {"content": page_title}}]},        
        "url": {"url": url if url else None},                          
        "date_watched": {"date": {"start": date.today().isoformat()}},
        "cpe_credits": {"number": 0.5},                                
    }

    # Map standard fields from .txt file
    for key, val in record.items():
        if key in SKIP_FIELDS or not val: continue
        if key in SELECT_FIELDS:
            props[key] = {"select": {"name": str(val).strip()}}
        elif key in MULTI_SELECT_FIELDS:
            items = [x.strip() for x in str(val).split(",")]
            props[key] = {"multi_select": [{"name": i} for i in items if i]}
        elif key in RICH_TEXT_FIELDS:
            props[key] = {"rich_text": [{"text": {"content": str(val)[:2000]}}]}

    # === CMMC Relations ===
    cmmc_raw = record.get("cmmc_mapping", "")
    if cmmc_raw:
        cids = [x.strip() for x in cmmc_raw.split(",") if x.strip()]
        rels = [{"id": CMMC_CACHE[cid]} for cid in cids if cid in CMMC_CACHE]
        if rels:
            props["Master Frameworks(CMMC 2.0 / NIST 800-171)"] = {"relation": rels}

    # === Learning Plan Relation (The "Nickname" Fix) ===
    learning_raw = record.get("learning_phase", "")
    if learning_raw:
        # Extract "Week 26" from "Week 26 – Building compliance programs"
        phase_key = learning_raw.split(" – ")[0].strip()
        if phase_key in LEARNING_CACHE:
            props["GRC_Learning_Plan_All_Phases"] = {"relation": [{"id": LEARNING_CACHE[phase_key]}]}
            print(f"    🔗 Linked to Learning Plan: {phase_key}")
# === TEMPORARY DEBUG: Run this once to see your column names ===
#    print("\n🔍 NOTION COLUMN NAMES DETECTED:")
#    print(list(notion.databases.retrieve(database_id=DATABASE_ID).get("properties").keys()))
#    import sys; sys.exit() # This stops the script so you can read the list
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
# 6. PARSER & MAIN
# ===================================================================

def parse_records(file_path: Path) -> List[dict]:
    if not file_path.exists(): return []
    content = file_path.read_text(encoding="utf-8")
    blocks = re.findall(r'===INTEL_RECORD_START===(.*?)===INTEL_RECORD_END===', content, re.DOTALL)
    records = []
    for block in blocks:
        raw = {}
        for line in block.strip().split('\n'):
            if '::' in line:
                k, v = line.split('::', 1)
                raw[k.strip()] = v.strip()
        if raw.get('record_id'): records.append(raw)
    return records

def main():
    print("\n" + "="*60 + "\n🛡️ STAR CPE LOGGER V5.4 — PROJECT DARKSWORD\n" + "="*60)
    load_cmmc_cache()
    
    while True:
        print("\n1. Daily Threat Brief\n2. Exit")
        choice = input("\nSelection: ").strip()
        if choice == "2": break
        
        url = input("Source URL: ").strip()
        input(f"Save AI output to governance_input.txt then press ENTER...")
        
        records = parse_records(SCRIPT_DIR / "governance_input.txt")
        for r in records:
            push_record(r, "Daily Threat Brief", url)

if __name__ == "__main__":
    main()