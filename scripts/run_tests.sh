#!/usr/bin/env bash
# Auto-detects and runs the project test suite.
# Usage: run_tests.sh [project_root]
# Exit code: 0 = all passed, non-zero = failures detected

set -uo pipefail

PROJECT_ROOT="${1:-.}"
cd "$PROJECT_ROOT"

run_and_report() {
  local label="$1"; shift
  echo "→ Running: $label"
  if "$@"; then
    echo "✔ $label passed"
    return 0
  else
    echo "✘ $label FAILED (exit $?)"
    return 1
  fi
}

FAILED=0

# ── Python ────────────────────────────────────────────────────────────────────
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] || [ -f "setup.cfg" ] || find . -name "test_*.py" -maxdepth 4 | grep -q .; then
  if command -v pytest &>/dev/null; then
    run_and_report "pytest" pytest -x -q --tb=short || FAILED=1
  elif command -v python3 &>/dev/null && python3 -m pytest --version &>/dev/null 2>&1; then
    run_and_report "python3 -m pytest" python3 -m pytest -x -q --tb=short || FAILED=1
  fi
fi

# ── Node / JS / TS ────────────────────────────────────────────────────────────
if [ -f "package.json" ]; then
  TEST_CMD=$(node -e "try{const p=require('./package.json');console.log(p.scripts&&p.scripts.test||'')}catch(e){}" 2>/dev/null || true)
  if [ -n "$TEST_CMD" ] && [ "$TEST_CMD" != "echo \"Error: no test specified\" && exit 1" ]; then
    if command -v npm &>/dev/null; then
      run_and_report "npm test" npm test -- --passWithNoTests 2>/dev/null || \
      run_and_report "npm test" npm test || FAILED=1
    fi
  elif command -v npx &>/dev/null; then
    # Try common test runners
    for runner in vitest jest mocha; do
      if [ -f "node_modules/.bin/$runner" ] || npx --no "$runner" --version &>/dev/null 2>&1; then
        run_and_report "$runner" npx "$runner" --passWithNoTests 2>/dev/null || \
        run_and_report "$runner" npx "$runner" || FAILED=1
        break
      fi
    done
  fi
fi

# ── Go ────────────────────────────────────────────────────────────────────────
if [ -f "go.mod" ] && command -v go &>/dev/null; then
  run_and_report "go test" go test ./... || FAILED=1
fi

# ── Rust ──────────────────────────────────────────────────────────────────────
if [ -f "Cargo.toml" ] && command -v cargo &>/dev/null; then
  run_and_report "cargo test" cargo test || FAILED=1
fi

# ── Ruby ──────────────────────────────────────────────────────────────────────
if [ -f "Gemfile" ] && command -v bundle &>/dev/null; then
  if [ -f "spec/spec_helper.rb" ] || [ -d "spec" ]; then
    run_and_report "rspec" bundle exec rspec || FAILED=1
  elif [ -d "test" ]; then
    run_and_report "rake test" bundle exec rake test || FAILED=1
  fi
fi

# ── Java / Maven / Gradle ─────────────────────────────────────────────────────
if [ -f "pom.xml" ] && command -v mvn &>/dev/null; then
  run_and_report "mvn test" mvn test -q || FAILED=1
elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
  if [ -f "gradlew" ]; then
    run_and_report "gradlew test" ./gradlew test || FAILED=1
  elif command -v gradle &>/dev/null; then
    run_and_report "gradle test" gradle test || FAILED=1
  fi
fi

if [ "$FAILED" -ne 0 ]; then
  echo ""
  echo "RESULT: One or more test suites FAILED — review before proceeding."
  exit 1
else
  echo ""
  echo "RESULT: All detected test suites passed."
  exit 0
fi
