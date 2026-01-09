# GitHub Copilot & Codex Configuration Guide (Trading Bot Swarm)

## Purpose and Scope

This guide defines a consistent, secure, and high-quality development baseline for the Trading Bot Swarm ecosystem when using GitHub Copilot and OpenAI Codex. Copilot acts as a **pair programmer** with strict behavioral rules: it must follow repo conventions, prioritize correctness and security, and defer to existing patterns. Codex is configured to enforce automation, safety, and workflow consistency across agents and contributors.

The scope covers:

- Configuration standards for Copilot and Codex.
- Testing, linting, code style, async patterns, security defaults, logging, observability, CI/CD, and version control practices.
- Examples of custom instructions and workflow automation.
- Best practices for release management and security scanning.
- Contributor expectations, review criteria, and maintenance cadence.

---

## Configuration Overview

### Testing & Quality Gates

- **Run tests and linters for all code changes.**
- **Ignore documentation-only changes** for automated test runs.
- **Prefer fast, focused test suites** (unit tests, smoke tests) for pre-merge; full regression runs on release branches.
- **Fail fast** when tests or linters fail.

### Linting & Code Style

- Enforce consistent formatting and linting across Python, JavaScript/TypeScript, and YAML.
- Use shared configuration files (e.g., `pyproject.toml`, `.eslintrc`, `.prettierrc`).
- Require Copilot and Codex to conform to established style and architectural conventions.

### Async Patterns

- Use structured concurrency patterns where supported.
- Prefer explicit cancellation and timeouts for async workflows.
- Avoid blocking operations in async code paths.

### Security Defaults

- Never log secrets or PII.
- Validate external inputs by default.
- Use least-privilege credentials in CI/CD.
- Require dependency pinning and signed releases.

### Logging & Observability

- Use structured logs (JSON) with consistent fields.
- Include correlation IDs in workflow and bot execution logs.
- Expose health checks and metrics for bot services.

### CI/CD Integration

- Integrate lint/test jobs into pull request checks.
- Require quality gates prior to merge.
- Run dependency scanning and SAST regularly.

### Version Control

- Enforce semantic commits.
- Use release tags for all production deployments.
- Require pull requests for mainline changes.

---

## Custom Instruction Behavior (Codex & Copilot)

### Example Rules (Human-Readable)

- Always prefer repository code patterns over novel implementations.
- Run unit tests and linters for any code change.
- Skip tests for documentation-only changes.
- Use explicit timeouts for API calls.
- Prohibit secret leakage in logs.

### Conceptual YAML Instructions (Full Template)

```yaml
copilot:
  role: pair-programmer
  behavior:
    - follow_repo_conventions
    - prioritize_security_and_correctness
    - avoid_speculative_changes
    - prefer_existing_patterns
  quality:
    tests_required: true
    skip_tests_for_docs_only: true
    lint_required: true
  coding:
    async_patterns:
      - avoid_blocking_in_async
      - enforce_timeouts
    security:
      - no_secrets_in_logs
      - validate_external_inputs
      - least_privilege_credentials
    logging:
      format: json
      include_correlation_id: true

codex:
  role: automation-enforcer
  behavior:
    - apply_quality_gates
    - enforce_ci_policy
    - reject_unvalidated_changes
  checks:
    require_tests_for_code_changes: true
    skip_for_docs_only: true
    require_lint: true
  workflows:
    - run_unit_tests
    - run_lint
    - run_security_scans
```

---

## GitHub Workflow Example: Lint & Test Automation

### Trigger Conditions

- Pull requests targeting `main` or `release/*`.
- Pushes to `main`.
- Ignore documentation-only changes in `/docs` and `*.md` files.

### Example Workflow (Quality Gate)

```yaml
name: quality-gate

on:
  pull_request:
    branches: ["main", "release/*"]
    paths-ignore:
      - "docs/**"
      - "**/*.md"
  push:
    branches: ["main"]
    paths-ignore:
      - "docs/**"
      - "**/*.md"

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
      - name: Run linters
        run: make lint
      - name: Run tests
        run: make test
```

---

## Best Practices: Semantic Release & Version Tagging

### Semantic Release (Example)

```yaml
name: semantic-release

on:
  push:
    branches: ["main"]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install deps
        run: npm ci
      - name: Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: npx semantic-release
```

### Version Tagging

- Tags follow `vMAJOR.MINOR.PATCH` (e.g., `v1.4.2`).
- Tags are immutable and must reference a tested commit.

---

## Security & Dependency Scanning

### Example (Dependency Review + SAST)

```yaml
name: security-scan

on:
  schedule:
    - cron: "0 6 * * 1"
  pull_request:
    branches: ["main"]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Dependency Review
        uses: actions/dependency-review-action@v4
      - name: CodeQL Init
        uses: github/codeql-action/init@v3
        with:
          languages: python
      - name: CodeQL Analyze
        uses: github/codeql-action/analyze@v3
```

---

## Contributor Guidelines

### Proposing Changes

- Open an issue describing the goal, risks, and testing plan.
- Submit a pull request with:
  - A clear summary.
  - Test and lint output.
  - Security implications (if any).

### Review Criteria

- Conformance with coding standards and patterns.
- Test coverage and lint compliance.
- Safe handling of secrets and external inputs.

### Validation Process

- All CI checks must pass.
- Manual validation is required for changes to trading logic, execution paths, or risk controls.

---

## Troubleshooting & Optimization

- **Slow tests:** split unit and integration tests; run unit tests by default.
- **Lint noise:** align local tooling versions with CI.
- **Flaky async behavior:** enforce timeouts and retries with backoff.

---

## Maintenance Schedule

- **Monthly:** review CI/CD workflows and security scans.
- **Quarterly:** refresh Copilot/Codex instruction templates.
- **Release-cycle:** update workflow rules, testing requirements, and dependency baselines.

---

## Closing Note

The goal of this guide is to standardize excellence and strengthen the reliability, performance, and safety of the Trading Bot Swarm ecosystem through disciplined automation and consistent engineering practices.
