# Code Purge — Dead Code Patterns & Analysis Checklist

## Table of Contents
1. [Dead Code Patterns](#dead-code-patterns)
2. [Duplicate Logic Patterns](#duplicate-logic-patterns)
3. [Unused File Patterns](#unused-file-patterns)
4. [Complexity Patterns](#complexity-patterns)
5. [Safe Removal Checklist](#safe-removal-checklist)
6. [Refactoring Heuristics](#refactoring-heuristics)

---

## Dead Code Patterns

### Definitively dead (safe to remove)
- Functions/classes/methods with zero call sites, zero imports
- Variables assigned but never read
- Imports never referenced in the file body
- `if False:` / `if 0:` blocks
- Code after `return`/`raise`/`sys.exit()` at the same scope level
- Commented-out code blocks (>3 lines) that have been untouched for >6 months (check git blame)
- Conditional branches guarded by constants (`if DEBUG and False:`)

### Conditionally dead (verify before removing)
- Functions only called by other dead functions
- Exports only imported by unused files
- Methods only invoked via reflection/dynamic dispatch — check for `getattr`, `__getattribute__`, decorator patterns
- Public API surface: check if consumers exist outside the repo (package users)
- Event handlers and callbacks — grep for event name strings before removing
- `__all__` exports — explicitly declared public surface

### Never remove without deep analysis
- `__init__` / `__new__` / `__del__` — Python lifecycle hooks
- Entry points listed in `setup.py` / `pyproject.toml` / `package.json` `bin`
- Plugin registration callbacks (Django signals, Flask extensions, pytest fixtures)
- `@app.route`, `@router.get` and similar framework decorators
- Functions referenced by string in config files (celery tasks, etc.)
- Serialization/deserialization methods (may be called by frameworks)

---

## Duplicate Logic Patterns

### High-confidence duplicates (consolidate)
- Identical function bodies in different files (copy-paste, detected by jscpd)
- Near-identical utility functions that differ only in variable names
- Multiple implementations of the same validation/transformation logic
- Repeated `try/except` blocks with identical error handling

### Consolidation targets
- `utils.py` / `helpers.js` files in multiple modules with overlapping functions
- Multiple date/string/array formatting functions doing the same thing
- Repeated DB query patterns that could be a repository method
- Copy-pasted test setup code → `conftest.py` / `beforeEach` fixtures

### False positive duplicates (leave alone)
- Short, simple functions (≤5 lines) that happen to look similar
- Domain-specific logic that coincidentally resembles general logic
- Test data builders — each test may need unique setup even if structurally similar

---

## Unused File Patterns

### Likely unused
- Files with no imports from anywhere in the project
- Migration files beyond the "squash point" in Django/Rails (check project policy)
- Generated files checked into git (regenerate from source instead)
- Backup files (`*.bak`, `*.orig`, `*.old`, `file_copy.py`)
- Experimental/draft files (`draft_*.py`, `*_v2.py`, `*_new.js`)
- Empty `__init__.py` in Python 3 packages that don't need them

### Verify before removing
- Config files — may be loaded by name at runtime
- Type stubs (`.pyi`, `.d.ts`) — may be consumed by tools not visible to import analysis
- Locale/i18n files — referenced by string keys
- Template files — loaded by name/path, not import
- Test fixtures — loaded by file path
- `Dockerfile`, `*.yml` CI configs — used by external systems

---

## Complexity Patterns

### Target for simplification
| Pattern | Threshold | Approach |
|---------|-----------|---------|
| Cyclomatic complexity | CC > 10 | Extract sub-functions, early returns |
| Function length | > 50 lines | Single-responsibility split |
| Nesting depth | > 4 levels | Invert conditions, extract guards |
| Parameter count | > 5 params | Parameter object / options dict |
| Long if/elif chains | > 7 branches | Dict dispatch / polymorphism |
| God classes | > 500 lines, > 20 methods | Decompose by responsibility |
| Feature envy | Method uses another class more than its own | Move method |

### Refactoring approaches
- **Long functions**: Extract until each function does one thing, named clearly enough that comments are unnecessary
- **Deep nesting**: Apply "early return" / "guard clause" pattern — handle error/edge cases first and return, keep happy path unindented
- **Repeated conditionals**: Extract condition into a well-named boolean variable or predicate function
- **Parallel data structures**: Combine parallel arrays/dicts into a list of objects/dataclasses

---

## Safe Removal Checklist

Before removing any code:
- [ ] Run `analyze.py` and confirm the item appears in the report
- [ ] Check git blame — when was this last touched? Who touched it?
- [ ] Search for string-based references: `grep -r "function_name"` — dynamic calls, eval, reflection
- [ ] Search config files (YAML, JSON, TOML) for the symbol name
- [ ] Check if the file/function is in `__all__`, exported in an index file, or in public API docs
- [ ] Check if referenced in tests (even if the code is "unused" in production)
- [ ] Confirm backup exists before proceeding

After removing:
- [ ] Run full test suite (`run_tests.sh`)
- [ ] Build the project (compilation errors catch some missed references)
- [ ] Run the application's smoke test / health check if applicable
- [ ] Review diff before committing — no unintended changes

---

## Refactoring Heuristics

### When to refactor vs. remove
- If a function does useful work but is currently unreachable → fix the call site, don't delete
- If a module has 60% dead code → refactor the live part into a new module, delete the old
- If complexity > threshold but function is business-critical → add tests first, then refactor

### Incremental strategy for large cleanups
1. Run analysis, export JSON report
2. Sort findings by severity (high first)
3. Address dead code in leaf modules first (no dependents)
4. Work inward toward core/shared modules
5. Commit in small logical batches: "remove dead utils in auth module"
6. Run tests after each batch — catch regressions early

### What NOT to clean in one pass
- Don't mix dead-code removal with feature refactors in the same commit
- Don't remove a function and change its callers in the same commit
- Don't restructure file/directory layout in the same pass as logic removal
