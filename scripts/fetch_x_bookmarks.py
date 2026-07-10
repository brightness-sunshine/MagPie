import os
import json
import argparse
import base64
from datetime import datetime, timezone
from pathlib import Path
import requests

try:  # optional: only needed for the OAuth 1.0a user-context fallback
    from requests_oauthlib import OAuth1
except ImportError:  # pragma: no cover
    OAuth1 = None

BASE = Path(__file__).resolve().parents[1]
ENV_PATH = Path(os.environ.get('MAGPIE_ENV_PATH', '')).expanduser() if os.environ.get('MAGPIE_ENV_PATH') else None
RAW_DIR = BASE / 'data' / 'raw' / 'x'
NORM_DIR = BASE / 'data' / 'normalized' / 'x'
RAW_DIR.mkdir(parents=True, exist_ok=True)
NORM_DIR.mkdir(parents=True, exist_ok=True)


def load_env():
    vals = dict(os.environ)
    if ENV_PATH and ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if not line or line.lstrip().startswith('#') or '=' not in line:
                continue
            key, val = line.split('=', 1)
            vals[key.strip()] = val.strip().strip('"').strip("'")
    # Backward compatibility for the one-time misspelled secret.
    if not vals.get('X_OAUTH2_REFRESH_TOKEN') and vals.get('X_OATH2_REFRESH_TOKEN'):
        vals['X_OAUTH2_REFRESH_TOKEN'] = vals['X_OATH2_REFRESH_TOKEN']
    return vals


def save_env(updates):
    if not ENV_PATH:
        return
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    out = []
    seen = set()
    for line in lines:
        if '=' not in line or line.lstrip().startswith('#'):
            out.append(line)
            continue
        key = line.split('=', 1)[0].strip()
        if key in updates:
            out.append(f'{key}={updates[key]}')
            seen.add(key)
        else:
            out.append(line)
    for key, val in updates.items():
        if key not in seen:
            out.append(f'{key}={val}')
    ENV_PATH.write_text('\n'.join(out) + '\n')


def refresh_oauth2(env):
    refresh_token = env.get('X_OAUTH2_REFRESH_TOKEN')
    if not refresh_token:
        raise RuntimeError('Missing X_OAUTH2_REFRESH_TOKEN')
    basic = base64.b64encode(f"{env['X_CLIENT_ID']}:{env['X_CLIENT_SECRET']}".encode()).decode()
    resp = requests.post(
        'https://api.x.com/2/oauth2/token',
        headers={
            'Authorization': f'Basic {basic}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': env['X_CLIENT_ID'],
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f'OAuth2 refresh failed: {resp.status_code} {resp.text[:500]}')
    data = resp.json()
    updates = {
        'X_OAUTH2_ACCESS_TOKEN': data['access_token'],
        'X_OAUTH2_REFRESH_TOKEN': data.get('refresh_token', refresh_token),
    }
    save_env(updates)
    env.update(updates)
    return env


def oauth1_auth(env):
    if OAuth1 is None:
        raise RuntimeError('OAuth 1.0a fallback needs requests_oauthlib (pip install -r requirements.txt)')
    access_token = env.get('X_ACCESS_TOKEN')
    access_token_secret = env.get('X_ACCESS_TOKEN_SECRET')
    if not access_token or not access_token_secret:
        raise RuntimeError('Missing X_ACCESS_TOKEN or X_ACCESS_TOKEN_SECRET for OAuth 1.0a fallback')
    return OAuth1(env['X_API_KEY'], env['X_API_SECRET'], access_token, access_token_secret)


def has_oauth2_refresh(env):
    return bool(env.get('X_OAUTH2_REFRESH_TOKEN'))


def require_x_user_context(env):
    """Bookmarks need a user context; an app-only bearer token is silently insufficient."""
    if has_oauth2_refresh(env):
        return
    if env.get('X_ACCESS_TOKEN') and env.get('X_ACCESS_TOKEN_SECRET'):
        return
    raise RuntimeError(
        'X bookmark sync needs X_OAUTH2_REFRESH_TOKEN, or X_ACCESS_TOKEN + X_ACCESS_TOKEN_SECRET '
        'for the OAuth 1.0a fallback. Set them in the environment or in MAGPIE_ENV_PATH.'
    )


def authed_get(path, env, params=None):
    headers = {'Authorization': f"Bearer {env['X_OAUTH2_ACCESS_TOKEN']}"}
    resp = requests.get(f'https://api.x.com{path}', headers=headers, params=params, timeout=30)

    bearer_was_app_only = resp.status_code == 403 and 'OAuth 2.0 Application-Only' in resp.text
    oauth1_allowed = bool(env.get('X_ACCESS_TOKEN') and env.get('X_ACCESS_TOKEN_SECRET'))
    bookmarks_endpoint = path.endswith('/bookmarks')

    # The bookmarks endpoint is stricter than ordinary reads: a bearer token reaches the API
    # but is rejected without user context, so fail with a useful message instead of a 401.
    if bookmarks_endpoint and not has_oauth2_refresh(env) and resp.status_code in (401, 403):
        raise RuntimeError(
            'X bookmarks require OAuth 2.0 User Context, but no X_OAUTH2_REFRESH_TOKEN is '
            'configured. Reconnect the X integration before rerunning the bookmark sync.'
        )

    if resp.status_code == 401:
        try:
            env = refresh_oauth2(env)
            headers = {'Authorization': f"Bearer {env['X_OAUTH2_ACCESS_TOKEN']}"}
            resp = requests.get(f'https://api.x.com{path}', headers=headers, params=params, timeout=30)
        except RuntimeError:
            if oauth1_allowed:
                resp = requests.get(f'https://api.x.com{path}', auth=oauth1_auth(env), params=params, timeout=30)
    elif resp.status_code == 403 and oauth1_allowed and not bookmarks_endpoint:
        resp = requests.get(f'https://api.x.com{path}', auth=oauth1_auth(env), params=params, timeout=30)

    if bearer_was_app_only and not has_oauth2_refresh(env) and not env.get('X_ACCESS_TOKEN'):
        raise RuntimeError(
            'The stored X access token is application-only, and neither X_OAUTH2_REFRESH_TOKEN '
            'nor X_ACCESS_TOKEN is configured. Bookmarks need a user context.'
        )

    resp.raise_for_status()
    return resp.json(), env


def fetch_page(env, user_id, pagination_token=None, page_size=100):
    params = {
        'max_results': page_size,
        'tweet.fields': 'created_at,author_id,public_metrics,entities',
        'expansions': 'author_id',
        'user.fields': 'name,username,profile_image_url'
    }
    if pagination_token:
        params['pagination_token'] = pagination_token
    return authed_get(f'/2/users/{user_id}/bookmarks', env, params=params)


def normalize_items(data, ingested_at, raw_path):
    users = {u['id']: u for u in data.get('includes', {}).get('users', [])}
    normalized = []
    for item in data.get('data', []):
        author = users.get(item.get('author_id'), {})
        tweet_id = item['id']
        normalized.append({
            'id': f'x:{tweet_id}',
            'platform': 'x',
            'platformRecordId': tweet_id,
            'savedAt': None,
            'ingestedAt': ingested_at,
            'url': f'https://x.com/{author.get("username", "i")}/status/{tweet_id}' if author.get('username') else f'https://x.com/i/web/status/{tweet_id}',
            'authorHandle': author.get('username'),
            'authorName': author.get('name'),
            'title': None,
            'text': item.get('text'),
            'media': [],
            'tags': [],
            'sourceType': 'api',
            'rawRef': str(raw_path),
            'createdAt': item.get('created_at'),
            'metrics': item.get('public_metrics', {}),
        })
    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--page-size', type=int, default=100)
    args = parser.parse_args()

    env = load_env()
    me_data, env = authed_get('/2/users/me', env)
    user = me_data['data']
    user_id = user['id']

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    pagination_token = None
    all_normalized = []
    raw_files = []

    for page_num in range(1, args.pages + 1):
        data, env = fetch_page(env, user_id, pagination_token=pagination_token, page_size=args.page_size)
        raw_path = RAW_DIR / f'{ts}-page{page_num}.json'
        raw_path.write_text(json.dumps(data, indent=2))
        raw_files.append(str(raw_path))
        normalized = normalize_items(data, ts, raw_path)
        all_normalized.extend(normalized)
        pagination_token = data.get('meta', {}).get('next_token')
        if not pagination_token:
            break

    deduped = {}
    for row in all_normalized:
        deduped[row['id']] = row
    deduped_items = list(deduped.values())

    norm_path = NORM_DIR / 'bookmarks.latest.json'
    norm_path.write_text(json.dumps({
        'user': user,
        'count': len(deduped_items),
        'pagesFetched': len(raw_files),
        'next_token': pagination_token,
        'items': deduped_items,
    }, indent=2))

    jsonl_path = NORM_DIR / 'bookmarks.jsonl'
    existing = set()
    if jsonl_path.exists():
        for line in jsonl_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                existing.add(json.loads(line)['id'])
            except Exception:
                pass
    with jsonl_path.open('a') as f:
        for row in deduped_items:
            if row['id'] not in existing:
                f.write(json.dumps(row) + '\n')

    print(json.dumps({
        'user': user,
        'fetched': len(deduped_items),
        'pagesFetched': len(raw_files),
        'raw_files': raw_files,
        'latest_path': str(norm_path),
        'jsonl_path': str(jsonl_path),
        'next_token': pagination_token
    }, indent=2))


if __name__ == '__main__':
    main()
