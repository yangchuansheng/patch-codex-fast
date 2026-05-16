import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from codex_fast_patch.app import AppPaths
from codex_fast_patch.bundle import patch_js
from codex_fast_patch.zed_remote import detect_zed_remote_status


HOST_HELPERS = (
    "function fC(e){let t=e[tf],n=typeof t?.sshAlias==`string`?t.sshAlias.trim():``;"
    "if(n.length>0)return n;let r=Array.isArray(e.terminal_command)?e.terminal_command.at(-1):null,"
    "i=typeof r==`string`?r.trim():``;return i.length>0?i:null}"
    "function pC(e){let t=e.trim();return t.split(/[:/]/).at(-1)?.trim()||t}"
    "function dC(e){if(e.kind===`ssh`){let t=fC(e);if(t)return t}"
    "return e.name?.trim()||pC(e.id)}"
)

ZED_TARGET = (
    "function cC(){return`vscode-remote://x`}"
    "function Ow(e,t){return t?[`${e}:${t.line}:${t.column}`]:[e]}"
    "function iT(){return Fp(`zed`)??iC([`/Applications/Zed.app/Contents/MacOS/zed`])}"
    "function oT(){return oC(`Zed`)??iC([`/Applications/Zed.app`])}"
    "function sT(e){let t=e.indexOf(`.app/Contents/MacOS/`);return t===-1?null:e.slice(0,t+4)}"
    "async function cT(e,t,n){let r=Ow(t,n),i=sT(e)??oT();"
    "if(i){if(await zp(`open`,[`-a`,i,t]),!n)return;let e=Fp(`zed`);"
    "if(e)try{await zp(e,r)}catch{}return}await zp(e,r)}"
    "var rT={id:`zed`,platforms:{darwin:{label:`Zed`,icon:`apps/zed.png`,kind:`editor`,"
    "detect:iT,args:Ow,open:async({command:e,path:t,location:n})=>{await cT(e,t,n)}},"
    "win32:{label:`Zed`,icon:`apps/zed.png`,kind:`editor`,detect:aT,args:Ow}}};"
    "var lT=[rT];"
)


class ZedRemotePatchTest(unittest.TestCase):
    def make_paths(self, tmp: Path) -> AppPaths:
        build_dir = tmp / "app" / ".vite" / "build"
        assets_dir = tmp / "app" / "webview" / "assets"
        build_dir.mkdir(parents=True)
        assets_dir.mkdir(parents=True)
        return AppPaths(resources_dir=tmp, fuse_app_path=tmp / "Codex.app")

    def test_patches_zed_target_as_remote_capable(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            paths = self.make_paths(tmp)
            bundle = paths.extracted_app_dir / ".vite" / "build" / "main-a.js"
            bundle.write_text(HOST_HELPERS + ZED_TARGET, encoding="utf-8")

            with patch("codex_fast_patch.zed_remote.find_zed_app_path", return_value=Path("/Applications/Zed.app")):
                report = patch_js(paths, include_fast_plugins=False, include_zed_remote=True)
                status = detect_zed_remote_status(paths)

            text = bundle.read_text(encoding="utf-8")
            self.assertEqual(report.patch_actions, 2)
            self.assertEqual(report.patched_files, 1)
            self.assertTrue(status.patched)
            self.assertIn("supportsSsh:!0", text)
            self.assertIn("zedHostConfig", text)
            self.assertIn("zedRemotePathForCodexPatch", text)
            self.assertIn("zedSshConfigForCodexPatch", text)
            self.assertIn("typeof n.user==`string`", text)
            self.assertIn("typeof n.username==`string`", text)
            self.assertIn("ssh://${r}", text)
            self.assertIn(
                "open:async({command:e,path:t,location:n,"
                "hostConfig:zedHostConfig,remoteWorkspaceRoot:zedRemoteRoot,"
                "remotePath:zedRemotePath})=>{await cT(e,t,n,zedHostConfig,zedRemoteRoot,zedRemotePath)}",
                text,
            )
            self.assertIn("zedRemotePath)}},win32", text)
            self.assertNotIn("zedRemotePath)}}},win32", text)
            self.assertIn("Remote control does not support Zed remote open yet.", text)

    def test_raises_when_zed_remote_patterns_do_not_match(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            paths = self.make_paths(tmp)
            bundle = paths.extracted_app_dir / ".vite" / "build" / "main-a.js"
            bundle.write_text("var rT={id:`zed`,platforms:{darwin:{label:`Zed`}}};", encoding="utf-8")

            with self.assertRaises(SystemExit):
                patch_js(paths, include_fast_plugins=False, include_zed_remote=True)


if __name__ == "__main__":
    unittest.main()
