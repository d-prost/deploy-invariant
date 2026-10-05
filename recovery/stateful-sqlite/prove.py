#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

EXPECTED_ROWS = [
    (1, "ORD-1001", "queued", 1299),
    (2, "ORD-1002", "paid", 2499),
    (3, "ORD-1003", "shipped", 3599),
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def readonly_uri(path: Path) -> str:
    return f"file:{path}?mode=ro"


def seed_source_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA user_version = 1")
        connection.execute(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                reference TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0)
            )
            """
        )
        connection.executemany(
            "INSERT INTO orders (id, reference, status, amount_cents) VALUES (?, ?, ?, ?)",
            EXPECTED_ROWS,
        )
        connection.commit()


def create_database_aware_export(source: Path, export_path: Path) -> None:
    with closing(sqlite3.connect(readonly_uri(source), uri=True)) as source_db:
        with closing(sqlite3.connect(export_path)) as export_db:
            source_db.backup(export_db)
            export_db.commit()


def restore_isolated(export_path: Path, restored_path: Path) -> None:
    with closing(sqlite3.connect(readonly_uri(export_path), uri=True)) as export_db:
        with closing(sqlite3.connect(restored_path)) as restored_db:
            export_db.backup(restored_db)
            restored_db.commit()


def verify_database(path: Path) -> dict[str, object]:
    with closing(sqlite3.connect(readonly_uri(path), uri=True)) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()
        rows = connection.execute(
            "SELECT id, reference, status, amount_cents FROM orders ORDER BY id"
        ).fetchall()

    require(integrity == ("ok",), f"integrity check failed: {integrity!r}")
    require(user_version == (1,), f"unexpected schema version: {user_version!r}")
    require(rows == EXPECTED_ROWS, f"representative data mismatch: {rows!r}")

    return {
        "integrity_check": "ok",
        "schema_version": 1,
        "representative_rows": len(rows),
    }


def run_proof() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="deploy-invariant-stateful-recovery.") as raw_tmp:
        root = Path(raw_tmp)
        source_dir = root / "source"
        export_dir = root / "export"
        restore_dir = root / "isolated-restore"
        source_dir.mkdir()
        export_dir.mkdir()
        restore_dir.mkdir()

        source = source_dir / "live.sqlite3"
        export_path = export_dir / "synthetic-export.sqlite3"
        restored = restore_dir / "restored.sqlite3"

        seed_source_database(source)
        source_hash_before = sha256_file(source)

        create_database_aware_export(source, export_path)
        require(export_path.is_file(), "database-aware export was not created")
        export_verification = verify_database(export_path)

        restore_isolated(export_path, restored)
        require(restored.is_file(), "isolated restore was not created")
        require(restored.parent == restore_dir, "restore escaped the isolated target directory")
        restored_verification = verify_database(restored)

        source_hash_after = sha256_file(source)
        require(
            source_hash_after == source_hash_before,
            "source database changed during export or isolated restore",
        )

        return {
            "schema_version": 1,
            "reference": "sqlite",
            "data_class": "synthetic-only",
            "export_method": "sqlite3.Connection.backup",
            "database_aware_export": True,
            "isolated_restore": True,
            "functional_verification": True,
            "source_unchanged": True,
            "source_sha256": source_hash_after,
            "export_verification": export_verification,
            "restore_verification": restored_verification,
        }


def main() -> int:
    result = run_proof()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
