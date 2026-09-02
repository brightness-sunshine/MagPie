# Magpie OpenClaw Skill

Magpie is a local-first bookmark memory layer for OpenClaw.

Bring saved links in, keep them local, and make them searchable, explainable, and reusable.

## What it does today

- Imports X bookmarks into normalized local records
- Stores bookmarks in SQLite with JSONL compatibility
- Searches saved links
- Groups bookmarks into lightweight themes
- Provides folder-first onboarding payloads
- Exports selected bookmarks to markdown
- Produces Telegram-style JSON payloads for interactive flows

## Install / try locally

The quickstart is stdlib-only — no pip install, no credentials, no account.
It runs against the bundled sample bookmarks:

```bash
git clone https://github.com/brightness-sunshine/MagPie.git
cd MagPie
python3 scripts/magpie.py init-db
python3 scripts/magpie.py import-jsonl --path data/normalized/x/bookmarks.sample.jsonl
python3 scripts/magpie.py stats
python3 scripts/magpie.py search "UFO" --limit 5
python3 scripts/staged_onboarding.py folder-setup
```

To fetch your own bookmarks you need your own X app (`X_CLIENT_ID` / `X_CLIENT_SECRET`,
scope `bookmark.read`) and `pip install -r requirements.txt`:

```bash
MAGPIE_ENV_PATH=./magpie-x.env python3 scripts/fetch_x_bookmarks.py --pages 2 --page-size 100
```

Your fetched bookmarks stay in `data/` and are gitignored. Only the `*.sample.*` files are tracked.

## Data safety

This repo includes only sample bookmark data. Real user data should stay local under `data/` and should not be committed.

`.gitignore` excludes runtime SQLite databases, raw snapshots, caches, indexes, exports, and env files.

## OpenClaw skill usage

Copy this folder into an OpenClaw skills directory or install it as a skill once packaged through ClawHub/OpenClaw skill distribution.

The skill file is `SKILL.md`; scripts live in `scripts/`.

## Roadmap

1. Harden X API ingest and cost assumptions
2. Add browser-assisted fallback connector
3. Persist user-edited folder assignments
4. Add richer exports / shared shelf generation
5. Add a small local web UI after the ingest/search loop is stable
