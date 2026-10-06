#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROOF = REPO / "recovery" / "sqlite-reference" / "prove.py"


def main() -> int:
    completed = subprocess.run(
        [sys.executable, str(PROOF), "--rto-target-seconds", "30"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)

    assert result["schema_version"] == 1
    assert result["reference"] == "sqlite-synthetic-stateful-recovery"
    assert result["synthetic_data_only"] is True

    export = result["application_export"]
    assert export["method"] == "sqlite3.Connection.backup"
    assert export["database_aware"] is True
    assert export["raw_file_copy"] is False

    restore = result["isolated_restore"]
    assert restore["passed"] is True
    assert restore["functional_verification"] is True
    assert restore["source_unchanged"] is True
    assert restore["source_path_reused"] is False

    representative = result["representative_recovery"]
    assert representative["expected"] == representative["restored"]
    assert len(representative["restored"]["notes"]) == 3
    assert (
        representative["restored"]["representative_lookup"]
        == "synthetic recovery record bravo"
    )
    assert representative["restored"]["metadata"] == {
        "dataset": "synthetic-only",
        "generation": "baseline-v1",
    }

    source_integrity = result["source_integrity"]
    assert (
        source_integrity["sha256_before_export"]
        == source_integrity["sha256_after_export"]
        == source_integrity["sha256_after_restore"]
    )

    objectives = result["recovery_objectives"]
    assert objectives["rpo_target_seconds"] == 0
    assert objectives["rpo_observed_seconds"] == 0
    assert objectives["rpo_met"] is True
    assert objectives["rto_target_seconds"] == 30
    assert objectives["rto_met"] is True

    rollback = result["configuration_rollback"]
    assert rollback["performed"] is False
    assert rollback["persistent_data_restore_claimed"] is False
    assert rollback["separate_control"] is True

    print(
        "Stateful recovery reference passed: database-aware export, isolated "
        "restore, representative functional recovery, source immutability and "
        "configuration/data-recovery separation verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
