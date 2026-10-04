#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-target-inventory.py"


def write_inventory(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


def run(
    path: Path,
    environment: str,
    extra_env: dict[str, str] | None = None,
    extra_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["python3", str(VALIDATOR), str(path), "--environment", environment, *extra_args],
        text=True,
        capture_output=True,
        env=env,
    )


def expect_ok(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


def expect_fail(result: subprocess.CompletedProcess[str], text: str) -> None:
    if result.returncode == 0:
        raise AssertionError("expected target-inventory validation failure")
    combined = result.stdout + result.stderr
    if "PRE_MUTATION_REFUSAL" not in combined or text not in combined:
        raise AssertionError(combined)


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    inventory = root / "hosts.yml"

    write_inventory(
        inventory,
        """---
all:
  hosts:
    prod:
      ansible_connection: ssh
      ansible_host: example.invalid
      ansible_user: operator
      deploy_invariant_environment: production
      deploy_invariant_expected_hostname: prod.example
      deploy_invariant_expected_machine_id: null
""",
    )
    expect_ok(run(inventory, "production"))

    expect_fail(
        run(
            inventory,
            "production",
            {"ANSIBLE_SSH_ARGS": "-o StrictHostKeyChecking=no"},
        ),
        "ANSIBLE_SSH_ARGS weakens SSH host-key verification",
    )

    write_inventory(
        inventory,
        """---
all:
  hosts:
    prod:
      ansible_connection: local
      ansible_host: 127.0.0.1
      deploy_invariant_environment: production
      deploy_invariant_expected_hostname: prod.example
""",
    )
    expect_fail(run(inventory, "production"), "must use the ssh connection plugin")

    write_inventory(
        inventory,
        """---
all:
  hosts:
    prod:
      ansible_connection: ssh
      ansible_host: example.invalid
      ansible_user: operator
      ansible_ssh_common_args: "-o StrictHostKeyChecking=no"
      deploy_invariant_environment: production
      deploy_invariant_expected_hostname: prod.example
""",
    )
    expect_fail(run(inventory, "production"), "weakens SSH host-key verification")

    write_inventory(
        inventory,
        """---
all:
  hosts:
    prod:
      ansible_connection: ssh
      ansible_host: example.invalid
      ansible_user: operator
      deploy_invariant_environment: production
      deploy_invariant_expected_hostname: prod.example
      deploy_invariant_expected_machine_id: NOT-A-MACHINE-ID
""",
    )
    expect_fail(run(inventory, "production"), "must be null or 32 lowercase hex")

    write_inventory(
        inventory,
        """---
all:
  hosts:
    lab:
      ansible_connection: local
      ansible_host: 127.0.0.1
      deploy_invariant_environment: lab
      deploy_invariant_expected_hostname: disposable-lab
""",
    )
    expect_ok(run(inventory, "lab"))
    expect_fail(
        run(inventory, "lab", extra_args=("--require-ssh", "--single-host")),
        "must use the ssh connection plugin",
    )

    remote = """---
all:
  hosts:
    lab:
      ansible_connection: ssh
      ansible_host: example.invalid
      deploy_invariant_environment: lab
      deploy_invariant_expected_hostname: disposable-lab
"""
    write_inventory(inventory, remote)
    remote_args = ("--require-ssh", "--single-host", "--outside-repository", str(ROOT))
    expect_ok(run(inventory, "lab", extra_args=remote_args))
    expect_fail(
        run(inventory, "lab", {"ANSIBLE_SSH_ARGS": "-o StrictHostKeyChecking=no"}, remote_args),
        "weakens SSH host-key verification",
    )
    write_inventory(inventory, remote.replace("ansible_host:", "ansible_host_key_checking: false\n      ansible_host:"))
    expect_fail(run(inventory, "lab", extra_args=remote_args), "host-key checking must not be disabled")
    write_inventory(inventory, remote + "    second:\n      ansible_connection: ssh\n")
    expect_fail(run(inventory, "lab", extra_args=remote_args), "exactly one host")
    write_inventory(inventory, remote)
    expect_fail(
        run(inventory, "lab", extra_args=("--outside-repository", str(root))),
        "outside the repository tree",
    )
    alias = root / "alias.yml"
    alias.symlink_to(inventory)
    expect_fail(
        run(alias, "lab", extra_args=("--outside-repository", str(root))),
        "outside the repository tree",
    )

print(
    "Target inventory policy tests passed: Production SSH is mandatory, "
    "host-key weakening is refused, machine ID is optional and validated."
)
