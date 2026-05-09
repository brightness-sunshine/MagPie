#!/usr/bin/env python3
import json
import argparse
import re
from pathlib import Path
from collections import defaultdict

LATEST = Path(__file__).resolve().parents[1] / 'data' / 'normalized' / 'x' / 'bookmarks.latest.json'


def load_items():
    data = json.loads(LATEST.read_text())
    return data.get('items', []), data.get('user', {})


def clean(text):
    return ' '.join((text or '').replace('\n', ' ').split()).strip()


def short(text, n=150):
    text = clean(text)
    return text if len(text) <= n else text[: n - 1] + '…'


def classify_folder(item):
    text = clean(item.get('text') or '').lower()
    rules = [
        # Put narrow subject clusters before broad AI so UFO/robotics posts that mention AI don't get swallowed.
        ('UFO', ['ufo', 'uap', 'jellyfish', 'whistleblower', 'disclosure', 'abductions', 'grusch', 'ontological']),
        ('Robotics', ['robot', 'robotics', 'wearable', 'sensor', 'camera', 'lidar', 'hardware']),
        ('XR', ['vision pro', 'visionos', 'meta quest', 'quest', 'smart glasses', 'android xr', 'spatial', 'mixed reality', 'augmented reality', 'virtual reality']),
        ('AI', ['gpt', 'llm', 'ai', 'agent', 'agents', 'automation', 'model', 'brand kit', 'openai', 'claude']),
        ('Business', ['startup', 'founder', 'revenue', 'market', 'launch', 'pricing', 'sales', 'customer']),
        ('Science', ['biology', 'science', 'protein', 'genome', 'flagellum', 'genetics', 'cell']),
    ]
    for label, needles in rules:
        if any((re.search(r'\bai\b', text) if n == 'ai' else n in text) for n in needles):
            return label
    return 'Other'


def classify_intent(item):
    text = clean(item.get('text') or '').lower()
    if any(n in text for n in ['watch', 'video', 'filmed', 'clip', 'demo']):
        return 'Watch later'
    if any(n in text for n in ['launch', 'try', 'tool', 'app', 'build', 'free', 'clone']):
        return 'Try'
    if any(n in text for n in ['research', 'study', 'science', 'genome', 'biology', 'report']):
        return 'Research'
    return None


def build_folders(items):
    folders = defaultdict(list)
    people = defaultdict(int)
    for item in items:
        folders[classify_folder(item)].append(item)
        intent = classify_intent(item)
        if intent:
            folders[intent].append(item)
        handle = item.get('authorHandle')
        if handle:
            people[handle] += 1
    if people:
        folders['People'] = [{'authorHandle': h, 'count': c} for h, c in sorted(people.items(), key=lambda kv: (-kv[1], kv[0]))]
    return folders


def folder_entries(folders):
    preferred = ['AI', 'UFO', 'Business', 'Science', 'Robotics', 'XR', 'Try', 'Research', 'Watch later', 'People', 'Other']
    return [(name, len(folders[name])) for name in preferred if name in folders and folders[name]]


def buttons_for_folders(folders):
    entries = folder_entries(folders)
    rows = []
    for i in range(0, min(len(entries), 9), 3):
        rows.append([
            {'text': f'{name} ({count})', 'callback_data': f'magpie:onboard:folder:{name}'}
            for name, count in entries[i:i + 3]
        ])
    rows.append([
        {'text': 'Use these folders', 'callback_data': 'magpie:onboard:confirm-folders'},
    ])
    rows.append([
        {'text': 'Smart themes', 'callback_data': 'magpie:onboard:smart'},
        {'text': 'Search now', 'callback_data': 'magpie:onboard:search'},
    ])
    return rows


def welcome():
    return {
        'stage': 'welcome',
        'text': (
            "**Welcome to Magpie**\n\n"
            "Bring your saved links into one local, searchable library.\n\n"
            "Start with folders you can understand. Magpie can add smart themes on top when you want them."
        ),
        'buttons': [[
            {'text': 'Set up folders', 'callback_data': 'magpie:onboard:folder-setup'},
            {'text': 'Smart themes', 'callback_data': 'magpie:onboard:smart'},
        ], [
            {'text': 'Search immediately', 'callback_data': 'magpie:onboard:search'}
        ]]
    }


def folder_setup(items, user):
    folders = build_folders(items)
    visible = folder_entries(folders)
    lines = [
        f"**Starter folders for @{user.get('username', 'unknown')}**",
        '',
        'Here’s a first folder map from the current import. Nothing gets moved or renamed yet — this is just the proposed shelf layout.',
        ''
    ]
    for name, count in visible[:10]:
        sample = folders[name][0]
        if name == 'People':
            example = f"top saved author: @{sample.get('authorHandle')}"
        else:
            example = short(sample.get('text') or '', 72)
        lines.append(f'- **{name}** ({count}) — {example}')
    lines.extend(['', 'Use this as the home view, tweak later, or switch to smart themes.'])
    return {
        'stage': 'folder_setup',
        'text': '\n'.join(lines),
        'buttons': [
            [
                {'text': 'Use these folders', 'callback_data': 'magpie:onboard:confirm-folders'},
                {'text': 'Preview folders', 'callback_data': 'magpie:onboard:folders'},
            ],
            [
                {'text': 'Smart themes instead', 'callback_data': 'magpie:onboard:smart'},
                {'text': 'Search now', 'callback_data': 'magpie:onboard:search'},
            ]
        ],
        'folders': {name: count for name, count in visible},
    }


def import_success(items, user):
    return {
        'stage': 'import_success',
        'text': (
            f"**Imported {len(items)} bookmarks for @{user.get('username', 'unknown')}**\n\n"
            "They’re now local, deduped, and ready to search.\n"
            "Raw bookmark data stays in Magpie’s store — not assistant memory."
        ),
        'buttons': [[
            {'text': 'Set up folders', 'callback_data': 'magpie:onboard:folder-setup'},
            {'text': 'Search', 'callback_data': 'magpie:onboard:search'},
        ]]
    }


def smart_home(items, user):
    folders = build_folders(items)
    smart_order = ['AI', 'UFO', 'Science', 'Business', 'Robotics', 'XR', 'Other']
    visible = [(name, len(folders[name])) for name in smart_order if name in folders and folders[name]]
    lines = [
        f"**Magpie’s smart themes for @{user.get('username', 'unknown')}**",
        '',
        "These are lightweight theme clusters Magpie inferred from what you saved.",
        "They’re additive — not a replacement for folder view.",
        ''
    ]
    for name, count in visible[:6]:
        lines.append(f'- {name}: {count}')
    lines.extend(['', 'Open a theme, or switch back to folder view.'])
    return {
        'stage': 'smart_home',
        'text': '\n'.join(lines),
        'buttons': [
            [
                {'text': f'{name} ({count})', 'callback_data': f'magpie:onboard:folder:{name}'}
                for name, count in visible[:3]
            ],
            [
                {'text': f'{name} ({count})', 'callback_data': f'magpie:onboard:folder:{name}'}
                for name, count in visible[3:6]
            ] if len(visible) > 3 else [],
            [
                {'text': 'Folder view', 'callback_data': 'magpie:onboard:folders'},
                {'text': 'Search now', 'callback_data': 'magpie:onboard:search'},
            ]
        ],
        'themes': {name: count for name, count in visible},
    }


def both_home(items, user):
    folders = build_folders(items)
    lines = [
        f"**Two ways in for @{user.get('username', 'unknown')}**",
        '',
        "Start with folders for control, or Magpie themes for discovery.",
        '',
        f"- Biggest folder: AI ({len(folders.get('AI', []))})",
        f"- Strongest weird cluster: UFO ({len(folders.get('UFO', []))})",
        f"- Best action bucket: Try ({len(folders.get('Try', []))})",
        '',
        "Pick the mode that feels right first. You can switch anytime."
    ]
    return {
        'stage': 'both_home',
        'text': '\n'.join(lines),
        'buttons': [
            [
                {'text': 'Folder view', 'callback_data': 'magpie:onboard:folders'},
                {'text': 'Smart themes', 'callback_data': 'magpie:onboard:smart'},
            ],
            [
                {'text': 'Search now', 'callback_data': 'magpie:onboard:search'}
            ]
        ]
    }


def folder_home(items, user):
    folders = build_folders(items)
    visible = folder_entries(folders)
    lines = [
        f"**Your Magpie folders for @{user.get('username', 'unknown')}**",
        '',
        "Folder-led first: readable shelves, then smart themes as a layer on top.",
        ''
    ]
    for name, count in visible[:10]:
        lines.append(f'- {name}: {count}')
    lines.extend(['', 'Pick a folder to open, or search across everything.'])
    return {
        'stage': 'folder_home',
        'text': '\n'.join(lines),
        'buttons': buttons_for_folders(folders),
        'folders': {name: count for name, count in visible},
    }


def folder_detail(items, folder_name, limit=5):
    folders = build_folders(items)
    selected = folders.get(folder_name, [])
    lines = [f'**{folder_name} bookmarks**', '']
    if folder_name == 'People':
        for idx, person in enumerate(selected[:limit], 1):
            lines.append(f'{idx}. @{person.get("authorHandle")} — {person.get("count")} saved')
    else:
        for idx, item in enumerate(selected[:limit], 1):
            author = item.get('authorHandle') or 'unknown'
            lines.append(f'{idx}. **@{author}**')
            lines.append(short(item.get('text') or ''))
            if item.get('url'):
                lines.append(f'<{item.get("url")}>')
            lines.append('')
    remaining = len(selected) - limit
    if remaining > 0:
        lines.append(f'_And {remaining} more._')
    return {
        'stage': 'folder_detail',
        'folder': folder_name,
        'count': len(selected),
        'text': '\n'.join(lines).strip(),
        'buttons': [[
            {'text': 'Back to folders', 'callback_data': 'magpie:onboard:folders'},
            {'text': 'Search all', 'callback_data': 'magpie:onboard:search'},
        ]]
    }


def main():
    parser = argparse.ArgumentParser(description='Magpie staged onboarding prototype')
    parser.add_argument('stage', choices=['welcome', 'import-success', 'folder-setup', 'confirm-folders', 'folders', 'folder', 'smart', 'both'])
    parser.add_argument('--folder', default='AI')
    parser.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()

    items, user = load_items()
    if args.stage == 'welcome':
        payload = welcome()
    elif args.stage == 'import-success':
        payload = import_success(items, user)
    elif args.stage == 'folder-setup':
        payload = folder_setup(items, user)
    elif args.stage == 'confirm-folders':
        payload = folder_home(items, user)
        payload['stage'] = 'folders_confirmed'
        payload['text'] = '**Folders are your Magpie home now.**\n\n' + payload['text']
    elif args.stage == 'folders':
        payload = folder_home(items, user)
    elif args.stage == 'smart':
        payload = smart_home(items, user)
    elif args.stage == 'both':
        payload = both_home(items, user)
    else:
        payload = folder_detail(items, args.folder, args.limit)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
