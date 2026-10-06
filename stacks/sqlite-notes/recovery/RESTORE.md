# Synthetic SQLite recovery reference

This reference proves the stateful recovery boundary with public, synthetic data. It is not a backup framework, and configuration rollback never becomes responsible for application data.

## Boundary

- Git-managed configuration: `compose.yaml`, `defaults.env`, `app.py` and `stack.yml`.
- Persistent application data: the Compose `notes_data` volume mounted at `/data`.
- Application-aware export: `app.py export` reads the SQLite schema and emits a versioned JSON document.
- Recovery: `app.py restore` accepts only that versioned export and refuses to overwrite an existing database.
- Isolation: restore uses a different Compose project and therefore a different named volume.
- Functional verification: the restored application must serve the representative synthetic note over HTTP.
- Configuration rollback: DeployInvariant may restore previous accepted managed files, but it never rewinds or replaces `notes_data`.

Real recovery-readiness evidence still belongs outside the public repository and must satisfy `scripts/check-recovery-readiness.py`.

## Automated proof

Run:

```bash
make stateful-recovery-proof
```

The proof performs this sequence:

1. start a source project and create the synthetic note `reference=synthetic-state-v1`;
2. read the live database through the application's `export` command;
3. validate the exported JSON shape;
4. restore it into a separate Compose project and named volume;
5. start the restored application and read the representative note through HTTP;
6. change only the restored copy;
7. verify the source application still returns the original value;
8. destroy both disposable projects and volumes.

The restore project never mounts the source volume and the proof never invokes configuration rollback as a data-recovery mechanism.

## Manual equivalent

From this stack directory, use distinct project names. The export contains synthetic JSON and may be inspected directly.

```bash
docker compose --env-file defaults.env -f compose.yaml -p source up -d

docker compose --env-file defaults.env -f compose.yaml -p source exec -T notes \
  python /app/app.py seed --database /data/notes.db \
  --key reference --value synthetic-state-v1

docker compose --env-file defaults.env -f compose.yaml -p source exec -T notes \
  python /app/app.py export --database /data/notes.db > /tmp/notes-export.json

docker compose --env-file defaults.env -f compose.yaml -p restore run --rm --no-deps -T notes \
  python /app/app.py restore --database /data/notes.db < /tmp/notes-export.json

docker compose --env-file defaults.env -f compose.yaml -p restore up -d
```

For a real service, replace the synthetic export and restore commands with that application's database-aware tooling and keep the same isolation and verification properties.
