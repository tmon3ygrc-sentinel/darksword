You are operating within the DARKSWORD GRC Intelligence Platform. 
The pipeline code lives at C:\Work\GRC\darksword\notion_logger_v7.py.
Agent briefings are in C:\Work\GRC\darksword\.claude\
Session board/backlog: C:\Work\GRC\boards\BOARD.md — read FIRST each session.
Mount boards\, not darksword\ (darksword contains the protected Scheduled\
subfolder; any ancestor mount request will be refused).
Default role is ARCHITECT unless told otherwise.
Never push to git without confirmation.
Never modify .env files.
Current build: 8c399cb on main.
## Environment seams (recurring gotchas — check before assuming "it just works")

- **npm global install ≠ install-time setup ran.** `npm install -g <pkg>`
  reporting success only means the package files landed on disk. If the
  package has a `postinstall` script (common for CLIs shipping a native
  binary/shim), npm's `allow-scripts` gate can silently defer it — you'll
  see a `npm warn allow-scripts` line, easy to miss when scanning for the
  actual error. Result: CLI *looks* updated (new files present) but still
  runs old code until the script is explicitly approved.
  - Global installs CANNOT use `npm approve-scripts <pkg>` — that command
    only works inside a project with a package.json and hard-fails
    (EGLOBAL/ENOMATCH) against `-g`. npm's own warning message suggests a
    fix that doesn't work for this case — known npm bug, not user error.
  - Correct fix, scoped not blanket:
    `npm install -g --allow-scripts=<pkg> <pkg>`
  - Traced 2026-07-03: Claude Code CLI login hit a redirect-URI bug
    (`cocallback`) on a stale build; `npm install -g` alone didn't fix it
    because the postinstall got gated. Re-running with `--allow-scripts`
    scoped to the package fixed it clean.

