"""Command line interface. Exit codes: 0 clean, 1 drift (--fail-on-drift), 2 usage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from protodrift import SEVERITIES, __version__
from protodrift.scan import (
    Finding,
    discover,
    language_of,
    load_config,
    map_stub,
    scan,
    stub_stem,
)

_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proto-drift",
        description="Detect drift between .proto sources and committed generated stubs.",
    )
    parser.add_argument("--version", action="version", version=f"proto-drift {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_cmd = sub.add_parser("scan", help="scan a repo for proto drift")
    scan_cmd.add_argument("path", nargs="?", default=".", help="repo root (default: current directory)")
    scan_cmd.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    scan_cmd.add_argument("--fail-on-drift", action="store_true", help="exit 1 when drift is found")

    check_cmd = sub.add_parser("check", help="check one .proto against one SDK directory")
    check_cmd.add_argument("--proto", required=True, help=".proto file, relative to --root")
    check_cmd.add_argument("--sdk", required=True, help="SDK directory, relative to --root")
    check_cmd.add_argument("--root", default=".", help="repo root (default: current directory)")
    check_cmd.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    check_cmd.add_argument("--fail-on-drift", action="store_true", help="exit 1 when drift is found")
    return parser


def _sorted(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (_ORDER[f.severity], f.type, f.proto, f.stub))


def _render(findings: list[Finding], root: Path) -> str:
    findings = _sorted(findings)
    if not findings:
        return "No proto drift detected."
    lines = [
        f"{f.severity:<8} {f.type:<12} {f.proto or '(deleted .proto)'}"
        f"{' -> ' + f.stub if f.stub else ' (no generated stub)'}\n           {f.detail}"
        for f in findings
    ]
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary = ", ".join(f"{counts[s]} {s}" for s in sorted(counts, key=lambda s: _ORDER[s]))
    lines.append(f"\n{len(findings)} finding(s): {summary}")
    return "\n".join(lines)


def _to_json(findings: list[Finding], root: Path) -> dict:
    return {
        "tool": "proto-drift",
        "version": __version__,
        "root": str(root),
        "drift_count": len(findings),
        "findings": [
            {"type": f.type, "severity": f.severity, "language": f.language,
             "proto": f.proto, "stub": f.stub, "detail": f.detail}
            for f in _sorted(findings)
        ],
    }


def _gates(cfg: dict) -> dict[str, bool]:
    fail = cfg.get("fail", {})
    return {k: bool(fail.get(f"on_{k}", True)) for k in SEVERITIES}


def _exit_code(findings: list[Finding], cfg: dict, fail_on_drift: bool) -> int:
    """`--fail-on-drift` exits 1 when a *gated* type was reported. One place, so
    scan and check can never disagree about what the `[fail]` config means."""
    if not fail_on_drift:
        return 0
    gates = _gates(cfg)
    return 1 if any(gates.get(f.type, True) for f in findings) else 0


def _must_exist(target: Path, label: str, want_dir: bool, shown: str) -> str | None:
    """One place decides what a missing or wrong-kind path prints, so scan and check agree."""
    if not target.exists():
        return f"proto-drift: {label} not found: {shown}"
    if target.is_dir() != want_dir:
        return f"proto-drift: {label} is not a {'directory' if want_dir else 'file'}: {shown}"
    return None


def _cmd_scan(args) -> int:
    root = Path(args.path)
    problem = _must_exist(root, "root", True, args.path)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    cfg = load_config(root)
    findings = scan(root, cfg)
    print(json.dumps(_to_json(findings, root.resolve()), indent=2) if args.json else _render(findings, root.resolve()))
    return _exit_code(findings, cfg, args.fail_on_drift)


def _cmd_check(args) -> int:
    root = Path(args.root).resolve()
    proto = root / args.proto
    sdk = root / args.sdk
    for label, target, want_dir in (("root", root, True), ("proto", proto, False), ("sdk", sdk, True)):
        problem = _must_exist(target, label, want_dir, getattr(args, label))
        if problem:
            print(problem, file=sys.stderr)
            return 2
    cfg = load_config(root)
    tree = discover(root, cfg)
    proto = proto.resolve()
    findings: list[Finding] = []
    mapped = 0
    undecidable = False
    for stub in tree.stubs:
        if sdk not in stub.parents:
            continue
        mapping = map_stub(tree, stub)
        if mapping.proto != proto:
            # An ambiguous stub whose stem could be this .proto proves a stub exists;
            # refusing to guess must not be reported as "no generated stub" (#14).
            undecidable |= mapping.ambiguous and stub_stem(stub.name) == proto.stem
            continue
        mapped += 1
        if proto.stat().st_mtime_ns > stub.stat().st_mtime_ns:
            findings.append(Finding("stale", SEVERITIES["stale"], language_of(stub) or "", proto.relative_to(root).as_posix(),
                                    stub.relative_to(root).as_posix(), "proto modified after stub"))
    if not mapped and not undecidable:
        findings.append(Finding("missing_sdk", SEVERITIES["missing_sdk"], "", proto.relative_to(root).as_posix(), "",
                                f"no generated stub for this proto under {args.sdk}"))
    print(json.dumps(_to_json(findings, root), indent=2) if args.json else _render(findings, root))
    return _exit_code(findings, cfg, args.fail_on_drift)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return _cmd_scan(args) if args.command == "scan" else _cmd_check(args)


if __name__ == "__main__":
    raise SystemExit(main())