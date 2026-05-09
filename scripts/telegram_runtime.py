import json
import argparse
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
VIEW = BASE / 'scripts' / 'telegram_view.py'
ONBOARD = BASE / 'scripts' / 'staged_onboarding.py'


def run_script(script, args):
    cmd = ['python3', str(script)] + args
    return subprocess.check_output(cmd, text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['digest', 'latest', 'search', 'author', 'topic', 'onboard'])
    parser.add_argument('value', nargs='?')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--stage', choices=['welcome', 'import-success', 'folder-setup', 'confirm-folders', 'folders', 'folder', 'smart', 'both'])
    parser.add_argument('--folder')
    args = parser.parse_args()

    if args.mode == 'onboard':
        stage = args.stage or 'welcome'
        onboard_args = [stage]
        if stage == 'folder':
            onboard_args.extend(['--folder', args.folder or args.value or 'AI', '--limit', str(args.limit)])
        payload = json.loads(run_script(ONBOARD, onboard_args))
        print(json.dumps(payload, indent=2))
        return

    view_args = [args.mode]
    if args.value:
        view_args.append(args.value)
    if args.mode != 'digest':
        view_args.extend(['--limit', str(args.limit)])
    text = run_script(VIEW, view_args).strip()

    buttons = []
    if args.mode in ('search', 'topic', 'author', 'latest'):
        buttons = [
            [
                {'text': 'Digest', 'callback_data': 'magpie:digest'},
                {'text': 'Latest', 'callback_data': 'magpie:latest'},
                {'text': 'AI', 'callback_data': 'magpie:topic:ai'},
            ],
            [
                {'text': 'XR', 'callback_data': 'magpie:topic:xr'},
                {'text': '🛸', 'callback_data': 'magpie:topic:weird'},
                {'text': 'Folders', 'callback_data': 'magpie:onboard:folders'},
            ],
            [
                {'text': 'Start onboarding', 'callback_data': 'magpie:onboard:welcome'}
            ]
        ]
    elif args.mode == 'digest':
        buttons = [[
            {'text': 'Latest', 'callback_data': 'magpie:latest'},
            {'text': 'AI', 'callback_data': 'magpie:topic:ai'},
            {'text': '🛸', 'callback_data': 'magpie:topic:weird'},
        ], [
            {'text': 'Start onboarding', 'callback_data': 'magpie:onboard:welcome'}
        ]]

    print(json.dumps({'text': text, 'buttons': buttons}, indent=2))


if __name__ == '__main__':
    main()
