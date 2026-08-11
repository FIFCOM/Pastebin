#!/usr/bin/env python3
"""Keep Material Bin's product version fields synchronized."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

MANAGED_PATHS = (
    "VERSION",
    ".env.example",
    "pyproject.toml",
    "uv.lock",
    "app/__init__.py",
    "config/config.py",
    "Dockerfile",
    "compose.build.yaml",
    "web/package.json",
    "web/package-lock.json",
)


class VersioningError(RuntimeError):
    """Raised when version metadata is invalid or inconsistent."""


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> Version:
        match = SEMVER_RE.fullmatch(value.strip())
        if not match:
            raise VersioningError(
                f"invalid version {value!r}; expected MAJOR.MINOR.PATCH"
            )
        return cls(*(int(part) for part in match.groups()))

    def next_patch(self) -> Version:
        return Version(self.major, self.minor, self.patch + 1)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class TextRule:
    label: str
    path: str
    pattern: re.Pattern[str]


TEXT_RULES = (
    TextRule(
        "environment example version",
        ".env.example",
        re.compile(r'(?m)^(VERSION=")[^"]+("\s*)$'),
    ),
    TextRule(
        "pyproject project version",
        "pyproject.toml",
        re.compile(r'(?m)^(version = ")[^"]+("\s*)$'),
    ),
    TextRule(
        "uv material-bin version",
        "uv.lock",
        re.compile(
            r'(?m)(^\[\[package\]\]\nname = "material-bin"\nversion = ")[^"]+("$)'
        ),
    ),
    TextRule(
        "Python package version",
        "app/__init__.py",
        re.compile(r'(?m)^(__version__ = ")[^"]+("\s*)$'),
    ),
    TextRule(
        "runtime default version",
        "config/config.py",
        re.compile(r'(version=os\.getenv\("VERSION", ")[^"]+("\))'),
    ),
    TextRule(
        "Docker build version",
        "Dockerfile",
        re.compile(r"(?m)^(ARG APP_VERSION=)[^\s]+(\s*)$"),
    ),
    TextRule(
        "Compose build version",
        "compose.build.yaml",
        re.compile(r'(?m)^(\s*APP_VERSION: "\$\{APP_VERSION:-)[^}]+(\}"\s*)$'),
    ),
    TextRule(
        "frontend package version",
        "web/package.json",
        re.compile(r'(?m)^(  "version": ")[^"]+(",\s*)$'),
    ),
    TextRule(
        "frontend lock root version",
        "web/package-lock.json",
        re.compile(r'(?m)^(  "version": ")[^"]+(",\s*)$'),
    ),
    TextRule(
        "frontend lock workspace version",
        "web/package-lock.json",
        re.compile(
            r'(?m)(^\s{6}"name": "material-bin-web",\n\s{6}"version": ")[^"]+("\s*,)'
        ),
    ),
)


def _replace_rule(rule: TextRule, version: Version) -> None:
    path = ROOT / rule.path
    text = path.read_text(encoding="utf-8")
    updated, count = rule.pattern.subn(
        lambda match: f"{match.group(1)}{version}{match.group(2)}", text
    )
    if count != 1:
        raise VersioningError(
            f"{rule.label}: expected one version field in {rule.path}, found {count}"
        )
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def _extract_rule_from_text(rule: TextRule, text: str) -> Version:
    matches = list(rule.pattern.finditer(text))
    if len(matches) != 1:
        raise VersioningError(
            f"{rule.label}: expected one version field in {rule.path}, "
            f"found {len(matches)}"
        )
    match = matches[0]
    return Version.parse(text[match.end(1) : match.start(2)])


def _extract_rule(rule: TextRule) -> Version:
    text = (ROOT / rule.path).read_text(encoding="utf-8")
    return _extract_rule_from_text(rule, text)


def current_version() -> Version:
    return Version.parse((ROOT / "VERSION").read_text(encoding="utf-8"))


def set_version(version: Version) -> None:
    (ROOT / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    for rule in TEXT_RULES:
        _replace_rule(rule, version)

    # Ensure targeted edits did not leave either JSON file malformed.
    for relative_path in ("web/package.json", "web/package-lock.json"):
        with (ROOT / relative_path).open(encoding="utf-8") as file:
            json.load(file)


def check_versions() -> None:
    expected = current_version()
    mismatches = []
    for rule in TEXT_RULES:
        actual = _extract_rule(rule)
        if actual != expected:
            mismatches.append(f"{rule.label}: {actual} (expected {expected})")
    if mismatches:
        raise VersioningError(
            "version fields are inconsistent:\n  " + "\n  ".join(mismatches)
        )


def _read_file_at_ref(ref: str, path: str, *, required: bool = True) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout
    if required:
        raise VersioningError(f"cannot read {path} from Git ref {ref!r}")
    return None


def version_at_ref(ref: str) -> Version:
    version_file = _read_file_at_ref(ref, "VERSION", required=False)
    if version_file is not None:
        return Version.parse(version_file)

    pyproject = _read_file_at_ref(ref, "pyproject.toml")
    assert pyproject is not None
    pyproject_rule = next(rule for rule in TEXT_RULES if rule.path == "pyproject.toml")
    return _extract_rule_from_text(pyproject_rule, pyproject)


def check_versions_at_ref(ref: str) -> None:
    version_file = _read_file_at_ref(ref, "VERSION", required=False)
    if version_file is None:
        # Commits before VERSION was introduced remain valid legacy history.
        return

    expected = Version.parse(version_file)
    mismatches = []
    for rule in TEXT_RULES:
        text = _read_file_at_ref(ref, rule.path)
        assert text is not None
        actual = _extract_rule_from_text(rule, text)
        if actual != expected:
            mismatches.append(f"{rule.label}: {actual} (expected {expected})")
    if mismatches:
        raise VersioningError(
            "version fields are inconsistent:\n  " + "\n  ".join(mismatches)
        )


def validate_transition(previous: Version, current: Version) -> None:
    if current == previous.next_patch():
        return

    larger_line = current.major > previous.major or (
        current.major == previous.major and current.minor > previous.minor
    )
    if larger_line and current.patch == 0:
        return

    raise VersioningError(
        f"invalid version transition {previous} -> {current}; "
        f"expected {previous.next_patch()} or a larger major/minor version with patch 0"
    )


def selected_commit_version(previous: Version, staged: Version) -> Version:
    if staged.major > previous.major or (
        staged.major == previous.major and staged.minor > previous.minor
    ):
        if staged.patch != 0:
            raise VersioningError("a manual major/minor version must have patch 0")
        return staged

    if (staged.major, staged.minor) < (previous.major, previous.minor):
        raise VersioningError(f"cannot decrease version from {previous} to {staged}")

    return previous.next_patch()


def check_range(before: str, after: str) -> None:
    if not before or set(before) == {"0"}:
        raise VersioningError(
            "cannot validate a push without its previous Git revision"
        )

    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", before, after], cwd=ROOT, check=False
    )
    if ancestry.returncode != 0:
        raise VersioningError(
            f"{before} is not an ancestor of {after}; force-push refused"
        )

    result = subprocess.run(
        ["git", "rev-list", "--first-parent", "--reverse", f"{before}..{after}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    commits = result.stdout.split()
    if not commits:
        raise VersioningError("push range contains no first-parent commits")

    previous_ref = before
    for commit in commits:
        try:
            check_versions_at_ref(commit)
            previous = version_at_ref(previous_ref)
            current = version_at_ref(commit)
            validate_transition(previous, current)
        except VersioningError as error:
            raise VersioningError(f"commit {commit[:12]}: {error}") from error
        previous_ref = commit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("current", help="print the current version")
    subparsers.add_parser("check", help="check all managed version fields")
    subparsers.add_parser("paths", help="print all managed file paths")

    set_parser = subparsers.add_parser("set", help="set and synchronize a version")
    set_parser.add_argument("version")

    subparsers.add_parser("bump-patch", help="increment and synchronize patch")

    at_ref_parser = subparsers.add_parser(
        "at-ref", help="print a version stored in Git"
    )
    at_ref_parser.add_argument("ref")

    select_parser = subparsers.add_parser(
        "select-commit", help="select an automatic or manually requested commit version"
    )
    select_parser.add_argument("previous")
    select_parser.add_argument("staged")

    transition_parser = subparsers.add_parser(
        "validate-transition", help="validate one version transition"
    )
    transition_parser.add_argument("previous")
    transition_parser.add_argument("current")

    range_parser = subparsers.add_parser(
        "check-range", help="validate every first-parent commit in a pushed range"
    )
    range_parser.add_argument("before")
    range_parser.add_argument("after")

    tag_parser = subparsers.add_parser("check-tag", help="check vX.Y.Z against VERSION")
    tag_parser.add_argument("tag")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "current":
            print(current_version())
        elif args.command == "check":
            check_versions()
            print(current_version())
        elif args.command == "paths":
            print("\n".join(MANAGED_PATHS))
        elif args.command == "set":
            version = Version.parse(args.version)
            set_version(version)
            print(version)
        elif args.command == "bump-patch":
            version = current_version().next_patch()
            set_version(version)
            print(version)
        elif args.command == "at-ref":
            print(version_at_ref(args.ref))
        elif args.command == "select-commit":
            print(
                selected_commit_version(
                    Version.parse(args.previous), Version.parse(args.staged)
                )
            )
        elif args.command == "validate-transition":
            validate_transition(
                Version.parse(args.previous), Version.parse(args.current)
            )
        elif args.command == "check-range":
            check_range(args.before, args.after)
        elif args.command == "check-tag":
            tag_version = args.tag.removeprefix("v")
            expected = current_version()
            actual = Version.parse(tag_version)
            if actual != expected:
                raise VersioningError(
                    f"tag {args.tag!r} does not match repository version {expected}"
                )
        else:  # pragma: no cover - argparse enforces a command.
            raise AssertionError(args.command)
    except (OSError, subprocess.CalledProcessError, VersioningError) as error:
        print(f"versioning error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
