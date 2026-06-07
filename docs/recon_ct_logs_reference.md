# RECON Reference — Certificate Transparency Logs

> **Note for SCRIBE/AUDITOR:** This content was drafted as a section to append to `.claude/RECON.md` under a new `## Certificate Transparency Logs` heading (immediately before `## Key Files`). It was placed in `docs/` instead because `.claude/RECON.md` sits in a protected/restricted path for this session — paste the section below into RECON.md manually when convenient.

---

## Certificate Transparency Logs

### What they are

Certificate Transparency (CT) is a public, append-only log system (RFC 6962) that records every TLS/SSL certificate issued by a participating Certificate Authority. Browsers (Chrome, Safari) require CAs to log certificates to CT before trusting them, which means CT logs contain a near-complete public record of every certificate ever issued for every domain — including subdomains that were never intended to be discoverable.

### Why they're valuable for passive recon

CT logs are a pure OSINT source: querying them generates no traffic against the target's own infrastructure, leaves no trace, and requires no authentication. For RECON's purposes they answer two questions cheaply:

- **Attack surface mapping** — any subdomain that has ever had a certificate issued shows up in CT logs, including staging environments, internal tools, and forgotten infrastructure that DNS enumeration alone would miss.
- **Early warning for impersonation** — a certificate issued for a lookalike or typosquatted domain (`darksw0rd.io`, `notion-darksword.com`, etc.) appears in CT logs within minutes of issuance, often before the phishing infrastructure behind it goes live.

### Primary tools

| Tool | Purpose | Access |
|------|---------|--------|
| **crt.sh** | Web UI and JSON API over the CT log corpus (run by Sectigo); the standard first stop for manual lookups | `https://crt.sh/?q=<domain>&output=json` — free, no key |
| **Censys** | Indexes CT logs alongside active internet-wide scan data; correlates a certificate with the live host serving it | `https://search.censys.io` — free tier with API key |
| **Cert Spotter** | Purpose-built CT monitoring service; can issue near-real-time alerts when a new certificate is issued for a watched domain | `https://sslmate.com/certspotter/` — free tier (100 domains) |

### Subdomain enumeration one-liner

```bash
curl -s "https://crt.sh/?q=%25.example.com&output=json" \
  | jq -r '.[].name_value' \
  | sed 's/\*\.//g' \
  | sort -u
```

This queries crt.sh for every certificate ever logged for `*.example.com`, extracts the `name_value` field (which may contain multiple SANs per entry, newline-separated), strips wildcard prefixes, and deduplicates. Swap `example.com` for the target domain — the `%25` is a URL-encoded `%` wildcard.

### Defensive monitoring angle for DARKSWORD's own domains

CT logs cut both ways — RECON should use them not just to map third-party attack surface but to monitor DARKSWORD's own footprint:

- Run the crt.sh one-liner periodically against any domains DARKSWORD owns or is associated with (including the GitHub Pages domain if one exists, and any custom domains tied to the Notion workspace or Transistor RSS feed).
- Set up a Cert Spotter watch on DARKSWORD's primary domain(s) — free tier alerting catches unauthorized or unexpected certificate issuance (a sign of a compromised CA account, a misconfigured subdomain takeover, or a phishing domain impersonating the project).
- Cross-reference any unexpected subdomain found in CT logs against the URL inventory in **Current Attack Surface** in `.claude/RECON.md` — an unfamiliar subdomain with a valid certificate is a structural finding (possible forgotten staging environment, shadow IT, or takeover risk) and should be escalated to AUDITOR immediately per the existing "Exposed secret or UUID" handoff path.

### Integration with existing RECON scope

CT log review slots directly into the existing **Recon Checklist** and **Current Attack Surface** sections of `.claude/RECON.md`:

- Add a CT log pass to the **GitHub exposure** checklist: query crt.sh for the project's domain(s) before each pre-release audit, alongside the existing log/`.env` history checks.
- Treat CT findings as an extension of **URL / endpoint health** — any newly discovered subdomain should be health-checked the same way hardcoded pipeline endpoints are.
- File CT-derived findings the same way as any other recon finding: exposed or unexpected infrastructure → AUDITOR immediately; documentation of a new monitoring routine → SCRIBE.
