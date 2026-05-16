import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from codex_fast_patch.app import AppPaths, rollback_files


class AppSafetyTest(unittest.TestCase):
    def make_paths(self, tmp: Path) -> AppPaths:
        return AppPaths(resources_dir=tmp, fuse_app_path=tmp / "Codex.app")

    def test_rollback_restores_asar_before_removing_extracted_app(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            paths = self.make_paths(tmp)
            paths.extracted_app_dir.mkdir()
            (paths.extracted_app_dir / "marker.txt").write_text("patched", encoding="utf-8")
            paths.backup_asar_path.write_text("official asar", encoding="utf-8")

            rollback_files(paths)

            self.assertFalse(paths.extracted_app_dir.exists())
            self.assertEqual(paths.asar_path.read_text(encoding="utf-8"), "official asar")

    def test_rollback_keeps_extracted_app_when_restore_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            paths = self.make_paths(tmp)
            paths.extracted_app_dir.mkdir()
            paths.backup_asar_path.write_text("official asar", encoding="utf-8")

            original_copy2 = shutil.copy2

            def blocked_copy(src, dst, *args, **kwargs):
                if Path(dst) == paths.asar_path:
                    raise PermissionError("blocked by App Management")
                return original_copy2(src, dst, *args, **kwargs)

            with patch("codex_fast_patch.app.shutil.copy2", side_effect=blocked_copy):
                with self.assertRaises(SystemExit):
                    rollback_files(paths)

            self.assertTrue(paths.extracted_app_dir.exists())
            self.assertFalse(paths.asar_path.exists())


if __name__ == "__main__":
    unittest.main()
