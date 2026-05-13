import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SkillPackagingTest(unittest.TestCase):
    def test_uses_canonical_skills_directory_entrypoint(self) -> None:
        self.assertFalse((ROOT / "SKILL.md").exists())
        skill_file = ROOT / "skills" / "patch-codex-fast" / "SKILL.md"
        self.assertTrue(skill_file.exists())
        text = skill_file.read_text(encoding="utf-8")
        self.assertIn("name: patch-codex-fast", text)
        self.assertIn("description:", text)
        self.assertLessEqual(len(text.splitlines()), 500)

    def test_installable_skill_contains_current_script_assets(self) -> None:
        root_scripts = sorted(
            p.relative_to(ROOT / "scripts")
            for p in (ROOT / "scripts").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
        packaged_scripts = sorted(
            p.relative_to(ROOT / "skills" / "patch-codex-fast" / "scripts")
            for p in (ROOT / "skills" / "patch-codex-fast" / "scripts").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
        self.assertEqual(root_scripts, packaged_scripts)
        for rel_path in root_scripts:
            root_bytes = (ROOT / "scripts" / rel_path).read_bytes()
            packaged_bytes = (
                ROOT / "skills" / "patch-codex-fast" / "scripts" / rel_path
            ).read_bytes()
            self.assertEqual(root_bytes, packaged_bytes, str(rel_path))


if __name__ == "__main__":
    unittest.main()
