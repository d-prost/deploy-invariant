#!/usr/bin/env python3
"""Functional and negative proof for the synthetic stateful reference."""
from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "examples" / "stateful-sqlite" / "recovery.py"
spec = importlib.util.spec_from_file_location("stateful_sqlite_reference", MODULE)
assert spec and spec.loader
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


class StatefulSQLiteReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="deploy-invariant-sqlite-proof-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "source.db"
        self.backup = self.root / "backup.db"
        self.workspace = self.root / "isolated"
        self.workspace.mkdir()
        reference.seed(self.source)

    def test_export_and_http_restore_preserve_source(self) -> None:
        before = self.source.read_bytes()
        reference.export_backup(self.source, self.backup)
        self.assertEqual(before, self.source.read_bytes())
        result = reference.verify_isolated_restore(self.backup, self.workspace)
        self.assertEqual(result["isolated_restore"], "PASS")
        self.assertEqual(result["functional_verification"], "PASS")
        self.assertEqual(result["restored_note_ids"], [1, 2, 3])
        self.assertEqual(result["production_unchanged"], "NOT_EVALUATED")
        self.assertEqual(result["configuration_rollback_safe"], "NOT_EVALUATED")
        self.assertEqual(before, self.source.read_bytes())
        self.assertEqual(list(self.workspace.iterdir()), [], "isolated restore must be cleaned up")

    def test_never_overwrite_source_or_existing_backup(self) -> None:
        with self.assertRaises(reference.RecoveryError):
            reference.export_backup(self.source, self.source)
        reference.export_backup(self.source, self.backup)
        digest = self.backup.read_bytes()
        with self.assertRaises(reference.RecoveryError):
            reference.export_backup(self.source, self.backup)
        self.assertEqual(digest, self.backup.read_bytes())

    def test_reject_symlinked_source(self) -> None:
        link = self.root / "linked.db"
        link.symlink_to(self.source)
        with self.assertRaises(reference.RecoveryError):
            reference.export_backup(link, self.backup)

    def test_reject_corrupt_backup_without_false_pass(self) -> None:
        self.backup.write_bytes(b"not a sqlite database")
        with self.assertRaises((sqlite3.Error, reference.RecoveryError)):
            reference.verify_isolated_restore(self.backup, self.workspace)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_reject_wrong_application_data(self) -> None:
        with sqlite3.connect(self.source) as db:
            db.execute("UPDATE notes SET body = ? WHERE id = 2", ("tampered",))
        with self.assertRaises(reference.RecoveryError):
            reference.export_backup(self.source, self.backup)
        self.assertFalse(self.backup.exists())

    def test_seed_cannot_overwrite_existing_source(self) -> None:
        before = self.source.read_bytes()
        with self.assertRaises(reference.RecoveryError):
            reference.seed(self.source)
        self.assertEqual(before, self.source.read_bytes())


if __name__ == "__main__":
    unittest.main()
