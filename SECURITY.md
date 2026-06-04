# Security Policy

This is a personal learning project. There is no formal SLA, but security reports are welcome.

## Reporting a vulnerability

Please report any vulnerability privately by email to **brunotfurtado@gmail.com**, or by opening a
private security advisory under the repository's **Security** tab. Include steps to reproduce and
the affected files when possible. Avoid opening a public issue for security matters.

## Scope

The repository contains a data pipeline for the public NYC TLC dataset and its tooling. No
credentials are stored in the repo: Databricks auth lives in `~/.databrickscfg` and CI uses GitHub
repository secrets.
