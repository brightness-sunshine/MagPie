import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict

LATEST = Path(__file__).resolve().parents[1] / 'data' / 'normalized' / 'x' / 'bookmarks.latest.json'


def load_items():
    data = json.loads(LATEST.read_text())
    return data.get('items', []), data.get('user', {})


def preview(text, n=140):
    text = (text or '').replace('\n', ' ').strip()
    return text if len(text) <= n else text[: n - 1] + '…'


def cmd_search(items, query):
    q = query.lower()
    matches = []
    for item in items:
        hay = ' '.join([
            item.get('text') or '',
            item.get('authorHandle') or '',
            item.get('authorName') or '',
            item.get('url') or '',
        ]).lower()
        if q in hay:
            matches.append(item)
    return matches


def infer_groups(items):
    buckets = defaultdict(list)
    rules = {
        'xr_spatial': ['xr', 'vision pro', 'visionos', 'meta', 'quest', 'ar ', ' vr', 'spatial', 'smart glasses', 'android xr'],
        'ai_tools': ['ai', 'gpt', 'agent', 'agents', 'model', 'llm', 'brand kit', 'automation', 'robot'],
        'biology_science': ['biology', 'science', 'flagellum', 'protein', 'cell', 'genome', 'research'],
        'founder_business': ['founder', 'startup', 'pricing', 'revenue', 'sales', 'market', 'launching'],
    }
    for item in items:
        hay = (item.get('text') or '').lower()
        placed = False
        for bucket, needles in rules.items():
            if any(n in hay for n in needles):
                buckets[bucket].append(item)
                placed = True
        if not placed:
            buckets['uncategorized'].append(item)
    return buckets


def top_authors(items, limit=10):
    counts = Counter()
    for item in items:
        handle = item.get('authorHandle') or '(unknown)'
        counts[handle] += 1
    return counts.most_common(limit)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('search')
    s.add_argument('query')
    s.add_argument('--limit', type=int, default=10)

    sub.add_parser('groups')
    sub.add_parser('authors')
    sub.add_parser('latest')

    args = parser.parse_args()
    items, user = load_items()

    if args.cmd == 'search':
        matches = cmd_search(items, args.query)[: args.limit]
        print(json.dumps({
            'user': user,
            'query': args.query,
            'count': len(matches),
            'items': [
                {
                    'author': i.get('authorHandle'),
                    'url': i.get('url'),
                    'text': preview(i.get('text')),
                }
                for i in matches
            ]
        }, indent=2))
    elif args.cmd == 'groups':
        groups = infer_groups(items)
        print(json.dumps({
            'user': user,
            'groups': {k: len(v) for k, v in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))}
        }, indent=2))
    elif args.cmd == 'authors':
        print(json.dumps({
            'user': user,
            'top_authors': top_authors(items)
        }, indent=2))
    elif args.cmd == 'latest':
        print(json.dumps({
            'user': user,
            'count': len(items),
            'items': [
                {
                    'author': i.get('authorHandle'),
                    'url': i.get('url'),
                    'text': preview(i.get('text')),
                }
                for i in items[:10]
            ]
        }, indent=2))


if __name__ == '__main__':
    main()
