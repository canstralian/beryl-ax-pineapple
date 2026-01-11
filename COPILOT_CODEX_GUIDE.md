# Trading Bot Swarm Copilot + Codex Configuration Guide

## Purpose and Scope
This guide standardizes how GitHub Copilot and Codex are configured and used across the Trading Bot Swarm ecosystem. The goal is to ensure consistent code quality, secure automation, and predictable collaboration. Copilot acts as a pair programmer that must follow strict behavioral rules: prioritize correctness, minimize risk, and always align with the project’s security and quality standards.

This guide covers:
- Behavioral expectations for Copilot and Codex
- Configuration principles for testing, linting, and code style
- Security defaults and safe automation
- Logging, observability, and CI/CD integration
- Version control and release practices
- Contributor workflows, troubleshooting, and maintenance

## Configuration Overview
### Testing
- Run unit tests for any code change touching core logic.
- Require integration tests for trading execution paths or external API changes.
- Prefer deterministic tests; use recorded fixtures for market data where possible.

### Linting and Formatting
- Enforce project lint rules via CI to keep style uniform.
- Require formatting checks as part of the quality gate.

### Code Style
- Prefer explicit, readable code over clever shortcuts.
- Use docstrings for public APIs and key trading logic.
- Maintain a consistent file organization (domain modules grouped by feature).

### Async Patterns
- Use async/await consistently in I/O-heavy modules.
- Avoid blocking calls in event loops.
- Provide timeouts for network requests and queue operations.

### Security Defaults
- Never store secrets in code or logs.
- Validate all inbound data from exchanges and user input.
- Default to least-privilege credentials and read-only tokens where possible.

### Logging and Observability
- Use structured logging with consistent fields (request_id, strategy_id, exchange).
- Log warnings for retries or partial failures.
- Emit metrics for latency, fill rate, and error rate.

### CI/CD Integration
- Gate merges on lint + test success.
- Track coverage and ensure it meets minimum thresholds.
- Publish build artifacts only from trusted branches.

### Version Control
- Use small, well-described commits.
- Prefer linear history and squash merges for feature branches.
- Tag releases with semantic versioning (vX.Y.Z).

## Custom Instruction Behavior for Codex and Copilot
### Example Behavioral Rules
- Always run tests and linters when code changes are introduced.
- Avoid editing documentation unless explicitly requested.
- Never change CI/CD workflows without explicit approval.
- Verify API contracts when updating exchange adapters.

### Conceptual YAML Instructions
```yaml
assistant:
  role: pair_programmer
  priorities:
    - correctness
    - security
    - readability
    - maintainability
  rules:
    - run_tests_for_code_changes: true
    - run_linters_for_code_changes: true
    - no_doc_changes_without_request: true
    - enforce_type_hints: true
    - avoid_blocking_calls_in_async: true
    - require_timeouts_for_network_io: true
    - secrets_never_in_code_or_logs: true
  verification:
    - ensure_ci_passes: true
    - ensure_coverage_threshold: 80
  review:
    - check_api_contracts: true
    - verify_db_migrations: true
```

## GitHub Workflow Example: Lint + Test Automation
### Trigger Conditions
- On pull requests to `main` or `release/*`
- On pushes to `main` or `develop`

### Quality Gate Workflow
```yaml
name: Quality Gate
on:
  pull_request:
    branches: ["main", "release/*"]
  push:
    branches: ["main", "develop"]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Lint
        run: |
          flake8 app
          black --check app
          isort --check-only app
      - name: Tests
        run: pytest --cov=app --cov-fail-under=80
```

## Semantic Release and Version Tagging
### Best Practices
- Use conventional commits to drive release notes.
- Automate version bumps based on commit types.
- Tag releases with `vX.Y.Z` and annotate with changelogs.

### Example Release Workflow
```yaml
name: Release
on:
  push:
    branches: ["main"]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install semantic-release
        run: npm install -g semantic-release @semantic-release/changelog @semantic-release/git
      - name: Run semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: semantic-release
```

## Security and Dependency Scanning
### Best Practices
- Scan dependencies on every PR.
- Fail builds on critical vulnerabilities.
- Periodically update dependency baselines.

### Example Security Workflow
```yaml
name: Security Scan
on:
  pull_request:
  schedule:
    - cron: "0 3 * * 1"

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install pip-audit
        run: pip install pip-audit
      - name: Dependency scan
        run: pip-audit -r requirements.txt
```

## Contributor Guidelines
### Proposing Changes
- Open a PR with a clear summary and scope.
- Link related issues or strategy tickets.
- Include test coverage evidence.

### Review Criteria
- Tests and linting must pass.
- No hardcoded secrets or unsafe defaults.
- Changes preserve deterministic execution and risk controls.

### Validation Process
- Validate strategy behavior in paper trading first.
- Run regression tests for trade execution paths.
- Review logs and metrics for anomalies.

## Troubleshooting and Optimization
- **Flaky tests:** stabilize by removing time-based dependencies or mocking exchange responses.
- **Lint failures:** run formatting locally before committing.
- **Performance regressions:** profile hot paths and ensure batch operations are used.
- **Async deadlocks:** confirm all awaits resolve and use timeouts.

## Maintenance Schedule
- **Monthly:** review workflows, dependency scans, and coverage thresholds.
- **Quarterly:** validate instruction sets for Copilot/Codex against new standards.
- **After major releases:** update the guide to reflect new architecture or tooling.

## Closing Note
Standardizing Copilot and Codex behavior strengthens the reliability, performance, and safety of the Trading Bot Swarm ecosystem. Following this guide ensures consistent excellence across all contributions.
