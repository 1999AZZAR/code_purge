#!/usr/bin/env python3
"""
Universal dead-code analyzer for code-purge skill.

Detects languages present, runs appropriate static-analysis tools,
and outputs a structured JSON report to stdout.

Usage:
    python3 analyze.py [project_root] [--json|--summary]
    python3 analyze.py . --json > report.json
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class Finding:
    category: str          # dead_code | duplicate | unused_import | unused_file | complexity
    severity: str          # high | medium | low
    file: str
    line: Optional[int]
    description: str
    tool: str


@dataclass
class Report:
    project_root: str
    languages: list[str]
    findings: list[Finding] = field(default_factory=list)
    tool_errors: list[str] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def add_error(self, msg: str) -> None:
        self.tool_errors.append(msg)

    def build_summary(self) -> None:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.category] = counts.get(f.category, 0) + 1
        self.summary = {
            "total": len(self.findings),
            "by_category": counts,
            "by_severity": {
                s: sum(1 for f in self.findings if f.severity == s)
                for s in ("high", "medium", "low")
            },
        }


# ── Language detection ────────────────────────────────────────────────────────

EXT_MAP = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go",
    ".rb": "ruby",
    ".java": "java",
    ".rs": "rust",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".c": "c", ".h": "c",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".cache", ".next", ".nuxt", "coverage",
    ".code-purge-backups",
}


def detect_languages(root: Path) -> list[str]:
    counts: dict[str, int] = {}
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        lang = EXT_MAP.get(p.suffix.lower())
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return sorted(counts, key=lambda k: -counts[k])


# ── Tool runners ──────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return -1, "", f"tool not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", f"timeout: {cmd[0]}"


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def _project_node_tool(root: str, name: str) -> str | None:
    tool = Path(root) / "node_modules" / ".bin" / name
    return str(tool) if tool.is_file() and tool.stat().st_mode & 0o111 else None


def run_vulture(root: str, report: Report) -> None:
    """Python dead code via vulture."""
    if not _tool_available("vulture"):
        report.add_error("vulture not installed (pip install vulture)")
        return
    _, out, _ = _run(["vulture", ".", "--min-confidence", "80"], root)
    if not out:
        return
    for line in out.splitlines():
        # format: path/file.py:12: unused function 'foo' (confidence: 90%)
        m = re.match(r"^(.+):(\d+):\s+(.+)\s+\(confidence:\s*(\d+)%\)$", line)
        if m:
            fpath, lineno, desc, conf = m.groups()
            severity = "high" if int(conf) >= 90 else "medium"
            report.add(Finding(
                category="dead_code",
                severity=severity,
                file=fpath,
                line=int(lineno),
                description=desc.strip(),
                tool="vulture",
            ))


def run_pyflakes(root: str, report: Report) -> None:
    """Python unused imports via pyflakes."""
    if not _tool_available("pyflakes"):
        report.add_error("pyflakes not installed (pip install pyflakes)")
        return
    _, out, err = _run(["pyflakes", "."], root)
    combined = out + err
    for line in combined.splitlines():
        m = re.match(r"^(.+):(\d+):\d+\s+'(.+)' imported but unused$", line)
        if m:
            fpath, lineno, sym = m.groups()
            report.add(Finding(
                category="unused_import",
                severity="low",
                file=fpath,
                line=int(lineno),
                description=f"'{sym}' imported but unused",
                tool="pyflakes",
            ))
        # redefined
        m2 = re.match(r"^(.+):(\d+):\d+\s+redefinition of unused '(.+)'", line)
        if m2:
            fpath, lineno, sym = m2.groups()
            report.add(Finding(
                category="dead_code",
                severity="medium",
                file=fpath,
                line=int(lineno),
                description=f"redefinition of unused '{sym}'",
                tool="pyflakes",
            ))


def run_knip(root: str, report: Report) -> None:
    """JS/TS dead exports and unused files via knip."""
    tool = _project_node_tool(root, "knip")
    if tool is None:
        report.add_error("knip not installed; use the project's pinned knip executable")
        return
    code, out, err = _run([tool, "--reporter", "json"], root, timeout=180)
    if code not in (0, 1):
        report.add_error(f"knip failed: {err.strip() or f'exit {code}'}")
        return
    if not out.strip():
        return
    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        report.add_error(f"knip returned invalid JSON: {exc}")
        return

    # Unused files
    for f in data.get("files", []):
        report.add(Finding(
            category="unused_file",
            severity="medium",
            file=f,
            line=None,
            description="file has no imports from the rest of the project",
            tool="knip",
        ))
    # Unused exports
    for item in data.get("exports", []):
        report.add(Finding(
            category="dead_code",
            severity="low",
            file=item.get("filePath", ""),
            line=item.get("line"),
            description=f"unused export: {item.get('symbol', '')}",
            tool="knip",
        ))
    # Unused dependencies
    for dep in data.get("dependencies", {}).get("unused", []):
        report.add(Finding(
            category="unused_import",
            severity="medium",
            file="package.json",
            line=None,
            description=f"unused dependency: {dep}",
            tool="knip",
        ))


def run_jscpd(root: str, report: Report) -> None:
    """Duplicate code detection via jscpd."""
    tool = _project_node_tool(root, "jscpd")
    if tool is None:
        report.add_error("jscpd not installed; use the project's pinned jscpd executable")
        return
    with tempfile.TemporaryDirectory(prefix="code-purge-jscpd-") as output_dir:
        cmd = [tool, ".", "--reporters", "json", "--output", output_dir, "--silent"]
        code, _, err = _run(cmd, root, timeout=180)
        if code not in (0, 1):
            report.add_error(f"jscpd failed: {err.strip() or f'exit {code}'}")
            return

        report_file = Path(output_dir) / "jscpd-report.json"
        if not report_file.exists():
            report.add_error("jscpd did not produce a JSON report")
            return
        try:
            data = json.loads(report_file.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            report.add_error(f"unable to read jscpd report: {exc}")
            return

    for clone in data.get("duplicates", []):
        first = clone.get("firstFile", {})
        second = clone.get("secondFile", {})
        lines = clone.get("lines", 0)
        severity = "high" if lines >= 20 else "medium" if lines >= 10 else "low"
        report.add(Finding(
            category="duplicate",
            severity=severity,
            file=first.get("name", ""),
            line=first.get("start"),
            description=(
                f"{lines}-line duplicate block also at "
                f"{second.get('name','')}:{second.get('start','')}"
            ),
            tool="jscpd",
        ))


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    root_arg = sys.argv[1] if len(sys.argv) > 1 else "."
    mode = sys.argv[2] if len(sys.argv) > 2 else "--json"
    root = Path(root_arg).resolve()

    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    langs = detect_languages(root)
    report = Report(project_root=str(root), languages=langs)

    print(f"Detected languages: {', '.join(langs) or 'none'}", file=sys.stderr)
    print(f"Running analysis on: {root}", file=sys.stderr)

    if "python" in langs:
        print("  → vulture (Python dead code)...", file=sys.stderr)
        run_vulture(str(root), report)
        print("  → pyflakes (Python unused imports)...", file=sys.stderr)
        run_pyflakes(str(root), report)

    if "javascript" in langs or "typescript" in langs:
        print("  → knip (JS/TS dead exports + unused files)...", file=sys.stderr)
        run_knip(str(root), report)

    if langs:
        print("  → jscpd (duplicate code)...", file=sys.stderr)
        run_jscpd(str(root), report)

    report.build_summary()

    if mode == "--summary":
        print(f"\n=== Code Purge Analysis: {root} ===")
        print(f"Languages: {', '.join(langs) or 'none'}")
        print(f"Total findings: {report.summary.get('total', 0)}")
        for cat, count in report.summary.get("by_category", {}).items():
            print(f"  {cat}: {count}")
        if report.tool_errors:
            print("\nTool warnings:")
            for e in report.tool_errors:
                print(f"  ⚠ {e}")
        print("\nTop findings:")
        high = [f for f in report.findings if f.severity == "high"][:10]
        for f in high:
            print(f"  [{f.category}] {f.file}:{f.line or '?'} — {f.description}")
    else:
        print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
