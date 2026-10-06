#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
import time
from pathlib import Path


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def open_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def assert_integrity(connection: sqlite3.Connection, label: str) -> None:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    if row != ("ok",):
        raise RuntimeError(f"{label}: SQLite integrity_check failed: {row!r}")


def create_synthetic_source(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                body TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [("dataset", "synthetic-only"), ("generation", "baseline-v1")],
        )
        connection.executemany(
            "INSERT INTO notes(id, slug, body) VALUES (?, ?, ?)",
            [
                (1, "alpha", "synthetic recovery record alpha"),
                (2, "bravo", "synthetic recovery record bravo"),
                (3, "charlie", "synthetic recovery record charlie"),
            ],
        )
        connection.commit()
        assert_integrity(connection, "source")


def application_aware_export(source: Path, backup: Path) -> None:
    backup.parent.mkdir(parents=True, exist_ok=True)
    with open_read_only(source) as source_connection:
        with sqlite3.connect(backup) as backup_connection:
            source_connection.backup(backup_connection)
            assert_integrity(backup_connection, "backup")


def isolated_restore(backup: Path, restored: Path) -> None:
    restored.parent.mkdir(parents=True, exist_ok=True)
    with open_read_only(backup) as backup_connection:
        with sqlite3.connect(restored) as restore_connection:
            backup_connection.backup(restore_connection)
            assert_integrity(restore_connection, "restored database")


def representative_snapshot(path: Path) -> dict:
    with open_read_only(path) as connection:
        assert_integrity(connection, "functional verification")
        metadata = dict(
            connection.execute("SELECT key, value FROM metadata ORDER BY key").fetchall()
        )
        notes = [
            {"id": row[0], "slug": row[1], "body": row[2]}
            for row in connection.execute(
                "SELECT id, slug, body FROM notes ORDER BY id"
            ).fetchall()
        ]
        recovered = connection.execute(
            "SELECT body FROM notes WHERE slug = ?",
            ("bravo",),
        ).fetchone()
        return {
            "metadata": metadata,
            "notes": notes,
            "representative_lookup": recovered[0] if recovered else None,
        }


def run_proof(rto_target_seconds: float) -> dict:
    if rto_target_seconds <= 0:
        raise ValueError("--rto-target-seconds must be positive")

    with tempfile.TemporaryDirectory(prefix="deploy-invariant-stateful-reference.") as raw:
        root = Path(raw)
        source = root / "source" / "application.sqlite3"
        backup = root / "backup" / "application.sqlite3"
        restored = root / "isolated-restore" / "application.sqlite3"

        create_synthetic_source(source)
        expected = representative_snapshot(source)
        source_hash_before = file_sha256(source)

        export_started = time.monotonic()
        application_aware_export(source, backup)
        export_elapsed_ms = int((time.monotonic() - export_started) * 1000)
        source_hash_after_export = file_sha256(source)

        restore_started = time.monotonic()
        isolated_restore(backup, restored)
        recovered = representative_snapshot(restored)
        rto_elapsed_seconds = time.monotonic() - restore_started
        rto_elapsed_ms = int(rto_elapsed_seconds * 1000)

        source_hash_after_restore = file_sha256(source)
        source_unchanged = (
            source_hash_before
            == source_hash_after_export
            == source_hash_after_restore
        )
        functional_verification = recovered == expected
        rpo_observed_seconds = 0
        rpo_target_seconds = 0
        rto_met = rto_elapsed_seconds <= rto_target_seconds
        isolated = source.resolve() != restored.resolve()

        passed = (
            source_unchanged
            and functional_verification
            and isolated
            and rpo_observed_seconds <= rpo_target_seconds
            and rto_met
        )

        return {
            "schema_version": 1,
            "reference": "sqlite-synthetic-stateful-recovery",
            "synthetic_data_only": True,
            "application_export": {
                "method": "sqlite3.Connection.backup",
                "database_aware": True,
                "raw_file_copy": False,
                "elapsed_milliseconds": export_elapsed_ms,
            },
            "isolated_restore": {
                "passed": passed,
                "functional_verification": functional_verification,
                "source_unchanged": source_unchanged,
                "source_path_reused": not isolated,
            },
            "representative_recovery": {
                "expected": expected,
                "restored": recovered,
            },
            "source_integrity": {
                "sha256_before_export": source_hash_before,
                "sha256_after_export": source_hash_after_export,
                "sha256_after_restore": source_hash_after_restore,
            },
            "recovery_objectives": {
                "rpo_target_seconds": rpo_target_seconds,
                "rpo_observed_seconds": rpo_observed_seconds,
                "rpo_met": rpo_observed_seconds <= rpo_target_seconds,
                "rto_target_seconds": rto_target_seconds,
                "rto_observed_milliseconds": rto_elapsed_ms,
                "rto_met": rto_met,
            },
            "configuration_rollback": {
                "performed": False,
                "persistent_data_restore_claimed": False,
                "separate_control": True,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the public synthetic SQLite recovery reference: database-aware "
            "export, isolated restore and representative functional verification."
        )
    )
    parser.add_argument(
        "--rto-target-seconds",
        type=float,
        default=30.0,
        help="bounded synthetic RTO target for the isolated restore proof",
    )
    args = parser.parse_args()

    result = run_proof(args.rto_target_seconds)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["isolated_restore"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
