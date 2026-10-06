#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

EXPORT_SCHEMA_VERSION = 1


class AppError(RuntimeError):
    pass


def connect_database(path: Path, *, read_only: bool = False) -> sqlite3.Connection:
    if read_only:
        if not path.is_file():
            raise AppError(f"database does not exist: {path}")
        return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS notes ("
        "key TEXT PRIMARY KEY, "
        "value TEXT NOT NULL"
        ")"
    )
    connection.commit()


def seed_note(database: Path, key: str, value: str) -> None:
    with connect_database(database) as connection:
        ensure_schema(connection)
        connection.execute(
            "INSERT INTO notes(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        connection.commit()


def export_payload(database: Path) -> dict:
    with connect_database(database, read_only=True) as connection:
        rows = connection.execute(
            "SELECT key, value FROM notes ORDER BY key"
        ).fetchall()
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "notes": [{"key": key, "value": value} for key, value in rows],
    }


def validate_export(payload: object) -> list[tuple[str, str]]:
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "notes"}:
        raise AppError("export must contain exactly schema_version and notes")
    if payload.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise AppError("unsupported export schema_version")
    notes = payload.get("notes")
    if not isinstance(notes, list):
        raise AppError("export notes must be a list")

    records: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(notes, 1):
        if not isinstance(item, dict) or set(item) != {"key", "value"}:
            raise AppError(f"export note #{index} must contain exactly key and value")
        key = item.get("key")
        value = item.get("value")
        if not isinstance(key, str) or not key:
            raise AppError(f"export note #{index} has an invalid key")
        if not isinstance(value, str):
            raise AppError(f"export note #{index} has an invalid value")
        if key in seen:
            raise AppError(f"export contains duplicate key: {key}")
        seen.add(key)
        records.append((key, value))
    return records


def restore_payload(database: Path, payload: object) -> None:
    if database.exists():
        raise AppError(f"refusing to restore over an existing database: {database}")
    records = validate_export(payload)
    database.parent.mkdir(parents=True, exist_ok=True)
    temporary = database.with_name(database.name + ".restore.tmp")
    if temporary.exists():
        temporary.unlink()

    try:
        with connect_database(temporary) as connection:
            ensure_schema(connection)
            connection.executemany(
                "INSERT INTO notes(key, value) VALUES (?, ?)",
                records,
            )
            connection.commit()
        temporary.replace(database)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_note(database: Path, key: str) -> str | None:
    with connect_database(database, read_only=True) as connection:
        row = connection.execute(
            "SELECT value FROM notes WHERE key = ?",
            (key,),
        ).fetchone()
    return None if row is None else str(row[0])


def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(database: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                json_response(self, 200, {"status": "ok"})
                return
            if parsed.path.startswith("/notes/"):
                key = unquote(parsed.path[len("/notes/") :])
                if not key:
                    json_response(self, 400, {"error": "missing-key"})
                    return
                value = read_note(database, key)
                if value is None:
                    json_response(self, 404, {"error": "not-found", "key": key})
                    return
                json_response(self, 200, {"key": key, "value": value})
                return
            json_response(self, 404, {"error": "not-found"})

        def log_message(self, _format: str, *_args: object) -> None:
            return

    return Handler


def serve(database: Path, host: str, port: int) -> None:
    with connect_database(database) as connection:
        ensure_schema(connection)
    server = ThreadingHTTPServer((host, port), make_handler(database))
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synthetic SQLite notes reference application")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("seed")
    seed.add_argument("--database", type=Path, required=True)
    seed.add_argument("--key", default="reference")
    seed.add_argument("--value", default="synthetic-state-v1")

    export = subparsers.add_parser("export")
    export.add_argument("--database", type=Path, required=True)

    restore = subparsers.add_parser("restore")
    restore.add_argument("--database", type=Path, required=True)

    server = subparsers.add_parser("serve")
    server.add_argument("--database", type=Path, required=True)
    server.add_argument("--host", default="0.0.0.0")
    server.add_argument("--port", type=int, default=8080)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "seed":
        seed_note(args.database, args.key, args.value)
        return 0
    if args.command == "export":
        json.dump(export_payload(args.database), sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return 0
    if args.command == "restore":
        restore_payload(args.database, json.load(sys.stdin))
        return 0
    if args.command == "serve":
        if not 1 <= args.port <= 65535:
            raise AppError("port must be between 1 and 65535")
        serve(args.database, args.host, args.port)
        return 0
    raise AppError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AppError, OSError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
