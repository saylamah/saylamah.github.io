#!/usr/bin/env python3
"""
Step 1 — Normalize the present-day professional identity on the five principal
website pages only.

Default mode is a dry run. Use --apply to write changes.

This script intentionally does NOT modify:
- papers/
- publications/ article pages
- historical publication records
- repository files other than the five principal HTML pages
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

TARGET_FILES = (
    "index.html",
    "selected-work.html",
    "research-tools.html",
    "publications.html",
    "about-cv.html",
)

REPLACEMENTS = (
    ("Prof. Dr. Ahmad Saylam", "Dr. Ahmad Saylam"),
    ('"honorificPrefix": "Prof. Dr."', '"honorificPrefix": "Dr."'),
)

OLD_MARKERS = (
    "Prof. Dr. Ahmad Saylam",
    '"honorificPrefix": "Prof. Dr."',
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def all_file_hashes(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".git/") or rel.startswith("_identity_backup_"):
            continue
        if rel == "IDENTITY_PATCH_REPORT.md":
            continue
        result[rel] = sha256(path)
    return result


def validate_repo(root: Path) -> list[Path]:
    missing = [name for name in TARGET_FILES if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(
            "Run this script from the repository root. Missing: "
            + ", ".join(missing)
        )
    return [root / name for name in TARGET_FILES]


def patch_text(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    updated = text
    for old, new in REPLACEMENTS:
        counts[old] = updated.count(old)
        updated = updated.replace(old, new)
    return updated, counts


def validate_jsonld(text: str, filename: str) -> list[str]:
    """Validate all JSON-LD blocks that were already valid JSON before/after this patch."""
    warnings: list[str] = []
    marker = '<script type="application/ld+json">'
    start = 0
    block_no = 0
    while True:
        open_pos = text.find(marker, start)
        if open_pos < 0:
            break
        content_start = open_pos + len(marker)
        close_pos = text.find("</script>", content_start)
        if close_pos < 0:
            warnings.append(f"{filename}: unclosed JSON-LD script block")
            break
        block_no += 1
        payload = text[content_start:close_pos].strip()
        try:
            json.loads(payload)
        except json.JSONDecodeError as exc:
            warnings.append(
                f"{filename}: JSON-LD block {block_no} is not valid JSON "
                f"(pre-existing or unrelated issue): {exc}"
            )
        start = close_pos + len("</script>")
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize Prof. Dr. Ahmad Saylam to Dr. Ahmad Saylam "
                    "on the five principal website pages."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the verified changes. Without this flag, perform a dry run.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory).",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    try:
        target_paths = validate_repo(root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    before_tree = all_file_hashes(root)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = root / f"_identity_backup_{timestamp}"

    planned: dict[str, dict[str, object]] = {}
    patched_texts: dict[Path, str] = {}
    jsonld_warnings: list[str] = []

    total_replacements = 0
    for path in target_paths:
        original = path.read_text(encoding="utf-8")
        updated, counts = patch_text(original)
        file_total = sum(counts.values())
        total_replacements += file_total

        remaining = [marker for marker in OLD_MARKERS if marker in updated]
        if remaining:
            print(
                f"ERROR: old identity marker remains in {path.name}: {remaining}",
                file=sys.stderr,
            )
            return 3

        jsonld_warnings.extend(validate_jsonld(updated, path.name))
        patched_texts[path] = updated
        planned[path.name] = {
            "replacement_counts": counts,
            "total_replacements": file_total,
            "changed": original != updated,
            "sha256_before": sha256(path),
        }

    print("Step 1 identity normalization")
    print(f"Repository: {root}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    for name, info in planned.items():
        print(f"{name}: {info['total_replacements']} replacement(s)")

    print(f"\nTotal planned replacements: {total_replacements}")

    if total_replacements == 0:
        print(
            "\nNo matching current-identity strings were found. "
            "The files may already be normalized."
        )
        return 0

    if not args.apply:
        print(
            "\nDry run passed. No files were changed.\n"
            "Run again with --apply to create backups, write the changes, "
            "and generate IDENTITY_PATCH_REPORT.md."
        )
        if jsonld_warnings:
            print("\nJSON-LD warnings detected (not caused by this identity patch):")
            for warning in jsonld_warnings:
                print(f"- {warning}")
        return 0

    backup_dir.mkdir(parents=True, exist_ok=False)
    for path in target_paths:
        shutil.copy2(path, backup_dir / path.name)
        path.write_text(patched_texts[path], encoding="utf-8", newline="\n")

    # Verify the written result.
    for path in target_paths:
        written = path.read_text(encoding="utf-8")
        for marker in OLD_MARKERS:
            if marker in written:
                print(
                    f"ERROR: verification failed; {marker!r} remains in {path.name}",
                    file=sys.stderr,
                )
                return 4
        planned[path.name]["sha256_after"] = sha256(path)

    after_tree = all_file_hashes(root)
    changed_files = sorted(
        set(before_tree) | set(after_tree),
        key=str.lower,
    )
    changed_files = [
        name for name in changed_files
        if before_tree.get(name) != after_tree.get(name)
    ]

    unexpected = [name for name in changed_files if name not in TARGET_FILES]
    if unexpected:
        print(
            "ERROR: files outside the approved scope changed: "
            + ", ".join(unexpected),
            file=sys.stderr,
        )
        return 5

    report = [
        "# Identity Normalization Patch Report",
        "",
        f"- Applied (UTC): {timestamp}",
        "- Approved current identity: **Dr. Ahmad Saylam**",
        "- Previous present-day identity: **Prof. Dr. Ahmad Saylam**",
        "- Scope: five principal website pages only",
        "- Historical publication/article pages modified: **No**",
        f"- Backup directory: `{backup_dir.name}/`",
        "",
        "## Modified files",
        "",
    ]

    for name in TARGET_FILES:
        info = planned[name]
        report.extend([
            f"### `{name}`",
            f"- Replacements: {info['total_replacements']}",
            f"- SHA-256 before: `{info['sha256_before']}`",
            f"- SHA-256 after: `{info['sha256_after']}`",
            "",
        ])

    report.extend([
        "## Validation",
        "",
        "- No approved old identity marker remains in the five target files.",
        "- No file outside the approved five-page scope changed.",
        "- `papers/` and `publications/` article pages were not modified.",
    ])

    if jsonld_warnings:
        report.extend([
            "",
            "## Pre-existing JSON-LD warnings",
            "",
            "These warnings were detected but were not modified in Step 1:",
            "",
        ])
        report.extend(f"- {warning}" for warning in jsonld_warnings)

    report_path = root / "IDENTITY_PATCH_REPORT.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")

    print("\nPatch applied and verified.")
    print(f"Backup: {backup_dir}")
    print(f"Report: {report_path}")
    if jsonld_warnings:
        print("\nPre-existing JSON-LD warnings:")
        for warning in jsonld_warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
