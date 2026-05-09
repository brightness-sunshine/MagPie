# Magpie Storage Layout

Magpie stores bookmark content as product data, not assistant memory.

## Current approach

Prototype with JSON/JSONL first. Move to SQLite once the flows feel right.

## Layout

- `data/raw/x/` — raw API snapshots from X bookmark sync
- `data/normalized/x/` — normalized bookmark records and latest snapshots
- `data/cache/screenshots/` — cached visual previews of bookmarks
- `data/index/` — search indexes and future retrieval artifacts
- `data/exports/` — exports for downstream use like Obsidian or markdown bundles
- `data/config.json` — storage strategy and paths

## What belongs in memory vs data

### Memory
Use memory only for:
- Magpie behavior rules
- user preferences
- naming and tone choices
- product decisions
- whether sync is enabled

### Data store
Use Magpie data store for:
- bookmark content
- URLs
- authors
- timestamps
- normalized records
- dedupe state
- screenshot cache
- topic labels
- digest artifacts
- search/index state

## Long-term migration

When Magpie needs faster retrieval, filters, tags, multi-source sync, and richer cache metadata, move from JSONL to SQLite.
