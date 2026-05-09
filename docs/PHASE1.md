# PHASE1.md - Magpie Phase 1

## Goal

Build the first usable version of **Magpie** as a bookmark-ingest and retrieval system focused on **X bookmarks only**.

Phase 1 is not about podcasts, Spotify, or Obsidian sync yet.
Phase 1 is about proving one thing well:

> Can Magpie reliably pull a user's saved X bookmarks into one searchable, structured store?

## Product Intent

Magpie should help turn scattered saved links into a durable personal knowledge stream.

For v1, success means:
- a user can connect X
- Magpie can ingest bookmarks from that account
- bookmarks are normalized and stored cleanly
- duplicates are handled
- saved items can be searched and grouped later

## Scope

### In scope
- X bookmarks ingest
- credentials/auth setup for one user
- raw + normalized bookmark storage
- dedupe strategy
- lightweight local retrieval/search
- connector abstraction so API and browser approaches can share the same store

### Out of scope
- podcast generation
- Telegram audio delivery
- Spotify publishing
- Obsidian export
- multi-platform sync
- polished end-user UI
- generalized production auth flow

## Core Technical Question

Before building the permanent version, verify whether **X bookmarks are accessible through the official API** under the new pricing model.

Two things must be tested:
1. Does a bookmarks endpoint actually exist and work for a user account?
2. Is that endpoint billed cheaply enough to make regular sync practical?

## Recommended Strategy

## Strategy A: API-first
Use the official X API if bookmarks are supported.

Why this is preferred:
- cleaner setup
- reusable as a skill for other users
- more stable than browser automation
- easier to run on cron
- lower maintenance cost long-term

### API-first prototype checklist
- verify credential format needed
- authenticate successfully
- locate bookmark-capable endpoint
- fetch a first page of bookmarks
- inspect pagination behavior
- inspect returned metadata
- estimate read cost under the new model
- confirm what can be stored and searched

## Strategy B: Browser fallback
If bookmarks are not exposed through the API, use browser-assisted sync.

Why this exists:
- allows Phase 1 to ship even if X API access is incomplete
- lets Magpie prove user value without blocking on X platform decisions

### Browser-fallback prototype checklist
- access logged-in X bookmarks page via browser integration
- extract bookmark rows/posts
- capture URLs, authors, timestamps, text, media hints
- paginate/scroll until complete enough for v1
- normalize into the same storage shape as API ingest

## Architecture

Magpie should separate **connector**, **normalizer**, and **store**.

### 1. Connector layer
Each ingest path should feed the same internal schema.

Possible connectors:
- `x_api`
- `x_browser`
- later: `linkedin`, `reddit`, `manual_import`

### 2. Normalizer layer
Every bookmark should be converted into a canonical object.

Suggested normalized record:

```json
{
  "id": "internal-stable-id",
  "platform": "x",
  "platformRecordId": "source-id-if-known",
  "savedAt": "ISO timestamp when bookmarked if available",
  "ingestedAt": "ISO timestamp",
  "url": "canonical URL",
  "authorHandle": "string or null",
  "authorName": "string or null",
  "title": "optional derived title",
  "text": "post text or extracted summary",
  "media": [],
  "tags": [],
  "sourceType": "api|browser",
  "rawRef": "pointer to raw payload"
}
```

### 3. Raw store
Preserve raw API/browser payloads for debugging and future enrichment.

Suggested structure:
- `data/raw/x/<timestamp>-<page>.json`
- `data/normalized/x/bookmarks.jsonl`
- or SQLite if it becomes easier quickly

### 4. Retrieval layer
Phase 1 only needs simple retrieval.

Required queries:
- latest bookmarks
- search by keyword
- filter by author
- filter by ingest date

## Dedupe Strategy

Bookmarks will eventually sync repeatedly, so dedupe must exist from day one.

Suggested dedupe priority:
1. platform record ID if reliable
2. canonical post URL
3. normalized content hash

## Secrets and Credentials

Do not store credentials in workspace files.

Use Klaus/OpenClaw secrets only.

Likely env vars for prototype testing:
- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`
- `X_BEARER_TOKEN` if needed

## Prototype Flow

### Step 1
Confirm official X bookmark access feasibility.

### Step 2
If feasible, build a tiny API test script that:
- authenticates
- fetches bookmarks
- saves raw response
- prints cost/volume assumptions if possible

### Step 3
Normalize one small batch into a local data file.

### Step 4
Test retrieval over that normalized set.

### Step 5
If API fails, switch to browser-assisted connector without changing the storage model.

## Success Criteria for Phase 1 Prototype

Magpie Phase 1 is successful if:
- one real X account can be connected
- at least one batch of bookmarks can be ingested
- normalized records are stored locally
- duplicates do not accumulate across repeated syncs
- the user can search or inspect saved items afterward
- the architecture clearly supports API-first and browser-fallback paths

## What Comes After Phase 1

Only after X ingest is real and stable should Magpie expand into:
- smart clustering
- topic grouping
- Obsidian export
- short spoken digests
- Telegram audio delivery
- Spotify distribution

## Immediate Next Step

Use the user's X API credentials to test whether bookmark access is truly available under the current X pricing model.

If yes: continue API-first.
If no: pivot immediately to browser-assisted ingest while preserving the same normalized store.
