# Remote SSH proof: 2026-10-05

This record describes a completed transaction against a new disposable VM.
The control host and target were separate machines connected over real SSH.
Raw inventory, SSH material, machine identity, deployment records and logs
remain private.

- Date: `2026-10-05` (Europe/Berlin)
- Repository/tooling commit: `d961e914986348d3f2a18b5b6c30d9cac2641061`
- Topology: `separate SSH target`
- Target OS: `Ubuntu 26.04.1 LTS`
- Docker Engine: `29.1.3`
- Docker Compose: `2.40.3+ds1-0ubuntu1`
- Control Ansible Core: `2.19.11`

## Baseline deployment

The clean current main checkout deployed the digest-pinned Dozzle reference
through `deploy-stack.sh --inventory lab --inventory-file <private-inventory>`.

- SSH host-key verification: `PASS`; the key was verified through the
  authenticated hypervisor channel before being added to the trust store.
- Declared hostname verification: `PASS`
- Optional machine-ID verification: `PASS`
- Candidate deployment: `PASS`
- Functional verification: `PASS`
- Durable acceptance: `ACCEPTED`
- Elapsed time: `27 seconds`

## Injected failure

The fixture was committed only in a separate private disposable worktree.
It retained the accepted image digest, introduced an intentionally failing
entrypoint and added a candidate-only managed file. The clean main control
checkout deployed its local fixture ref through the same SSH inventory.

- Candidate result: `REJECTED`; wrapper exit code `2`
- Rollback entered: `YES`
- Previous managed files restored: `PASS`; Compose and defaults hashes matched
- Candidate-only managed file removed: `PASS`
- Previous Compose model reapplied: `PASS`
- Previous functional verification: `PASS`
- Accepted record preserved byte-for-byte: `PASS`
- Unresolved transaction marker absent: `PASS`
- Terminal result: `REJECTED_ROLLBACK_VERIFIED`
- Elapsed time, including verified restoration: `26 seconds`

A separate SSH command then ran the accepted functional verifier again.
The Dozzle HTTP check returned `200`; the verifier reported
`Functional verification passed for 1 check(s).`

## Cleanup

- Disposable Compose stack removed: `PASS`
- Project-managed target files removed: `PASS`
- Proof acceptance records and unresolved marker removed: `PASS`
- Candidate/recovery directories absent: `PASS`
- Private inventory committed: `NO`
- Private SSH material committed: `NO`
- Deliberate failure fixture published: `NO`

## Compatibility observations

The remote proof exposed three gaps fixed in PR #7: selecting an external lab
inventory, preventing delegated Compose rendering from inheriting target root
privileges/HOME, and collecting server facts without Docker Go-template and
Ansible template/callback conflicts. All required CI checks passed before
the fix was merged and this transaction was run.

Ansible Core 2.19 warns that the facts collector's tree callback is deprecated
for removal in 2.23. Collection succeeded with the tested version; this record
does not claim compatibility with that future removal.
