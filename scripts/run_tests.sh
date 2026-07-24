#!/usr/bin/env bash
# Auto-detects and runs the project test suite.
# Usage: run_tests.sh [project_root]
# Exit code: 0 = all passed, non-zero = failures detected

set -uo pipefail

PROJECT_ROOT="${1:-.}"
cd "$PROJECT_ROOT" || exit 2

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
DETECTED=0
RAN=0

# ── Python ────────────────────────────────────────────────────────────────────
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ] || [ -f "setup.cfg" ] || find . -name "test_*.py" -maxdepth 4 | grep -q .; then
  DETECTED=1
  if command -v pytest &>/dev/null; then
    RAN=$((RAN + 1))
    run_and_report "pytest" pytest -x -q --tb=short || FAILED=1
  elif command -v python3 &>/dev/null && python3 -m pytest --version &>/dev/null 2>&1; then
    RAN=$((RAN + 1))
    run_and_report "python3 -m pytest" python3 -m pytest -x -q --tb=short || FAILED=1
  fi
fi

# ── Node / JS / TS ────────────────────────────────────────────────────────────
if [ -f "package.json" ]; then
  DETECTED=1
  TEST_CMD=$(node -e "try{const p=require('./package.json');console.log(p.scripts&&p.scripts.test||'')}catch(e){}" 2>/dev/null || true)
  if [ -n "$TEST_CMD" ] && [ "$TEST_CMD" != "echo \"Error: no test specified\" && exit 1" ]; then
    if command -v npm &>/dev/null; then
      RAN=$((RAN + 1))
      run_and_report "npm test" npm test || FAILED=1
    fi
  elif [ -d "node_modules/.bin" ]; then
    # Try common test runners
    for runner in vitest jest mocha; do
      if [ -x "node_modules/.bin/$runner" ]; then
        RAN=$((RAN + 1))
        if [ "$runner" = "mocha" ]; then
          run_and_report "$runner" "node_modules/.bin/$runner" || FAILED=1
        else
          run_and_report "$runner" "node_modules/.bin/$runner" --passWithNoTests || FAILED=1
        fi
        break
      fi
    done
  fi
fi

# ── Go ────────────────────────────────────────────────────────────────────────
if [ -f "go.mod" ]; then
  DETECTED=1
  if command -v go &>/dev/null; then
    RAN=$((RAN + 1))
    run_and_report "go test" go test ./... || FAILED=1
  fi
fi

# ── Rust ──────────────────────────────────────────────────────────────────────
if [ -f "Cargo.toml" ]; then
  DETECTED=1
  if command -v cargo &>/dev/null; then
    RAN=$((RAN + 1))
    run_and_report "cargo test" cargo test || FAILED=1
  fi
fi

# ── Ruby ──────────────────────────────────────────────────────────────────────
if [ -f "Gemfile" ]; then
  DETECTED=1
  if command -v bundle &>/dev/null && { [ -f "spec/spec_helper.rb" ] || [ -d "spec" ]; }; then
    RAN=$((RAN + 1))
    run_and_report "rspec" bundle exec rspec || FAILED=1
  elif command -v bundle &>/dev/null && [ -d "test" ]; then
    RAN=$((RAN + 1))
    run_and_report "rake test" bundle exec rake test || FAILED=1
  fi
fi

# ── Java / Maven / Gradle ─────────────────────────────────────────────────────
if [ -f "pom.xml" ]; then
  DETECTED=1
  if command -v mvn &>/dev/null; then
    RAN=$((RAN + 1))
    run_and_report "mvn test" mvn test -q || FAILED=1
  fi
elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
  DETECTED=1
  if [ -f "gradlew" ]; then
    RAN=$((RAN + 1))
    run_and_report "gradlew test" ./gradlew test || FAILED=1
  elif command -v gradle &>/dev/null; then
    RAN=$((RAN + 1))
    run_and_report "gradle test" gradle test || FAILED=1
  fi
fi

if [ "$RAN" -eq 0 ]; then
  echo ""
  if [ "$DETECTED" -eq 1 ]; then
    echo "RESULT: Test configuration detected, but no available runner executed."
  else
    echo "RESULT: No test suite detected; verification was not performed."
  fi
  exit 2
elif [ "$FAILED" -ne 0 ]; then
  echo ""
  echo "RESULT: One or more test suites FAILED — review before proceeding."
  exit 1
else
  echo ""
  echo "RESULT: All detected test suites passed."
  exit 0
fi
