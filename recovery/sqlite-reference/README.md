# Synthetic SQLite stateful recovery reference

This is the first public stateful recovery reference for DeployInvariant.

It uses only Python's standard-library `sqlite3` module and synthetic data.
The goal is to demonstrate the recovery control boundary without turning
DeployInvariant into a backup framework.

Run it with:

```bash
python3 recovery/sqlite-reference/prove.py
```

or:

```bash
make stateful-recovery-proof
```

The command emits one JSON result and exits non-zero if the bounded proof
fails.

## What the proof does

1. Creates a disposable SQLite database containing only synthetic records.
2. Captures a representative functional snapshot.
3. Creates a database-aware export with SQLite's online backup API
   (`sqlite3.Connection.backup`) rather than copying database-file bytes.
4. Restores that export into a separate path.
5. Runs `PRAGMA integrity_check`, verifies metadata and all synthetic records,
   and performs a representative lookup on the restored database.
6. Confirms the source database SHA-256 is unchanged by export and restore.
7. Reports bounded synthetic RPO/RTO observations.

The proof has no writes between the captured source state and the backup, so
its observed RPO is zero seconds. The default isolated-restore RTO target is
30 seconds.

## Control boundary

Persistent-data recovery is deliberately separate from configuration rollback.

This reference:

- does not call the deployment transaction;
- does not replace the source database during restore;
- does not claim that configuration rollback recovered application data;
- does not store a real recovery-readiness file in Git.

A real stateful deployment still needs private evidence that matches its exact
stack-generation hash and environment policy as described in
[`docs/RECOVERY_READINESS.md`](../../docs/RECOVERY_READINESS.md).

## What it does not prove

This public reference does not prove a real backup schedule, offsite retention,
encryption, secrets handling, a service-specific schema compatibility decision,
or environment-specific RPO/RTO. Those remain adoption responsibilities.

The reference exists to make the expected mechanics executable and reviewable:
database-aware export, isolated restore, representative functional recovery,
source unchanged, and explicit separation from configuration rollback.
