import json
from pathlib import Path
from collections import defaultdict

LATEST = Path(__file__).resolve().parents[1] / 'data' / 'normalized' / 'x' / 'bookmarks.latest.json'
OUT = Path(__file__).resolve().parents[1] / 'data' / 'normalized' / 'x' / 'digest.latest.md'


def load_items():
    data = json.loads(LATEST.read_text())
    return data.get('items', []), data.get('user', {})


def clean(text):
    return ' '.join((text or '').replace('\n', ' ').split()).strip()


def classify(text):
    t = clean(text).lower()
    rules = [
        ('XR & spatial', ['vision pro', 'visionos', 'meta quest', 'quest', 'smart glasses', 'android xr', 'spatial', 'augmented reality', 'virtual reality', 'xr']),
        ('AI tools & agents', ['gpt', 'ai', 'agent', 'agents', 'model', 'llm', 'automation', 'brand kit']),
        ('Science & biology', ['biology', 'science', 'protein', 'genome', 'flagellum', 'psychiatric genetics', 'cell']),
        ('Founder & business', ['startup', 'founder', 'revenue', 'market', 'launch', 'pricing', 'sales']),
        ('Robotics & hardware', ['robot', 'robotics', 'wearable', 'sensor', 'camera', 'lidar', 'hardware']),
    ]
    for label, needles in rules:
        if any(n in t for n in needles):
            return label
    return 'Other'


def short(text, n=220):
    text = clean(text)
    return text if len(text) <= n else text[: n - 1] + '…'


def main():
    items, user = load_items()
    grouped = defaultdict(list)
    for item in items:
        grouped[classify(item.get('text') or '')].append(item)

    lines = []
    lines.append(f"# Magpie Digest for @{user.get('username', 'unknown')}")
    lines.append('')
    lines.append(f"Bookmarks analyzed: **{len(items)}**")
    lines.append('')
    lines.append('## What Magpie sees')
    lines.append('')

    ordered = sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    for group, group_items in ordered:
        lines.append(f"### {group} ({len(group_items)})")
        lines.append('')
        for item in group_items[:5]:
            author = item.get('authorHandle') or 'unknown'
            url = item.get('url') or ''
            lines.append(f"- **@{author}** — {short(item.get('text') or '')}")
            lines.append(f"  - {url}")
        if len(group_items) > 5:
            lines.append(f"- _...and {len(group_items) - 5} more in this category._")
        lines.append('')

    lines.append('## Quick read')
    lines.append('')
    largest = ordered[:3]
    if largest:
        summary_bits = [f"{name} ({len(vals)})" for name, vals in largest]
        lines.append('Your bookmark stream currently leans most toward ' + ', '.join(summary_bits) + '.')
        lines.append('')
        lines.append('That suggests Magpie should prioritize topic grouping, better summarization, and eventually audio briefings built around these clusters.')

    OUT.write_text('\n'.join(lines) + '\n')
    print(json.dumps({
        'user': user,
        'count': len(items),
        'output': str(OUT),
        'groups': {k: len(v) for k, v in ordered}
    }, indent=2))


if __name__ == '__main__':
    main()
