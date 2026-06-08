"""
add_missing_controls.py — one-off script.
Adds 4 missing CMMC controls to the Master Frameworks Notion database
(CMMC_DATABASE_ID from .env). Safe to re-run: each control prints its
new page ID so you can delete duplicates if needed.
"""

import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
CMMC_DB_ID   = os.getenv("CMMC_DATABASE_ID")

if not NOTION_TOKEN:
    raise SystemExit("❌ NOTION_TOKEN not set in .env")
if not CMMC_DB_ID:
    raise SystemExit("❌ CMMC_DATABASE_ID not set in .env")

notion = Client(auth=NOTION_TOKEN)

# ---------------------------------------------------------------------------
# Control definitions
# NIST 800-171 Ref: derived from the numeric suffix in each control ID.
# PM.L1-6.1.1 has no direct NIST 800-171 mapping (L1 PM comes from FAR
# 52.204-21), so that field is left blank.
# ---------------------------------------------------------------------------
CONTROLS = [
    {
        "Name":             "PM.L1-6.1.1",
        "Domain":           "Program Management",
        "Maturity":         "L1",
        "Practice Title":   "Establish and maintain a basic cybersecurity program",
        "NIST 800-171 Ref": "",
    },
    {
        "Name":             "SA.L2-3.13.1",
        "Domain":           "System & Services Acquisition",
        "Maturity":         "L2",
        "Practice Title":   "Establish and manage contracts for external system services",
        "NIST 800-171 Ref": "3.13.1",
    },
    {
        "Name":             "PE.L2-3.10.1",
        "Domain":           "Physical Protection",
        "Maturity":         "L2",
        "Practice Title":   "Limit physical access to organizational systems",
        "NIST 800-171 Ref": "3.10.1",
    },
    {
        "Name":             "PE.L2-3.10.2",
        "Domain":           "Physical Protection",
        "Maturity":         "L2",
        "Practice Title":   "Protect and monitor the physical facility",
        "NIST 800-171 Ref": "3.10.2",
    },
]


def build_properties(ctrl: dict) -> dict:
    props = {
        "Name":           {"title":     [{"text": {"content": ctrl["Name"]}}]},
        "Domain":         {"select":    {"name": ctrl["Domain"]}},
        "Maturity":       {"select":    {"name": ctrl["Maturity"]}},
        "Practice Title": {"rich_text": [{"text": {"content": ctrl["Practice Title"]}}]},
    }
    if ctrl.get("NIST 800-171 Ref"):
        props["NIST 800-171 Ref"] = {"rich_text": [{"text": {"content": ctrl["NIST 800-171 Ref"]}}]}
    return props


for ctrl in CONTROLS:
    try:
        page = notion.pages.create(
            parent={"database_id": CMMC_DB_ID},
            properties=build_properties(ctrl),
        )
        print(f"✅ Created: {ctrl['Name']}  →  page_id: {page['id']}")
    except Exception as e:
        print(f"❌ Failed:  {ctrl['Name']}  →  {e}")
