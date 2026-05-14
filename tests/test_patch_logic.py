import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from codex_fast_patch.app import AppPaths
from codex_fast_patch.bundle import patch_js


class PatchLogicTest(unittest.TestCase):
    def make_paths(self, tmp: Path) -> AppPaths:
        assets = tmp / "app" / "webview" / "assets"
        assets.mkdir(parents=True)
        return AppPaths(resources_dir=tmp, fuse_app_path=tmp / "Codex.app")

    def test_patches_known_bundle_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            paths = self.make_paths(tmp)
            assets = paths.assets_dir

            (assets / "permissions-mode-helpers-a.js").write_text(
                "return!(r?.authMethod!==`chatgpt`||i?.requirements?.featureRequirements?.fast_mode===!1);"
                "if(i?.authMethod!==`chatgpt`||s){canUseFastMode:false}"
                "u?.models.some(M)??!1",
                encoding="utf-8",
            )
            (assets / "index-a.js").write_text(
                "const x=D?(0,$.jsx)(Sl,{tooltipContent:(0,$.jsx)(Y,{id:`sidebarElectron.pluginsDisabledTooltip`})});",
                encoding="utf-8",
            )
            (assets / "gradient-a.js").write_text(
                "function e(e){return e===`apikey`}",
                encoding="utf-8",
            )
            (assets / "use-plugin-install-flow-a.js").write_text(
                "if(a){(i=`connector-unavailable`)}",
                encoding="utf-8",
            )

            report = patch_js(paths)

            self.assertEqual(report.patch_actions, 6)
            self.assertEqual(report.patched_files, 4)
            self.assertIn("return true", (assets / "permissions-mode-helpers-a.js").read_text())
            self.assertIn("if(false){", (assets / "permissions-mode-helpers-a.js").read_text())
            self.assertIn("true", (assets / "permissions-mode-helpers-a.js").read_text())
            self.assertIn("0?(0,$.jsx)(Sl,{tooltipContent", (assets / "index-a.js").read_text())
            self.assertIn("function e(e){return false}", (assets / "gradient-a.js").read_text())
            self.assertIn("false&&(i=`connector-unavailable`)", (assets / "use-plugin-install-flow-a.js").read_text())


    def test_patches_chatgpt_variant_of_apikey_gate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            paths = self.make_paths(tmp)
            assets = paths.assets_dir

            (assets / "permissions-mode-helpers-a.js").write_text(
                "return!(r?.authMethod!==`chatgpt`||i?.requirements?.featureRequirements?.fast_mode===!1);"
                "if(i?.authMethod!==`chatgpt`||s){canUseFastMode:false}"
                "u?.models.some(M)??!1",
                encoding="utf-8",
            )
            (assets / "index-a.js").write_text(
                "const x=D?(0,$.jsx)(Sl,{tooltipContent:(0,$.jsx)(Y,{id:`sidebarElectron.pluginsDisabledTooltip`})});",
                encoding="utf-8",
            )
            (assets / "gradient-a.js").write_text(
                "function e(e){return e!==`chatgpt`}",
                encoding="utf-8",
            )
            (assets / "use-plugin-install-flow-a.js").write_text(
                "if(a){(i=`connector-unavailable`)}",
                encoding="utf-8",
            )

            report = patch_js(paths)

            self.assertEqual(report.patch_actions, 6)
            self.assertIn(
                "function e(e){return false}",
                (assets / "gradient-a.js").read_text(),
            )

    def test_patches_apikey_gate_with_regex_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            paths = self.make_paths(tmp)
            assets = paths.assets_dir

            (assets / "permissions-mode-helpers-a.js").write_text(
                "return!(r?.authMethod!==`chatgpt`||i?.requirements?.featureRequirements?.fast_mode===!1);"
                "if(i?.authMethod!==`chatgpt`||s){canUseFastMode:false}"
                "u?.models.some(M)??!1",
                encoding="utf-8",
            )
            (assets / "index-a.js").write_text(
                "const x=D?(0,$.jsx)(Sl,{tooltipContent:(0,$.jsx)(Y,{id:`sidebarElectron.pluginsDisabledTooltip`})});",
                encoding="utf-8",
            )
            # Identifier renamed by the minifier; only the regex fallback can match it.
            (assets / "gradient-a.js").write_text(
                "function q(q){return q!==`chatgpt`}",
                encoding="utf-8",
            )
            (assets / "use-plugin-install-flow-a.js").write_text(
                "if(a){(i=`connector-unavailable`)}",
                encoding="utf-8",
            )

            report = patch_js(paths)

            self.assertEqual(report.patch_actions, 6)
            self.assertIn(
                "function q(q){return false}",
                (assets / "gradient-a.js").read_text(),
            )

    def test_raises_when_no_patterns_match(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            paths = self.make_paths(tmp)
            (paths.assets_dir / "index-a.js").write_text("console.log('no patch')", encoding="utf-8")

            with self.assertRaises(SystemExit):
                patch_js(paths)


if __name__ == "__main__":
    unittest.main()
