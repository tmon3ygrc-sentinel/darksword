# ARCHITECT DESIGN TICKET — Audio-Ingest Path (Choice 9)
## Status: SCOPED — design pass needed before build. Not started.
## Filed: 2026-06-16 | Updated: 2026-06-22 (root cause traced to ground truth)
## Owner: ARCHITECT (design) → OPS (build, behind AO gate)

## Problem
On thin/empty-show-notes days, DARKSWORD has no working automated capture
path. The intel lives in the audio; RSS show notes on those days are
sponsor boilerplate with no story content for Claude to extract.

## ROOT CAUSE — traced to ground truth (2026-06-22), not inferred
Earlier framing ("YouTube path 0/6, just unreliable") was a SYMPTOM-LEVEL
read. The code + changelog reveal the true mechanism:

1. PRIMARY PATH (get_show_notes → Claude → Notion) is the intended,
   working path. v7.0 was deliberately built around it.
   - Proof: ep1157 (2026-06-19), 1,462-word notes → 8 records, exit 0.
   - Fails-soft on thin notes: no story content = nothing to extract.

2. FALLBACK PATH (YouTube transcript via get_transcript) is VESTIGIAL
   and STRUCTURALLY DEAD — blocked at the network/IP level.
   - Proof: notion_logger_v7.py changelog lines 23-24, verbatim:
     "get_transcript() (Whisper/yt-dlp) still blocked for Simply Cyber
      at network/IP level. Use get_show_notes() for all Simply Cyber
      content."
   - The 0/7 failure rate was NOT seven restricted videos — it was ONE
     persistent network/IP block failing identically 7x. The per-video
     "unplayable or restricted" errors were the API's generic response
     to a blocked connection, MISATTRIBUTED as per-video restriction.
   - v7.0's get_show_notes() pivot was built to ESCAPE this exact block.
     The YouTube fallback is the OLD path still wired in — it cannot work
     for Simply Cyber, by design.

   >> LESSON (3rd instance this project): surface error attribution named
      a plausible-but-wrong cause. Schema error named "tags" (real cause:
      cumulative). Agent inferred "Gerald traveling" (real fact: word
      count). Transcript errors said "video restricted" (real cause:
      network block). Each time, ground truth — reading the actual
      system — beat the error's finger-point. When a fix that should work
      doesn't, re-measure; don't trust the attribution.

## FIX CONSTRAINT (the key design insight)
The block is HOST-level (YouTube/yt-dlp/Whisper path). Therefore:
- Any YouTube-based approach (yt-dlp, Whisper-on-YT-audio) is a DEAD END
  — same blocked host.
- Audio-ingest via the Transistor enclosure is VIABLE specifically
  because Transistor (media.transistor.fm) is a DIFFERENT, reachable host.
  - Enclosure confirmed reachable via curl on feeds.transistor.fm:
    direct .mp3, no auth, no DRM (~84–116MB, audio/mpeg).
  - PRE-BUILD CHECK: confirm the enclosure is reachable from the
    PIPELINE'S network (not just a browser) — the block is IP-level, so
    verify the pipeline host itself can pull the .mp3 before committing.

## Proposed path: Choice 9 — Audio Ingest
Transistor enclosure .mp3 → download → speech-to-text → transcript →
(chunk/summarize) → Claude analysis → existing record pipeline → Notion

## OPEN DESIGN QUESTIONS (decide before building)
1. TRANSCRIPTION ENGINE (drives whole architecture):
   - Local Whisper / faster-whisper: free, private, SLOW on CPU
     (~15–40 min for a 90-min file); ~1–3GB model download.
     → NOTE: Whisper was listed as part of the BLOCKED path — but the
       block is on the YouTube *source*, not Whisper itself. Whisper run
       on a Transistor-sourced .mp3 should be fine. Confirm.
     → BLOCKER QUESTION: GPU available? Changes everything.
   - Hosted STT (Gemini audio / Deepgram / AssemblyAI): fast, per-minute
     cost, reintroduces API dependency.
     → Irony flag: just spent a session on Gemini-quota confabulation;
       weigh a real Gemini audio dependency carefully.
2. LONG-TRANSCRIPT HANDLING (the actual hard problem):
   - 90-min episode ≈ 12–15K words of rambling conversation.
   - Current Claude prompt is tuned for tidy, short show-notes input.
   - Needs: chunking, OR summarization pre-pass, OR prompt redesign to
     extract discrete stories from conversational transcript.
   - This is where the real engineering lives.
3. OPERATIONAL WEIGHT:
   - Download ~100MB/episode (store-and-clean vs stream).
   - Run-time: 16-sec auto-run → multi-minute-to-tens-of-minutes.
     Task Scheduler timeout tolerance?
   - Failure modes: partial downloads, transcription errors, retries.
   - Cost tracking if hosted STT.

## RELATED / FOLLOW-ON
- REMOVE OR REPLACE THE VESTIGIAL YOUTUBE FALLBACK. It is dead by design
  (network-blocked), burns run-time (scrape → attempt → fail), and
  produces misleading "unplayable/restricted" errors that MASK the real
  state. Worse: thin-notes days currently exit 0 looking like clean
  no-ops when they are actually UNRECOVERED MISSES. Replace
  "try dead YouTube → exit 0" with "thin notes detected → flag for
  manual ingest / audio path." (ARCHITECT design)
- Publish-race issue is SEPARATE (ep1153 fell through 14:00:41 vs run) —
  tracked in handover_2026-06-15.md. Audio-ingest doesn't fix the race;
  race needs poll-with-retry or feed-triggered ingest.

## SCOPE DISCIPLINE
Largest build proposed for DARKSWORD. Design pass FIRST (engine choice +
transcript strategy + run-time model + the pipeline-network reachability
check), THEN OPS builds behind AO gate. Do NOT build on momentum.
Transistor feed is permanent — zero cost to designing it right.

## IMMEDIATE (separate from this build)
- ep1153, ep1154, ep1158: thin-notes / dead-fallback misses. Capture via
  Choice 2 manual ONLY IF the episode is worth it (guest-host episodes
  may be content-thin, not just notes-thin — judge per episode). Several
  fallen-through episodes do NOT justify rushing the build.
