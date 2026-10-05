# Stateful SQLite recovery reference

This is the first public stateful recovery reference for DeployInvariant.

It is intentionally small and synthetic. The reference proves the recovery
properties that are separate from configuration rollback without turning
DeployInvariant into a backup engine.

## What the proof demonstrates

The proof creates a temporary SQLite database containing only synthetic order
rows and then verifies all of the following:

1. a database-aware export is created with SQLite's online backup API;
2. the export itself passes an integrity check and contains the expected schema
   and representative rows;
3. the export is restored into a separate isolated directory;
4. the restored database passes the same functional checks;
5. the source database SHA-256 is unchanged before and after export and restore.

The restore function receives only the exported artifact. It does not use the
source database as restore input.

## Run it

From the repository root:

```bash
make stateful-recovery-proof
```

The command exits non-zero if any invariant fails and prints a JSON result on
success.

No real Production target, credential, backup identifier or personal data is
used. Temporary files are deleted automatically when the proof exits.

## Boundary

This example demonstrates application-data recovery only.

It does **not** change the DeployInvariant transaction model:

- configuration rollback still restores the previous accepted managed
  configuration;
- application-data recovery remains a separate operator-controlled procedure;
- recovery-readiness evidence remains the gate for adopting a real stateful
  service;
- this repository does not become a backup scheduler, backup store or recovery
  database.

Real services must still follow
[`STATEFUL_ADOPTION_CHECKLIST.md`](../STATEFUL_ADOPTION_CHECKLIST.md) and keep
private restore evidence outside the public repository.
