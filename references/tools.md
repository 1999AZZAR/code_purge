# Code Purge — Tool Reference

## Python

| Tool | Purpose | Install | Command |
|------|---------|---------|---------|
| `vulture` | Dead functions, classes, variables | `pip install vulture` | `vulture . --min-confidence 80` |
| `pyflakes` | Unused imports, redefined names | `pip install pyflakes` | `pyflakes .` |
| `autoflake` | Auto-remove unused imports | `pip install autoflake` | `autoflake -r --in-place --remove-unused-variables --remove-all-unused-imports .` |
| `unimport` | Unused imports (more accurate) | `pip install unimport` | `unimport --check .` |
| `pylint` | Broad analysis incl. duplicates | `pip install pylint` | `pylint **/*.py --disable=all --enable=W0611,W0612,R0801` |

**Recommended stack**: `vulture` (dead code) + `autoflake --check` (imports) + `jscpd` (duplication)

## JavaScript / TypeScript

| Tool | Purpose | Install | Command |
|------|---------|---------|---------|
| `knip` | Dead exports, unused files, unused deps | `npm i -g knip` | `knip --reporter json` |
| `ts-prune` | Unused TS exports only | `npm i -g ts-prune` | `ts-prune` |
| `depcheck` | Unused npm dependencies | `npm i -g depcheck` | `depcheck` |
| `eslint` | Unused vars/imports (with plugins) | project-specific | `eslint --rule 'no-unused-vars: error'` |
| `unimport` | Auto unused import removal | `npm i -g unimport` | programmatic API |

**Recommended stack**: `knip` (comprehensive) + `jscpd` (duplication)

## All Languages — Duplicate Detection

| Tool | Purpose | Install | Command |
|------|---------|---------|---------|
| `jscpd` | Copy-paste detection, multi-language | `npm i -g jscpd` | `jscpd . --min-lines 5 --min-tokens 50` |
| `PMD CPD` | Java/C++/JS duplicate detection | JVM required | `cpd --minimum-tokens 50 --files src/` |
| `SonarQube` | Enterprise-grade (incl. cognitive complexity) | Docker | `sonar-scanner` |

## Go

```bash
# Built-in: unused imports are compile errors
go build ./...          # fails on unused imports
go vet ./...            # additional checks
staticcheck ./...       # advanced dead code (go install honnef.co/go/tools/cmd/staticcheck@latest)
```

## Rust

```bash
cargo clippy -- -D warnings          # unused code warnings as errors
cargo +nightly udeps                 # unused dependencies
```

## Ruby

```bash
gem install rubocop
rubocop --only Lint/UnusedMethodArgument,Lint/UnusedBlockArgument
```

## Complexity Analysis

| Tool | Languages | Purpose |
|------|-----------|---------|
| `radon` | Python | Cyclomatic + maintainability index |
| `lizard` | 20+ languages | Function complexity |
| `code-climate` | Multi | Cognitive complexity |
| `eslint complexity` | JS/TS | Max complexity rule |

**Radon usage:**
```bash
pip install radon
radon cc . -a -nb          # cyclomatic complexity, only B+ (complex) blocks
radon mi . -nb             # maintainability index, only low-grade files
```

**Lizard usage:**
```bash
pip install lizard
lizard . --CCN 10 --length 50    # flag functions with CC>10 or >50 lines
```

## File-level unused detection

For projects without a bundler/import graph, use `analyze.py`'s heuristic scanner.
For large monorepos, consider:
```bash
# Find files never imported/required (grep-based, Node projects)
find src -name "*.js" -o -name "*.ts" | while read f; do
  stem=$(basename "$f" | sed 's/\.[^.]*$//')
  if ! grep -rq "$stem" src/ --include="*.{js,ts}" --exclude="$f"; then
    echo "POSSIBLY UNUSED: $f"
  fi
done
```

## Auto-fix tools (use with caution — always backup first)

| Tool | What it auto-fixes |
|------|--------------------|
| `autoflake --in-place` | Python unused imports |
| `isort` | Python import organization |
| `eslint --fix` | JS/TS unused vars (with `--fix-type suggestion`) |
| `knip --fix` (experimental) | JS/TS dead exports removal |
| Manual + AI | Complex refactors, simplified logic |
