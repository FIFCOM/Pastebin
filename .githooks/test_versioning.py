#!/usr/bin/env python3
"""Regression tests for version consistency checks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))

import versioning  # noqa: E402


class RefVersionChecksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.files = {
            "VERSION": (versioning.ROOT / "VERSION").read_text(encoding="utf-8")
        }
        for rule in versioning.TEXT_RULES:
            self.files[rule.path] = (versioning.ROOT / rule.path).read_text(
                encoding="utf-8"
            )

    def _read_ref_file(
        self, _ref: str, path: str, *, required: bool = True
    ) -> str | None:
        value = self.files.get(path)
        if value is None and required:
            raise versioning.VersioningError(f"missing test file {path}")
        return value

    def test_accepts_consistent_managed_fields(self) -> None:
        with patch.object(
            versioning, "_read_file_at_ref", side_effect=self._read_ref_file
        ):
            versioning.check_versions_at_ref("consistent")

    def test_rejects_inconsistent_managed_field(self) -> None:
        rule = next(
            rule for rule in versioning.TEXT_RULES if rule.path == "pyproject.toml"
        )
        wrong_version = versioning.current_version().next_patch()
        self.files[rule.path], count = rule.pattern.subn(
            lambda match: f"{match.group(1)}{wrong_version}{match.group(2)}",
            self.files[rule.path],
        )
        self.assertEqual(count, 1)

        with patch.object(
            versioning, "_read_file_at_ref", side_effect=self._read_ref_file
        ):
            with self.assertRaisesRegex(
                versioning.VersioningError, "pyproject project version"
            ):
                versioning.check_versions_at_ref("inconsistent")

    def test_skips_full_consistency_check_for_legacy_commit(self) -> None:
        self.files.pop("VERSION")
        with patch.object(
            versioning, "_read_file_at_ref", side_effect=self._read_ref_file
        ):
            versioning.check_versions_at_ref("legacy")

    def test_range_rejects_inconsistent_intermediate_commit(self) -> None:
        commit = "a" * 40
        ancestry_result = versioning.subprocess.CompletedProcess([], 0)
        range_result = versioning.subprocess.CompletedProcess(
            [], 0, stdout=f"{commit}\n"
        )

        with (
            patch.object(
                versioning.subprocess,
                "run",
                side_effect=(ancestry_result, range_result),
            ),
            patch.object(
                versioning,
                "check_versions_at_ref",
                side_effect=versioning.VersioningError(
                    "version fields are inconsistent"
                ),
            ) as check_ref,
        ):
            with self.assertRaisesRegex(
                versioning.VersioningError,
                "commit aaaaaaaaaaaa: version fields are inconsistent",
            ):
                versioning.check_range("before", "after")

        check_ref.assert_called_once_with(commit)


if __name__ == "__main__":
    unittest.main()
