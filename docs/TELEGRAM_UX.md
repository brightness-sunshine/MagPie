# TELEGRAM_UX.md - Magpie Telegram Experience

## Product Direction

Magpie should treat **Telegram as the primary user interface** for Phase 1 and early Phase 2.

Do not build a separate visual UI first.
The fastest path to useful is:
- conversational search
- predictable command shortcuts
- compact result formatting
- follow-up buttons for common actions

The user should be able to retrieve saved material naturally while on the go.

## Design Principles

- Mobile-first
- Fast to use with one hand
- Readable in short bursts
- Works well in a Telegram DM
- Avoid overwhelming the user with long dumps
- Prefer 3 to 8 strong results over huge lists
- Make follow-up easy

## Core User Jobs

A user should be able to:
- find something they saved but half-forgot
- browse bookmarks by topic
- browse bookmarks by person/source
- get a short digest of recent saves
- turn a cluster into something readable or listenable later

## Interaction Modes

### 1. Natural language search
This should be the default and most important mode.

Examples:
- find my bookmarks about vision pro
- what have I saved on smart glasses
- show my posts about AI agents
- find that bookmark about brand kits
- what did I save from garrytan
- show the latest robotics bookmarks

Expected behavior:
- infer search intent
- search across text, author, URL, and topic hints
- return the strongest matches first
- keep the reply compact

### 2. Explicit commands
Useful for predictability and power users.

Suggested commands:
- `/bookmarks latest`
- `/bookmarks search <query>`
- `/bookmarks topic <topic>`
- `/bookmarks author <handle>`
- `/bookmarks digest`
- `/bookmarks themes`
- `/bookmarks random`

Commands should map to the same underlying retrieval engine as natural language.

### 3. Follow-up buttons
Buttons should reduce typing after results appear.

Suggested buttons:
- More
- Summarize
- Group by topic
- Similar
- Latest
- Audio digest

Telegram buttons can make Magpie feel like an app without building a new app.

## Response Format

Keep the structure extremely readable.

### Search result response
Example:

**Found 5 bookmarks about smart glasses**

1. **@descrailabs**
AI-powered smart glasses for the lab. Record experiments hands-free...
<https://x.com/...>

2. **@venturetwins**
Brand kits and swag generation with GPT-Image-2...
<https://x.com/...>

Buttons:
- More
- Group
- Summarize

### Author response
Example:

**Bookmarks from @garrytan**
- Post 1 snippet
- Post 2 snippet
- Post 3 snippet

### Digest response
Example:

**Your recent bookmark themes**
- AI tools & agents (39)
- XR & spatial (7)
- Founder & business (8)

Top thread right now:
- AI tooling for brand, automation, and robotics

Buttons:
- Read digest
- Audio digest
- Show links

## Retrieval Behaviors

Magpie should support these retrieval dimensions:
- keyword search
- author handle search
- recent vs older bookmarks
- topic/category grouping
- link/domain lookup
- semantic-ish matching later

For v1, keyword + author + group is enough.

## Result Quality Rules

- prioritize relevance over exhaustiveness
- limit default replies to 3 to 8 results
- show short excerpts, not full post text
- always include the original link
- avoid returning near-duplicates in the same response
- when confidence is low, say so briefly

## Good Early Features

### Must have
- latest bookmarks
- query search
- author filter
- digest summary
- grouped themes

### Nice next step
- “more like this”
- “saved this week”
- “top people I bookmark”
- “surprise me”
- audio digest from current result set

## Recommended Telegram V1

### User messages Magpie naturally
Examples:
- what did I save about robotics
- show me my latest bookmarks
- find bookmarked posts from scoble
- summarize what I’ve been saving lately

### Magpie replies with:
- a short title
- 3 to 5 results or a short digest
- clean snippets
- direct links
- follow-up buttons

This is enough to make the system feel useful from a phone immediately.

## What Not To Build Yet

Do not build yet:
- a large standalone web app
- complex folder trees
- manual drag-and-drop organization
- a heavy dashboard
- too many commands before natural language works well

These can come later once retrieval quality is excellent.

## Product Recommendation

Magpie should become:
- **Telegram-first for retrieval**
- **Obsidian-friendly for storage/export later**
- **audio-capable for digest consumption later**

That means the order should be:
1. sync bookmarks reliably
2. retrieve them well in Telegram
3. make digests feel smart
4. add audio
5. add multi-source sync

## Immediate Build Implications

The next engineering steps should be:
1. improve grouping/classification quality
2. create a Telegram-friendly formatter for result cards
3. support search by query/author/topic
4. wire follow-up actions into compact button flows

This is the fastest path to a product that already feels real.
