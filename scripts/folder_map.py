import json
from pathlib import Path
from collections import defaultdict

NORMALIZED = Path(__file__).resolve().parents[1] / 'data' / 'normalized' / 'x'
LATEST = NORMALIZED / 'bookmarks.latest.json'
SAMPLE = NORMALIZED / 'bookmarks.latest.sample.json'


def source_path():
    """A fresh clone has no fetched file — read the tracked sample instead, so
    every script here runs before any X credentials exist."""
    return LATEST if LATEST.exists() else SAMPLE


def load_items():
    data = json.loads(source_path().read_text())
    return data.get('items', []), data.get('user', {})


def clean(text):
    return ' '.join((text or '').replace('\n', ' ').split()).strip().lower()


def classify_topic(text):
    t = clean(text)
    rules = [
        ('AI', ['gpt', 'llm', 'ai', 'agent', 'agents', 'automation', 'model', 'brand kit']),
        ('XR', ['vision pro', 'visionos', 'meta quest', 'quest', 'smart glasses', 'android xr', 'spatial', 'mixed reality', 'augmented reality', 'virtual reality']),
        ('🛸 UFO', ['ufo', 'uap', 'jellyfish', 'whistleblower', 'disclosure', 'abductions', 'grusch']),
        ('Science', ['biology', 'science', 'protein', 'genome', 'flagellum', 'genetics', 'cell']),
        ('Business', ['startup', 'founder', 'revenue', 'market', 'launch', 'pricing', 'sales']),
        ('Robotics', ['robot', 'robotics', 'wearable', 'sensor', 'camera', 'lidar', 'hardware']),
    ]
    for label, needles in rules:
        if any(n in t for n in needles):
            return label
    return 'Other'


def classify_intent(text):
    t = clean(text)
    if any(n in t for n in ['watch', 'video', 'filmed', 'clip', 'demo']):
        return 'Watch later'
    if any(n in t for n in ['launch', 'try', 'tool', 'app', 'build', 'free']):
        return 'Try'
    if any(n in t for n in ['research', 'study', 'science', 'genome', 'biology', 'report']):
        return 'Research'
    return None


def main():
    items, user = load_items()
    topics = defaultdict(list)
    intents = defaultdict(list)
    authors = defaultdict(int)

    for item in items:
        text = item.get('text') or ''
        topics[classify_topic(text)].append(item)
        intent = classify_intent(text)
        if intent:
            intents[intent].append(item)
        handle = item.get('authorHandle')
        if handle:
            authors[handle] += 1

    top_topics = sorted(topics.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:6]
    top_authors = sorted(authors.items(), key=lambda kv: (-kv[1], kv[0]))[:3]

    lines = []
    lines.append(f"**Magpie mapped your bookmarks for @{user.get('username', 'unknown')}**")
    lines.append('')
    for name, vals in top_topics:
        lines.append(f"- {name} ({len(vals)})")
    lines.append('')
    lines.append('**Suggested folders**')
    lines.append('')
    for name, vals in top_topics:
        lines.append(f"- {name}")
    for name, vals in sorted(intents.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:3]:
        lines.append(f"- {name}")
    if top_authors:
        lines.append('- People')
    lines.append('')
    lines.append('Tap a folder:')

    buttons = []
    topic_row = []
    for name, vals in top_topics[:3]:
        topic_row.append({'text': f'{name} ({len(vals)})', 'callback_data': f'magpie:topic:{name}'})
    if topic_row:
        buttons.append(topic_row)
    topic_row2 = []
    for name, vals in top_topics[3:6]:
        topic_row2.append({'text': f'{name} ({len(vals)})', 'callback_data': f'magpie:topic:{name}'})
    if topic_row2:
        buttons.append(topic_row2)
    intent_row = []
    for name, vals in sorted(intents.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:3]:
        intent_row.append({'text': name, 'callback_data': f'magpie:intent:{name}'})
    if intent_row:
        buttons.append(intent_row)
    if top_authors:
        buttons.append([
            {'text': 'People', 'callback_data': 'magpie:people'},
            {'text': 'Digest all', 'callback_data': 'magpie:digest'}
        ])

    print(json.dumps({
        'text': '\n'.join(lines),
        'buttons': buttons,
        'topics': {name: len(vals) for name, vals in top_topics},
        'intents': {name: len(vals) for name, vals in intents.items()},
        'top_authors': top_authors,
    }, indent=2))


if __name__ == '__main__':
    main()
