from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from tests.helpers import assert_paths_equal

from voice_dubbing_runtime.paths import (
    legacy_user_data_root,
    migration_is_complete,
    standalone_user_data_root,
    user_data_root,
)
from voice_dubbing_runtime.storage_migration import migrate_storage


class StorageMigrationTests(unittest.TestCase):
    def _roots(self, base: Path) -> tuple[dict[str, str], Path, Path]:
        environ = {"LOCALAPPDATA": str(base)}
        return (
            environ,
            legacy_user_data_root(environ),
            standalone_user_data_root(environ),
        )

    @staticmethod
    def _write(root: Path, relative: str, content: bytes) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_empty_legacy_does_not_create_or_switch_target(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            environ, legacy, target = self._roots(Path(raw))
            payload = migrate_storage(legacy, target)
            self.assertEqual("NO_SOURCE", payload["status"])
            self.assertFalse(target.exists())
            assert_paths_equal(target, user_data_root(environ))

    def test_legacy_only_is_copied_verified_and_selected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            environ, legacy, target = self._roots(Path(raw))
            source = self._write(legacy, "profiles/alpha/references/ref_primary.wav", b"voice")
            payload = migrate_storage(legacy, target)
            copied = target / source.relative_to(legacy)
            self.assertEqual("COMPLETE", payload["status"])
            self.assertEqual(source.read_bytes(), copied.read_bytes())
            self.assertTrue(source.exists())
            self.assertTrue(migration_is_complete(target))
            assert_paths_equal(target, user_data_root(environ))

    def test_existing_identical_target_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _environ, legacy, target = self._roots(Path(raw))
            self._write(legacy, "licenses/acceptance.json", b"same")
            existing = self._write(target, "licenses/acceptance.json", b"same")
            before = existing.stat().st_mtime_ns
            payload = migrate_storage(legacy, target)
            self.assertEqual("COMPLETE", payload["status"])
            self.assertEqual(0, payload["files_copied"])
            self.assertEqual(before, existing.stat().st_mtime_ns)

    def test_partial_target_copies_only_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _environ, legacy, target = self._roots(Path(raw))
            self._write(legacy, "profiles/alpha/profile.json", b"profile")
            self._write(legacy, "runs/job/result.json", b"result")
            self._write(target, "profiles/alpha/profile.json", b"profile")
            payload = migrate_storage(legacy, target)
            self.assertEqual("COMPLETE", payload["status"])
            self.assertEqual(1, payload["files_copied"])
            self.assertEqual(b"result", (target / "runs/job/result.json").read_bytes())

    def test_hash_conflict_fails_without_source_or_target_data_loss(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            environ, legacy, target = self._roots(Path(raw))
            source = self._write(legacy, "profiles/alpha/profile.json", b"source")
            conflict = self._write(target, "profiles/alpha/profile.json", b"target")
            payload = migrate_storage(legacy, target)
            self.assertEqual("FAILED", payload["status"])
            self.assertEqual(b"source", source.read_bytes())
            self.assertEqual(b"target", conflict.read_bytes())
            self.assertFalse(migration_is_complete(target))
            assert_paths_equal(legacy, user_data_root(environ))

    def test_hidden_history_trash_and_pre_repair_snapshots_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _environ, legacy, target = self._roots(Path(raw))
            relatives = (
                "profiles/.history/profile/revision.json",
                "profiles/.trash/deleted/profile.json",
                "profiles/.lua_china_base.pre-repair-abc/profile.json",
            )
            for index, relative in enumerate(relatives):
                self._write(legacy, relative, f"hidden-{index}".encode())
            payload = migrate_storage(legacy, target)
            self.assertEqual("COMPLETE", payload["status"])
            for relative in relatives:
                self.assertEqual((legacy / relative).read_bytes(), (target / relative).read_bytes())

    def test_rerun_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            _environ, legacy, target = self._roots(Path(raw))
            self._write(legacy, "config/settings.json", b"{}")
            first = migrate_storage(legacy, target)
            second = migrate_storage(legacy, target)
            self.assertEqual("COMPLETE", first["status"])
            self.assertEqual("COMPLETE", second["status"])
            self.assertEqual(0, second["files_copied"])
            self.assertEqual(1, second["verified_count"])

    def test_incomplete_marker_falls_back_to_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            environ, legacy, target = self._roots(Path(raw))
            self._write(legacy, "profiles/alpha/profile.json", b"profile")
            target.mkdir(parents=True)
            (target / "migration.json").write_text(
                json.dumps({"schema_version": 1, "status": "FAILED"}), encoding="utf-8"
            )
            assert_paths_equal(legacy, user_data_root(environ))


if __name__ == "__main__":
    unittest.main()
