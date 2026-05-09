# Magpie Onboarding — Folder-First v1

## Product stance

Magpie should feel like a tidy shelf, not an AI takeover.

The first-run experience should start with folders because folders are legible, familiar, and easy to trust. Smart clustering is additive: it can suggest themes and shortcuts, but it should never replace or silently rewrite a user's chosen structure.

## First-run flow

### 1. Welcome

**Message**

> Welcome to Magpie. Bring your saved links into one local, searchable library.
>
> Start with folders you can understand. Magpie can add smart themes on top when you want them.

**Actions**

- `Set up folders` — primary
- `Let Magpie suggest themes` — secondary
- `Search immediately` — utility escape hatch

### 2. Folder setup

Show starter folders based on the current import.

For the included sample bookmark set, starter folders look like:

- AI
- UFO
- Business
- Science
- Robotics
- XR
- Try
- Research
- Watch later
- People
- Other

Each folder should show an item count and 1–2 preview examples before the user commits.

**Actions**

- `Use these folders`
- `Rename / merge folders`
- `Let Magpie organize instead`

### 3. Folder home

After confirmation, land on a folder home screen:

- folder list with counts
- latest imported count
- search box / search action
- secondary toggle: `Smart themes`

### 4. Folder detail

Opening a folder shows:

- top 5–10 items
- why each item belongs there when useful
- actions: `Search inside`, `Export folder`, `Back to folders`

### 5. Smart layer

Smart themes should be framed as a layer:

> Magpie noticed a few trails across your folders.

Examples:

- UFO disclosure trail
- AI tools to try
- Founder/operator advice
- XR hardware watchlist

Smart themes can cross folder boundaries but should not mutate folder membership unless the user confirms.

## Data model notes

Folder assignment should be product data in Magpie's store, not assistant memory.

Recommended next schema addition:

```sql
CREATE TABLE folders (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source TEXT NOT NULL, -- user|suggested|imported|smart
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE bookmark_folders (
  bookmark_id TEXT NOT NULL,
  folder_id TEXT NOT NULL,
  confidence REAL,
  reason TEXT,
  source TEXT NOT NULL, -- user|rule|cluster|import
  created_at TEXT NOT NULL,
  PRIMARY KEY (bookmark_id, folder_id)
);
```

For v1, folder suggestions can still be generated dynamically from rules. Persist them once the user clicks `Use these folders`.

## UX rules

- Email/RSS/shared-shelf exports are downstream outputs, not onboarding.
- Do not ask the user to tag 99 items manually.
- Always provide an escape hatch to search.
- Use counts and examples; avoid abstract labels with no preview.
- Keep folder names editable later.
