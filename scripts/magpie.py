#!/usr/bin/env python3
"""Magpie local-first bookmark memory CLI.

This is the small durable core behind the OpenClaw Magpie skill.
It owns the local SQLite store and basic import/search/group/export flows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / 'data'
DB_PATH = DATA / 'magpie.sqlite3'
JSONL_PATH = DATA / 'normalized' / 'x' / 'bookmarks.jsonl'
EXPORT_DIR = DATA / 'exports'

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS bookmarks (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  platform_record_id TEXT,
  saved_at TEXT,
  ingested_at TEXT,
  url TEXT,
  author_handle TEXT,
  author_name TEXT,
  title TEXT,
  text TEXT,
  source_type TEXT,
  raw_ref TEXT,
  created_at TEXT,
  media_json TEXT NOT NULL DEFAULT '[]',
  tags_json TEXT NOT NULL DEFAULT '[]',
  metrics_json TEXT NOT NULL DEFAULT '{}',
  content_hash TEXT,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_platform ON bookmarks(platform);
CREATE INDEX IF NOT EXISTS idx_bookmarks_author ON bookmarks(author_handle);
CREATE INDEX IF NOT EXISTS idx_bookmarks_ingested ON bookmarks(ingested_at);
CREATE INDEX IF NOT EXISTS idx_bookmarks_created ON bookmarks(created_at);

CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks_fts USING fts5(
  id UNINDEXED,
  title,
  text,
  author_handle,
  author_name,
  url
);
"""

from classify import GROUP_RULES, rule_group  # noqa: E402


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def preview(text: str | None, n: int = 180) -> str:
    value = (text or '').replace('\n', ' ').strip()
    return value if len(value) <= n else value[: n - 1] + '…'


def stable_hash(row: dict[str, Any]) -> str:
    seed = '|'.join([
        row.get('platform') or '',
        row.get('platformRecordId') or '',
        row.get('url') or '',
        row.get('text') or '',
    ])
    return hashlib.sha256(seed.encode('utf-8')).hexdigest()


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def load_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open() as f:
        for line in f:
            if not line.strip():
                continue
            yield json.loads(line)


def upsert_bookmark(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    bookmark_id = row.get('id') or f"{row.get('platform','unknown')}:{row.get('platformRecordId') or stable_hash(row)[:16]}"
    updated_at = now_iso()
    values = {
        'id': bookmark_id,
        'platform': row.get('platform') or 'unknown',
        'platform_record_id': row.get('platformRecordId'),
        'saved_at': row.get('savedAt'),
        'ingested_at': row.get('ingestedAt'),
        'url': row.get('url'),
        'author_handle': row.get('authorHandle'),
        'author_name': row.get('authorName'),
        'title': row.get('title'),
        'text': row.get('text'),
        'source_type': row.get('sourceType'),
        'raw_ref': row.get('rawRef'),
        'created_at': row.get('createdAt'),
        'media_json': json.dumps(row.get('media') or []),
        'tags_json': json.dumps(row.get('tags') or []),
        'metrics_json': json.dumps(row.get('metrics') or {}),
        'content_hash': stable_hash(row),
        'updated_at': updated_at,
    }
    conn.execute(
        """
        INSERT INTO bookmarks (
          id, platform, platform_record_id, saved_at, ingested_at, url,
          author_handle, author_name, title, text, source_type, raw_ref,
          created_at, media_json, tags_json, metrics_json, content_hash, updated_at
        ) VALUES (
          :id, :platform, :platform_record_id, :saved_at, :ingested_at, :url,
          :author_handle, :author_name, :title, :text, :source_type, :raw_ref,
          :created_at, :media_json, :tags_json, :metrics_json, :content_hash, :updated_at
        )
        ON CONFLICT(id) DO UPDATE SET
          platform=excluded.platform,
          platform_record_id=excluded.platform_record_id,
          saved_at=excluded.saved_at,
          ingested_at=excluded.ingested_at,
          url=excluded.url,
          author_handle=excluded.author_handle,
          author_name=excluded.author_name,
          title=excluded.title,
          text=excluded.text,
          source_type=excluded.source_type,
          raw_ref=excluded.raw_ref,
          created_at=excluded.created_at,
          media_json=excluded.media_json,
          tags_json=excluded.tags_json,
          metrics_json=excluded.metrics_json,
          content_hash=excluded.content_hash,
          updated_at=excluded.updated_at
        """,
        values,
    )
    conn.execute('DELETE FROM bookmarks_fts WHERE id = ?', (bookmark_id,))
    conn.execute(
        'INSERT INTO bookmarks_fts (id, title, text, author_handle, author_name, url) VALUES (?, ?, ?, ?, ?, ?)',
        (bookmark_id, values['title'], values['text'], values['author_handle'], values['author_name'], values['url']),
    )


def cmd_import_jsonl(args: argparse.Namespace) -> None:
    path = Path(args.path).expanduser()
    conn = connect(Path(args.db).expanduser())
    init_db(conn)
    count = 0
    for row in load_jsonl(path):
        upsert_bookmark(conn, row)
        count += 1
    conn.commit()
    total = conn.execute('SELECT COUNT(*) FROM bookmarks').fetchone()[0]
    print(json.dumps({'imported': count, 'total': total, 'db': str(Path(args.db).expanduser())}, indent=2))


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def cmd_search(args: argparse.Namespace) -> None:
    conn = connect(Path(args.db).expanduser())
    init_db(conn)
    rows = conn.execute(
        """
        SELECT b.*
        FROM bookmarks_fts f
        JOIN bookmarks b ON b.id = f.id
        WHERE bookmarks_fts MATCH ?
        ORDER BY COALESCE(b.created_at, b.ingested_at, b.updated_at) DESC
        LIMIT ?
        """,
        (args.query, args.limit),
    ).fetchall()
    print(json.dumps({
        'query': args.query,
        'count': len(rows),
        'items': [
            {
                'id': r['id'],
                'author': r['author_handle'],
                'url': r['url'],
                'createdAt': r['created_at'],
                'text': preview(r['text']),
            }
            for r in rows
        ]
    }, indent=2))


def infer_group(row: sqlite3.Row) -> str:
    return rule_group({k: row[k] for k in ('title', 'text', 'url', 'author_handle')})


def cmd_groups(args: argparse.Namespace) -> None:
    conn = connect(Path(args.db).expanduser())
    init_db(conn)
    rows = conn.execute('SELECT * FROM bookmarks').fetchall()
    buckets: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        buckets[infer_group(row)].append(row)
    output = {
        'total': len(rows),
        'groups': [
            {
                'name': name,
                'count': len(items),
                'examples': [
                    {'author': item['author_handle'], 'url': item['url'], 'text': preview(item['text'], 100)}
                    for item in items[: args.examples]
                ],
            }
            for name, items in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        ],
    }
    print(json.dumps(output, indent=2))


def cmd_stats(args: argparse.Namespace) -> None:
    conn = connect(Path(args.db).expanduser())
    init_db(conn)
    total = conn.execute('SELECT COUNT(*) FROM bookmarks').fetchone()[0]
    authors = conn.execute(
        'SELECT COALESCE(author_handle, "(unknown)") AS author, COUNT(*) AS count FROM bookmarks GROUP BY author ORDER BY count DESC LIMIT ?',
        (args.limit,),
    ).fetchall()
    platforms = conn.execute('SELECT platform, COUNT(*) AS count FROM bookmarks GROUP BY platform ORDER BY count DESC').fetchall()
    print(json.dumps({
        'db': str(Path(args.db).expanduser()),
        'total': total,
        'platforms': [dict(row) for row in platforms],
        'topAuthors': [dict(row) for row in authors],
    }, indent=2))


def cmd_export_markdown(args: argparse.Namespace) -> None:
    conn = connect(Path(args.db).expanduser())
    init_db(conn)
    rows = conn.execute(
        'SELECT * FROM bookmarks ORDER BY COALESCE(created_at, ingested_at, updated_at) DESC LIMIT ?',
        (args.limit,),
    ).fetchall()
    out = Path(args.output).expanduser() if args.output else EXPORT_DIR / f'magpie-export-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ['# Magpie Export', '', f'Generated: {now_iso()}', '', f'Items: {len(rows)}', '']
    for row in rows:
        title = row['title'] or preview(row['text'], 90) or row['url'] or row['id']
        lines.extend([
            f'## {title}',
            '',
            f'- Author: {row["author_handle"] or "unknown"}',
            f'- URL: {row["url"] or ""}',
            f'- Created: {row["created_at"] or ""}',
            '',
            row['text'] or '',
            '',
        ])
    out.write_text('\n'.join(lines))
    print(json.dumps({'output': str(out), 'items': len(rows)}, indent=2))


def row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    """Shape a row the way the Mews shelf generator expects to read it."""
    return {
        'id': row['id'],
        'authorHandle': row['author_handle'],
        'createdAt': row['created_at'],
        'text': row['text'],
        'url': row['url'],
        'metrics': json.loads(row['metrics_json'] or '{}'),
    }


def cmd_export_json(args: argparse.Namespace) -> None:
    """Export a selected slice as items[] JSON for `mews generate_shelf --input`."""
    conn = connect(Path(args.db).expanduser())
    init_db(conn)

    if args.query:
        rows = conn.execute(
            """
            SELECT b.*
            FROM bookmarks_fts f
            JOIN bookmarks b ON b.id = f.id
            WHERE bookmarks_fts MATCH ?
            ORDER BY COALESCE(b.created_at, b.ingested_at, b.updated_at) DESC
            LIMIT ?
            """,
            (args.query, args.limit),
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM bookmarks ORDER BY COALESCE(created_at, ingested_at, updated_at) DESC'
        ).fetchall()
        if args.group:
            rows = [r for r in rows if infer_group(r) == args.group][: args.limit]
        else:
            rows = rows[: args.limit]

    out = Path(args.output).expanduser() if args.output else EXPORT_DIR / f'{(args.group or args.query or "all")}.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'items': [row_to_item(r) for r in rows]}, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'output': str(out), 'items': len(rows), 'selector': args.group or args.query or 'all'}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description='Magpie local bookmark memory CLI')
    parser.add_argument('--db', default=str(DB_PATH))
    sub = parser.add_subparsers(dest='cmd', required=True)

    init = sub.add_parser('init-db')
    init.set_defaults(func=lambda args: (init_db(connect(Path(args.db).expanduser())), print(json.dumps({'db': args.db, 'initialized': True}, indent=2))))

    imp = sub.add_parser('import-jsonl')
    imp.add_argument('--path', default=str(JSONL_PATH))
    imp.set_defaults(func=cmd_import_jsonl)

    search = sub.add_parser('search')
    search.add_argument('query')
    search.add_argument('--limit', type=int, default=10)
    search.set_defaults(func=cmd_search)

    groups = sub.add_parser('groups')
    groups.add_argument('--examples', type=int, default=3)
    groups.set_defaults(func=cmd_groups)

    stats = sub.add_parser('stats')
    stats.add_argument('--limit', type=int, default=10)
    stats.set_defaults(func=cmd_stats)

    export = sub.add_parser('export-markdown')
    export.add_argument('--limit', type=int, default=25)
    export.add_argument('--output')
    export.set_defaults(func=cmd_export_markdown)

    ejson = sub.add_parser('export-json', help='emit items[] JSON for the Mews shelf generator')
    ejson.add_argument('--query', help='FTS query; selects by full-text match')
    ejson.add_argument('--group', help='theme group; selects by classifier')
    ejson.add_argument('--limit', type=int, default=1000)
    ejson.add_argument('--output')
    ejson.set_defaults(func=cmd_export_json)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
