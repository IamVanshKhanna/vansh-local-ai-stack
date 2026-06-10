# Versioning

This project uses [Semantic Versioning](https://semver.org/).

## Tag Scheme

```
v1.0.0  — Scenario B baseline: clean repo, fixed build, NVIDIA GPU, vls doctor
v1.1.0  — setup.ps1 idempotent + vls doctor notifications
v1.2.0  — Windows Task Scheduler automation (3 .xml exports + setup.ps1 registration)
v1.3.0  — Notification hooks (toast + email)
```

Each tag is a stable milestone. Every tag has a corresponding entry in CHANGELOG.md.

## Branch Strategy

- `main` — stable, tagged releases only
- Feature work happens on short-lived branches: `v1.1/setup-ps1`
