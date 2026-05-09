import json
import argparse
from pathlib import Path
from collections import defaultdict

LATEST = Path(__file__).resolve().parents[1] / 'data' / 'normalized' / 'x' / 'bookmarks.latest.json'


def load_items():
    data = json.loads(LATEST.read_text())
    return data.get('items', []), data.get('user', {})


def clean(text):
    return ' '.join((text or '').replace('\n', ' ').split()).strip()


def short(text, n=160):
    text = clean(text)
    return text if len(text) <= n else text[: n - 1] + '…'


def classify(text):
    t = clean(text).lower()
    rules = [
        ('XR & spatial', ['vision pro', 'visionos', 'meta quest', 'quest', 'smart glasses', 'android xr', 'spatial', 'augmented reality', 'virtual reality', 'mixed reality']),
        ('AI tools & agents', ['gpt', 'llm', 'ai', 'agent', 'agents', 'automation', 'model', 'brand kit']),
        ('Science & biology', ['biology', 'science', 'protein', 'genome', 'flagellum', 'psychiatric genetics', 'cell']),
        ('Founder & business', ['startup', 'founder', 'revenue', 'market', 'launch', 'pricing', 'sales']),
        ('Robotics & hardware', ['robot', 'robotics', 'wearable', 'sensor', 'camera', 'lidar', 'hardware']),
        ('Weird internet', ['ufo', 'uap', 'jellyfish', 'virgin mary', 'pope', 'mystery']),
    ]
    for label, needles in rules:
        if any(n in t for n in needles):
            return label
    return 'Other'


def search_items(items, query):
    q = query.lower()
    scored = []
    for item in items:
        hay_text = (item.get('text') or '').lower()
        hay_author = (item.get('authorHandle') or '').lower()
        hay_name = (item.get('authorName') or '').lower()
        score = 0
        if q in hay_author or q in hay_name:
            score += 4
        if q in hay_text:
            score += 3
        if q in (item.get('url') or '').lower():
            score += 2
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1].get('createdAt') or ''))
    return [item for _, item in scored]


def filter_topic(items, topic):
    return [i for i in items if classify(i.get('text') or '') == topic]


def format_results(title, items, limit=5):
    lines = [f'**{title}**', '']
    if not items:
        lines.append('No matches yet.')
        return '\n'.join(lines)
    for idx, item in enumerate(items[:limit], start=1):
        author = item.get('authorHandle') or 'unknown'
        lines.append(f'{idx}. **@{author}**')
        lines.append(short(item.get('text') or ''))
        lines.append(f'<{item.get("url") or ""}>')
        lines.append('')
    remaining = len(items) - limit
    if remaining > 0:
        lines.append(f'_And {remaining} more._')
    return '\n'.join(lines).strip()


def format_digest(items):
    groups = defaultdict(list)
    for item in items:
        groups[classify(item.get('text') or '')].append(item)
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    lines = ['**Your bookmark themes**', '']
    for name, vals in ordered[:5]:
        lines.append(f'- {name}: {len(vals)}')
    lines.append('')
    if ordered:
        top_name, top_vals = ordered[0]
        lines.append(f'Right now your strongest cluster is **{top_name}**.')
        lines.append('')
        lines.append('Try:')
        lines.append(f'- `show my {top_name.lower()} bookmarks`')
        lines.append('- `summarize my latest bookmarks`')
        lines.append('- `find bookmarks from <author>`')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('latest')
    p1.add_argument('--limit', type=int, default=5)

    p2 = sub.add_parser('search')
    p2.add_argument('query')
    p2.add_argument('--limit', type=int, default=5)

    p3 = sub.add_parser('author')
    p3.add_argument('handle')
    p3.add_argument('--limit', type=int, default=5)

    p4 = sub.add_parser('topic')
    p4.add_argument('topic')
    p4.add_argument('--limit', type=int, default=5)

    sub.add_parser('digest')

    args = parser.parse_args()
    items, user = load_items()

    if args.cmd == 'latest':
        print(format_results(f'Latest bookmarks for @{user.get("username", "unknown")}', items, args.limit))
    elif args.cmd == 'search':
        results = search_items(items, args.query)
        print(format_results(f'Found {len(results)} bookmarks for "{args.query}"', results, args.limit))
    elif args.cmd == 'author':
        q = args.handle.lower().lstrip('@')
        results = [i for i in items if (i.get('authorHandle') or '').lower() == q]
        print(format_results(f'Bookmarks from @{q}', results, args.limit))
    elif args.cmd == 'topic':
        topic_map = {
            'xr': 'XR & spatial',
            'ai': 'AI tools & agents',
            'science': 'Science & biology',
            'business': 'Founder & business',
            'robotics': 'Robotics & hardware',
            'weird': 'Weird internet',
            'other': 'Other',
        }
        chosen = topic_map.get(args.topic.lower(), args.topic)
        results = filter_topic(items, chosen)
        print(format_results(f'{chosen} bookmarks', results, args.limit))
    elif args.cmd == 'digest':
        print(format_digest(items))


if __name__ == '__main__':
    main()
