# Code Purge

Code Purge is an agent skill for finding and safely removing code that no longer serves a project. It combines static analysis with manual review, creates a non-destructive backup, asks for approval before editing, and runs the project's tests after cleanup.

## What It Finds

- Unused imports, variables, functions, classes, and exports
- Files that language-aware tools identify as unreferenced
- Unused project dependencies
- Duplicated code that can be consolidated
- Complex functions that are candidates for focused refactoring
- Dead branches and stale code markers that need manual review

Static analysis is treated as evidence, not proof. Framework callbacks, reflection, configuration-driven references, plugin registration, and public APIs are reviewed before anything is removed.

## How It Works

Code Purge follows five phases:

1. **Analyze:** Detect the project's languages and run available static-analysis tools.
2. **Report:** Show findings with confidence, severity, file paths, and line numbers.
3. **Confirm:** Ask which categories or individual findings may be changed.
4. **Backup and clean:** Create an external snapshot, then make only the approved changes.
5. **Verify:** Run detected test suites and report whether the cleanup passed, failed, or could not be verified.

Code Purge does not stage, stash, reset, or commit the target repository. Backups are stored outside the project under `${XDG_STATE_HOME:-$HOME/.local/state}/code-purge/` by default.

## Example Requests

Ask your agent to use the skill with requests such as:

```text
Use Code Purge to analyze this repository for dead code. Report findings only.
```

```text
Find unused imports and dependencies, then ask me before removing anything.
```

```text
Clean up high-confidence dead code, but skip public APIs and migration files.
```

```text
Find duplicated validation logic and propose the smallest safe consolidation.
```

## Supported Projects

The bundled analyzer detects Python, JavaScript, TypeScript, Go, Rust, Ruby, Java, PHP, C#, C, and C++ source files.

Built-in integrations include:

- Python: `vulture` and `pyflakes`
- JavaScript and TypeScript: project-local `knip`
- Duplicate detection: project-local `jscpd`
- Test verification: pytest, Jest, Vitest, Mocha, Go, Cargo, RSpec, Maven, and Gradle

Tools are optional. Missing tools are reported as warnings instead of being downloaded or executed automatically.

## Optional Tool Setup

Install only the tools relevant to the target project. Prefer development dependencies or an isolated Python environment.

```bash
# Python analysis and cleanup
python3 -m pip install vulture pyflakes autoflake radon lizard

# JavaScript and TypeScript analysis
npm install --save-dev knip jscpd
```

See [`references/tools.md`](references/tools.md) for additional language-specific tools.

## Manual Commands

The skill normally runs these scripts through an agent, but they can also be used directly.

```bash
# Human-readable analysis
python3 scripts/analyze.py /path/to/project --summary

# Machine-readable analysis
python3 scripts/analyze.py /path/to/project --json

# Non-destructive backup
bash scripts/backup.sh /path/to/project

# Auto-detect and run tests
bash scripts/run_tests.sh /path/to/project
```

`run_tests.sh` uses these exit codes:

- `0`: At least one detected test suite ran and passed.
- `1`: One or more test suites failed.
- `2`: No test suite could be run, so the cleanup remains unverified.

Set `CODE_PURGE_BACKUP_ROOT` to choose a different backup location.

```bash
CODE_PURGE_BACKUP_ROOT=/safe/backups bash scripts/backup.sh /path/to/project
```

## Safety Guarantees

- No cleanup starts before the user approves its scope.
- A backup is created before files are changed.
- The backup process preserves the working tree and staging area.
- Unused-file decisions require language-aware evidence and manual checks.
- Unpinned packages are never downloaded through `npx` during analysis.
- Existing user changes are not reverted or overwritten.
- A test result is only called successful when a test suite actually ran.

## Limitations

No static analyzer can reliably see every runtime reference. Extra review is required for:

- Published packages and externally consumed APIs
- Dependency injection and dynamic imports
- Reflection, decorators, signals, callbacks, and plugin systems
- Templates, migrations, fixtures, generated files, and configuration-loaded paths
- Projects without meaningful tests or build checks

For these cases, Code Purge reports uncertainty and leaves the final removal decision to the user.

## Skill Contents

- [`SKILL.md`](SKILL.md): Agent workflow and safety rules
- [`scripts/analyze.py`](scripts/analyze.py): Static-analysis coordinator
- [`scripts/backup.sh`](scripts/backup.sh): Non-destructive project snapshot
- [`scripts/run_tests.sh`](scripts/run_tests.sh): Test-suite detection and execution
- [`references/patterns.md`](references/patterns.md): Removal and refactoring checklist
- [`references/tools.md`](references/tools.md): Tool reference by language
- [`tests/test_scripts.py`](tests/test_scripts.py): Regression coverage for bundled scripts
