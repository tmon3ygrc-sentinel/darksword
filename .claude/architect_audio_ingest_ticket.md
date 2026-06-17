# ARCHITECT DESIGN TICKET — Audio-Ingest Path (Choice 9)
## Status: SCOPED — design pass needed before build. Not started.
## Filed: 2026-06-16 | Owner: ARCHITECT (design) → OPS (build, behind AO gate)

## Problem
On thin-show-notes days, DARKSWORD has NO working automated capture path
for Simply Cyber episodes. The intel lives only in the audio; RSS show
notes are sponsor boilerplate (~234 words, zero story content).

## Diagnosis (data-backed, 2026-06-16 — read-only log forensics)
YouTube transcript fallback (Choice 7/8) is CHRONICALLY DEAD, not a one-off:
- 6 invocations logged (06-05, 06-08, 06-09, 06-10, 06-11, 06-16)
- 6 failures, 0 successes — 0% success rate
- Three distinct failure modes:
  • No YouTube URL in RSS (06-05)
  • Video unplayable/restricted (06-08, 06-09, 06-16)
  • Transcripts disabled (06-10, 06-11)
- Root cause: Simply Cyber's YT uploads are systematically not
  transcript-accessible to the pipeline. Not a fixable bug — a dead source.

Podcast audio enclosure is OPEN and grabbable (verified via curl on
feeds.transistor.fm/simply-cyber):
- Direct .mp3 on Transistor CDN, no auth, no DRM
- Example: https://media.transistor.fm/{id}/{id}.mp3, ~84–116MB, audio/mpeg
- Architectural reason it works where YT fails: podcast audio is MEANT
  for open distribution (every podcast app downloads it); YT uploads are
  access-controlled by the creator.

## Proposed path: Choice 9 — Audio Ingest
enclosure .mp3 → download → speech-to-text → transcript → (chunk/summarize)
→ Claude analysis → existing record pipeline → Notion

## OPEN DESIGN QUESTIONS (decide before building)
1. TRANSCRIPTION ENGINE (drives whole architecture):
   - Local Whisper / faster-whisper: free, private, but SLOW on CPU
     (~15–40 min for a 90-min file); needs ~1–3GB model download.
     → BLOCKER QUESTION: is there a GPU available? Changes everything.
   - Hosted STT (Gemini audio / Deepgram / AssemblyAI): fast, costs
     per-minute, reintroduces API dependency.
     → NOTE: just spent a session on Gemini-quota confabulations;
       weigh the irony/risk of a real Gemini audio dependency.
2. LONG-TRANSCRIPT HANDLING (the actual hard problem):
   - 90-min episode ≈ 12–15K words of rambling conversation.
   - Current Claude prompt is tuned for tidy, short show-notes input.
   - Needs: chunking strategy, OR a summarization pre-pass, OR prompt
     redesign to extract discrete stories from conversational transcript.
   - This is where the real engineering lives — getting GOOD records out
     of a long transcript ≠ parsing structured notes.
3. OPERATIONAL WEIGHT:
   - Download handling: ~100MB/episode (store-and-clean vs stream).
   - Run-time: 16-sec auto-run becomes multi-minute-to-tens-of-minutes.
     Does Task Scheduler tolerate a long-running --auto? Timeout impact?
   - Failure modes: partial downloads, transcription errors, retries.
   - Cost tracking if hosted STT.

## RELATED / FOLLOW-ON
- YT fallback (Choice 7/8) is 0/6 dead weight that still costs run-time
  (scrape → attempt → fail). Once audio-ingest works, decide: remove it,
  or leave as harmless-but-useless. (Not urgent.)
- The publish-race issue is SEPARATE (ep1153 fell through 14:00:41 vs
  14:00:17 run) — tracked in handover_2026-06-15.md. Audio-ingest doesn't
  fix the race; the race needs poll-with-retry or feed-triggered ingest.

## SCOPE DISCIPLINE
This is the largest build proposed for DARKSWORD. Design pass FIRST
(engine choice + transcript strategy + run-time model), THEN OPS builds
behind AO gate. Do NOT start implementation on momentum. Audio is a
permanent RSS feed — zero cost to designing it right.

## IMMEDIATE (separate from this build)
ep1153 + ep1154 capture, if wanted: Choice 2 manual (skim/listen →
governance_input.txt → push), behind AO gate. Two episodes do NOT justify
rushing the build.
