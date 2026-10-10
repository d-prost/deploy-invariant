#!/usr/bin/env python3
"""Synthetic SQLite application recovery reference, not a deployment tool.

Uses SQLite's live backup API and exercises an isolated restored database
through a loopback-only HTTP endpoint. No Production state is ever mutated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

EXPECTED_NOTES = [
    (1, "alpha", "Synthetic first note"),
    (2, "beta", "Synthetic second note"),
    (3, "gamma", "Synthetic third note"),
]


class RecoveryError(RuntimeError):
    pass


def _source(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise RecoveryError("source must be an existing regular non-symlink file")
    return path.resolve()


def _open_readonly(path: Path) -> sqlite3.Connection:
    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=2)


def _read_notes(connection: sqlite3.Connection) -> list[tuple[int, str, str]]:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity != ("ok",):
        raise RecoveryError("SQLite integrity_check failed")
    rows = connection.execute("SELECT id, title, body FROM notes ORDER BY id").fetchall()
    if rows != EXPECTED_NOTES:
        raise RecoveryError("restored application data does not match synthetic fixtures")
    return rows


def seed(path: Path) -> None:
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise RecoveryError("seed destination must be absent and parent directory must exist")
    try:
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, title TEXT UNIQUE NOT NULL, body TEXT NOT NULL)")
            db.executemany("INSERT INTO notes (id, title, body) VALUES (?, ?, ?)", EXPECTED_NOTES)
            db.commit()
        os.chmod(path, 0o600)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def export_backup(source: Path, destination: Path) -> str:
    source = _source(source)
    if destination.exists() or destination.is_symlink() or not destination.parent.is_dir():
        raise RecoveryError("backup destination must be absent and parent directory must exist")
    if destination.resolve() == source:
        raise RecoveryError("backup destination must differ from source")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".sqlite-export-", suffix=".db", dir=destination.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
        with closing(_open_readonly(source)) as live:
            _read_notes(live)
            with closing(sqlite3.connect(temp_path)) as backup:
                live.backup(backup, pages=100, sleep=0.1)
        with closing(_open_readonly(temp_path)) as exported:
            _read_notes(exported)
        # os.link is exclusive: an existing destination is never overwritten.
        os.link(temp_path, destination)
        return hashlib.sha256(destination.read_bytes()).hexdigest()
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


class NotesHandler(BaseHTTPRequestHandler):
    database: Path

    def do_GET(self) -> None:
        if self.path not in ("/health", "/notes"):
            self.send_error(404)
            return
        try:
            with closing(_open_readonly(self.database)) as db:
                notes = _read_notes(db)
            payload: dict = {"status": "ok"} if self.path == "/health" else {
                "notes": [{"id": note_id, "title": title, "body": body} for note_id, title, body in notes]
            }
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (sqlite3.Error, RecoveryError):
            self.send_error(503)

    def log_message(self, *_args: object) -> None:
        pass


def verify_isolated_restore(backup: Path, workspace: Path) -> dict:
    backup = _source(backup)
    if not workspace.is_dir():
        raise RecoveryError("isolated workspace directory does not exist")

    before_digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="deploy-invariant-isolated-", dir=workspace) as tmp:
        restored = Path(tmp) / "restored.db"
        shutil.copyfile(backup, restored)
        with closing(_open_readonly(restored)) as db:
            notes = _read_notes(db)

        handler = type("IsolatedNotesHandler", (NotesHandler,), {"database": restored})
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        try:
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            with urlopen(base + "/health", timeout=3) as response:
                if response.status != 200 or json.load(response) != {"status": "ok"}:
                    raise RecoveryError("restored application health check failed")
            with urlopen(base + "/notes", timeout=3) as response:
                api_result = json.load(response)
            expected = [{"id": note_id, "title": title, "body": body} for note_id, title, body in notes]
            if api_result != {"notes": expected}:
                raise RecoveryError("restored application HTTP notes check failed")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    if hashlib.sha256(backup.read_bytes()).hexdigest() != before_digest:
        raise RecoveryError("backup source changed during isolated restore")

    return {
        "schema_version": 1,
        "reference": "synthetic-sqlite-notes",
        "application_aware_export": "sqlite3.Connection.backup",
        "isolated_restore": "PASS",
        "functional_verification": "PASS",
        "restored_note_ids": [row[0] for row in notes],
        "backup_sha256": before_digest,
        "measured_restore_seconds": round(time.monotonic() - started, 3),
        "production_unchanged": "NOT_EVALUATED",
        "configuration_rollback_safe": "NOT_EVALUATED",
        "rpo_met": "NOT_EVALUATED",
        "rto_met": "NOT_EVALUATED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("seed", help="create synthetic disposable SQLite source")
    create.add_argument("database", type=Path)
    backup = commands.add_parser("export", help="create application-aware SQLite backup")
    backup.add_argument("database", type=Path)
    backup.add_argument("backup", type=Path)
    restore = commands.add_parser("verify-restore", help="test backup in an isolated temporary directory")
    restore.add_argument("backup", type=Path)
    restore.add_argument("workspace", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "seed":
            seed(args.database)
            print("Synthetic SQLite data created")
        elif args.command == "export":
            print(json.dumps({"backup_sha256": export_backup(args.database, args.backup)}))
        else:
            print(json.dumps(verify_isolated_restore(args.backup, args.workspace), sort_keys=True))
    except (OSError, sqlite3.Error, RecoveryError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
