---
name: magpie
description: "Import, search, group, and export saved links/bookmarks with a local-first Magpie datastore. Use for X bookmark ingest, bookmark memory, folder-first onboarding, topic clustering, and markdown/shared-shelf exports."
---

# Magpie

Magpie is a local-first bookmark memory skill for OpenClaw.

It turns saved links — starting with X bookmarks — into a searchable local library with folder-first onboarding, smart theme clusters, and exportable research trails.

## Principles

- Keep bookmark content in Magpie's local datastore, not assistant memory.
- Prefer existing folders / user-legible shelves first.
- Treat smart clustering as additive, not destructive.
- Preserve raw payloads for debugging, but never publish user data.
- Use environment variables for credentials; never hardcode secrets.

## Quick start

From this skill directory:

```bash
python3 scripts/magpie.py init-db
python3 scripts/magpie.py import-jsonl --path data/normalized/x/bookmarks.sample.jsonl
python3 scripts/magpie.py stats
python3 scripts/magpie.py search "UFO" --limit 5
python3 scripts/magpie.py groups --examples 2
python3 scripts/magpie.py export-markdown --limit 10
```

## X bookmark ingest

Set credentials as environment variables or OpenClaw/Klaus secrets:

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_OAUTH2_ACCESS_TOKEN`
- `X_OAUTH2_REFRESH_TOKEN`

Then run:

```bash
python3 scripts/fetch_x_bookmarks.py --pages 1 --page-size 100
python3 scripts/magpie.py import-jsonl
```

If the official X API is unavailable or too expensive, keep the same normalized schema and swap in a browser-assisted connector later.

## User-facing workflows

- `stats` — see total imported bookmarks and top authors
- `search "query"` — full-text search
- `groups` — lightweight topic grouping
- `export-markdown` — export latest items into markdown
- `scripts/staged_onboarding.py folder-setup` — folder-first onboarding payload
- `scripts/telegram_runtime.py onboard --stage folders` — Telegram-style payloads

## Current v1 scope

Included:

- X bookmark ingest prototype
- SQLite-backed local store
- JSONL compatibility import
- dedupe/upsert strategy
- full-text search
- simple smart groups
- folder-first onboarding payloads
- markdown export
- Telegram-style JSON payloads

Not included yet:

- polished installer
- public hosted service
- multi-user auth
- persistent user-edited folders
- browser bookmark import
- local web UI
- multi-source sync

See `docs/` for launch direction, phase 1 scope, storage layout, onboarding, and Telegram UX notes.
