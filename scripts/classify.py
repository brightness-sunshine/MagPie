#!/usr/bin/env python3
"""Theme grouping for bookmarks.

Keyword rules settle most rows for free. Whatever they cannot place is
optionally sent to a model in one batched call, and only when ANTHROPIC_API_KEY
is set — without a key the pipeline still runs and leaves the remainder in
'uncategorized'.

Needles match on word boundaries. Plain substring matching is why 'ai' fired
inside brain/said/Azerbaijan and 'ar ' fired inside 'car ' and 'similar '.

These rules are a fallback for bookmarks captured without a user-supplied
caption. When the capture surface asks the user what a save is for, that answer
outranks anything inferred here.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

UNCATEGORIZED = 'uncategorized'

# Order matters: the first group whose needle matches wins.
GROUP_RULES = {
    'xr_spatial': ['xr', 'vision pro', 'visionos', 'meta', 'quest', 'ar', 'vr', 'spatial', 'smart glasses',
                   'android xr', 'headset', 'immersive', 'hologram', 'oculus', 'passthrough', 'metaverse'],
    'ai_tools': ['ai', 'gpt', 'agent', 'model', 'llm', 'automation', 'robot', 'claude', 'openai',
                 'neural', 'inference', 'transformer', 'dataset'],
    'biology_science': ['biology', 'science', 'flagellum', 'protein', 'cell', 'genome', 'research',
                        'brain', 'consciousness', 'physics', 'quantum', 'neuron', 'math'],
    'founder_business': ['founder', 'startup', 'pricing', 'revenue', 'sales', 'market', 'launch'],
    'uap_unknowns': ['uap', 'ufo', 'grusch', 'non-human', 'biologics', 'craft', 'disclosure',
                     'alien', 'orb', 'nhi', 'whistleblower', 'anomalous'],
}

GROUPS = list(GROUP_RULES)

# Two-letter tokens collide with ordinary English ('ai' in brain, 'ar' in car),
# so they only ever match standalone. Everything else may carry an inflection:
# 'robot' catches 'robotics', 'ufo' catches 'ufos'.
_EXACT_ONLY = {'ai', 'xr', 'vr', 'ar'}
_SUFFIX = r'(?:s|es|ing|ics)?'


@lru_cache(maxsize=None)
def _pattern(needle: str) -> re.Pattern[str]:
    if ' ' in needle or '-' in needle:
        return re.compile(re.escape(needle))
    if needle in _EXACT_ONLY:
        return re.compile(rf'\b{re.escape(needle)}\b')
    return re.compile(rf'\b{re.escape(needle)}{_SUFFIX}\b')


def haystack(row: dict) -> str:
    parts = [row.get('title'), row.get('text'), row.get('url'), row.get('author_handle')]
    return ' '.join(p for p in parts if p).lower()


def rule_group(row: dict) -> str:
    hay = haystack(row)
    for group, needles in GROUP_RULES.items():
        if any(_pattern(n).search(hay) for n in needles):
            return group
    return UNCATEGORIZED


def _client():
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic(api_key=key)


PROMPT = """Assign each bookmark to exactly one shelf.

Shelves: {groups}, or uncategorized if none genuinely fit.

Return only a JSON object mapping each id to a shelf name. No prose.

Bookmarks:
{items}"""


def llm_groups(rows: list[dict], batch_size: int = 40) -> dict[str, str]:
    """Classify rows a batch at a time. Returns {} when no key is configured."""
    client = _client()
    if client is None or not rows:
        return {}

    assigned: dict[str, str] = {}
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        items = '\n'.join(
            f'{r["id"]}: {(r.get("text") or r.get("title") or "")[:300]}'.replace('\n', ' ')
            for r in batch
        )
        message = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=2000,
            messages=[{
                'role': 'user',
                'content': PROMPT.format(groups=', '.join(GROUPS), items=items),
            }],
        )
        text = message.content[0].text.strip()
        match = re.search(r'\{.*\}', text, re.S)
        if not match:
            continue
        for bid, group in json.loads(match.group(0)).items():
            if group in GROUPS:
                assigned[bid] = group
    return assigned


def classify(rows: list[dict], use_llm: bool = True) -> dict[str, str]:
    """Map bookmark id -> shelf. Rules first, model for the remainder."""
    groups = {r['id']: rule_group(r) for r in rows}
    if not use_llm:
        return groups
    leftover = [r for r in rows if groups[r['id']] == UNCATEGORIZED]
    for bid, group in llm_groups(leftover).items():
        groups[bid] = group
    return groups
