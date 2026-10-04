# Security Policy

## Supported versions

Security fixes are applied to the default branch and, once releases exist, to the latest supported major release.

## Reporting

Use GitHub Private Vulnerability Reporting from the repository Security tab for suspected vulnerabilities.

Public issues should not contain exploit details, credentials, private hostnames, internal addresses, private URLs, backup metadata, private keys or recovery material.

## Project boundary

DeployInvariant contains reusable deployment logic, not real Production inventory or secrets.

Host hardening, network access control, secret storage, backup execution, restore testing and monitoring remain separate operational responsibilities.

Configuration rollback is not data recovery.

## Secret exposure

A committed secret should be treated as compromised: rotate or revoke it first, then remove it from the repository and rewrite history if the exposure requires it.
