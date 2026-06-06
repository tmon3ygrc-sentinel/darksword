"""
Standalone tool: transcribe a YouTube video using the Gemini API and write
the clean transcript to governance_input.txt.

Uses gemini-1.5-flash which accepts YouTube URLs natively — no audio
download, no yt-dlp, no Whisper. Designed for restricted or long-form
videos that YouTubeTranscriptApi cannot access.

The transcript is written as plain text so it can be inspected before
running the DARKSWORD pipeline, or piped directly through Choice 8 in
notion_logger_v7.py.

Usage:
    python gemini_ingest_tool.py <youtube_url>
    python gemini_ingest_tool.py          (prompts for URL)

Requires GEMINI_API_KEY in .env.
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent.absolute()
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUT_FILE    = SCRIPT_DIR / "governance_input.txt"


def scrub(text: str) -> str:
    text = re.sub(r'\b\d+:\d{2}\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def gemini_transcribe(url: str) -> str:
    """
    Sends a YouTube URL to Gemini 1.5 Flash and returns a clean transcript.
    Raises RuntimeError on API failure or missing key.
    """
    import google.generativeai as genai

    if not GEMINI_API_KEY:
        raise RuntimeError("❌ GEMINI_API_KEY not set in .env")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    print(f"📡 Sending to Gemini for transcription: {url}")

    response = model.generate_content([
        {
            "file_data": {
                "file_uri": url,
                "mime_type": "video/*"
            }
        },
        (
            "Provide a complete, verbatim transcription of all spoken content in this video. "
            "Output only the spoken words as plain text, preserving natural paragraph breaks. "
            "Do not include timestamps, speaker labels, or any commentary."
        )
    ])

    raw_text = response.text
    clean_text = scrub(raw_text)
    return clean_text


def main():
    url = sys.argv[1].strip() if len(sys.argv) > 1 else input("YouTube URL: ").strip()
    if not url:
        print("❌ No URL provided.")
        sys.exit(1)

    try:
        transcript = gemini_transcribe(url)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    word_count = len(transcript.split())
    print(f"✅ Transcript ready: {word_count:,} words")

    OUTPUT_FILE.write_text(transcript, encoding="utf-8")
    print(f"✅ Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
