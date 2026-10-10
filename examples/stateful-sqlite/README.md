# Synthetic SQLite stateful recovery reference

This is the first **runnable, public-safe stateful-data recovery example** for
DeployInvariant (#4). It is not a new deployment mode or a replacement for
the bounded Git/Ansible configuration transaction.

The fixture is a tiny SQLite-backed notes application with three invented
records. It uses only the Python standard library; no Production service,
credentials, host inventory, containers, or external API is involved.

## Run the end-to-end drill

From the repository root:

```bash
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir "$work/isolated"

python3 examples/stateful-sqlite/recovery.py seed "$work/source.db"
python3 examples/stateful-sqlite/recovery.py export "$work/source.db" "$work/backup.db"
python3 examples/stateful-sqlite/recovery.py verify-restore "$work/backup.db" "$work/isolated"
```

Expected result from the final command is JSON containing:

```json
{
  "isolated_restore": "PASS",
  "functional_verification": "PASS",
  "restored_note_ids": [1, 2, 3],
  "production_unchanged": "NOT_EVALUATED",
  "configuration_rollback_safe": "NOT_EVALUATED",
  "rpo_met": "NOT_EVALUATED",
  "rto_met": "NOT_EVALUATED"
}
```

The actual report additionally includes a hash and measured local restore
duration. This is **reference-specific output**, not the future product-level
terminal JSON result schema.

## What the drill actually proves

1. **Application-aware export.** The synthetic source database is opened
   read-only and exported using SQLite's `Connection.backup()`, rather than
   copying possibly active SQLite database files. Backup creation refuses to
   overwrite another file and validates the exported database.
2. **Isolated restore.** The backup is copied into an automatically generated
   temporary directory, then read read-only; the isolated database is deleted
   afterward. The original source database is never restored in-place.
3. **Functional verification.** The restored application is started as a
   loopback-only HTTP service on an ephemeral port. Both `/health` and
   `/notes` must return expected results from the restored SQLite database.
4. **Fail-closed negative cases.** Tests reject a symlink source, overwrites,
   invalid backup bytes and application data that fail the synthetic invariant.

Run the six negative/positive assertions with:

```bash
python3 tests/test-stateful-sqlite-recovery.py
```

The test is also invoked by `scripts/validate-repository.sh` on every PR.

## Boundaries (must not be conflated)

**Configuration rollback** remains the existing DeployInvariant Git/Ansible
transaction: a rejected candidate can restore previously accepted managed
configuration and reverify it, but it **does not restore persistent data**.

**Persistent-data recovery** is separately demonstrated by this fixture's
application-aware export and isolated restore. Its passing test does not prove
compatibility with a previously accepted application version or authorize
a Production database restore.

For actual stateful adoption, operators must additionally verify storage
coverage, secrets and notification isolation, RPO/RTO targets, backup age,
database version/schema compatibility, and Production non-mutation. Only
private, independently collected evidence should be projected into the strict
`DEPLOY_INVARIANT_RECOVERY_EVIDENCE` readiness schema described in
[Recovery readiness](../../docs/RECOVERY_READINESS.md). Do **not** copy this
reference report into that readiness file or mark Production `ready` based
on this example.

All data and ports in this example are local and synthetic; use a fresh
disposable directory instead of a real application database.
