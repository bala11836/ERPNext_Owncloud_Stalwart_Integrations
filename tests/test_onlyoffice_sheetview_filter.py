"""A saved sheet view with an empty column filter must not crash the editor (SRN workbook, 20-21 Nov 2026).

ONLYOFFICE 10.0.0 (build 169): CT_NsvFilter.IU() calls `.filter.IU()` on every column filter, but a
column filter may have no filter (saved as <columnFilter ...></columnFilter>), which throws
"Cannot read properties of null (reading 'IU')" and leaves the grid blank for everyone who opens the
file. Two defences: the editor start page replaces IU() with a null-safe copy, and the repair tool
removes such entries from a saved file. The guard test runs the editor's own original method (copied
from the pinned build) and the guard block from the start page in headless Chrome; skipped when
Chrome is not installed.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/onlyoffice"))
import sheetview_sanitize as tool  # noqa: E402

EJS = (ROOT / "integrations/onlyoffice/editor-wopi.ejs").read_text()
CHROME = next((p for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                           shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p and Path(p).exists()), None)

# Exact source of CT_NsvFilter.prototype.IU in sdkjs/cell/sdk-all.js of 10.0.0-25b1e290...
ORIGINAL_IU = "function(){var q=null;if(this.wB&&this.wB.length)for(var r=0;r<this.wB.length;r++)if((this.wB[r]&&this.wB[r].filter).IU()){q=!0;break}return q}"

VIEW_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<namedSheetViews xmlns="http://schemas.microsoft.com/office/spreadsheetml/2019/namedsheetviews">'
            '<namedSheetView name="Temporary View 1" id="{A}"></namedSheetView>'
            '<namedSheetView name="Private - Rajesh" id="{B}"><nsvFilter filterId="{C}" tableId="3">'
            '<columnFilter colId="5" id="{D}"></columnFilter>'
            '<columnFilter colId="2" id="{E}"><filter colId="2"><x:filters xmlns:x="u"><x:filter val="v"/></x:filters></filter></columnFilter>'
            '</nsvFilter></namedSheetView></namedSheetViews>')


def make_workbook(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/worksheets/sheet1.xml", "<worksheet>cells</worksheet>")
        z.writestr("xl/namedSheetViews/namedSheetView1.xml", VIEW_XML)


class SanitiserTests(unittest.TestCase):
    def test_removes_only_the_empty_column_filter_and_keeps_everything_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "a.xlsx", Path(tmp) / "b.xlsx"
            make_workbook(src)
            self.assertEqual(tool.inspect(src)["empty_column_filters"], 1)
            changed = tool.sanitize(src, dst)
            self.assertEqual(changed, ["xl/namedSheetViews/namedSheetView1.xml"])
            self.assertEqual(tool.inspect(dst)["empty_column_filters"], 0)
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst) as b:
                self.assertEqual(a.read("xl/worksheets/sheet1.xml"), b.read("xl/worksheets/sheet1.xml"))
                text = b.read("xl/namedSheetViews/namedSheetView1.xml").decode()
            self.assertIn('name="Private - Rajesh"', text)       # views and their real filters stay
            self.assertIn('<x:filter val="v"/>', text)
            self.assertIn('name="Temporary View 1"', text)        # shells stay unless asked

    def test_temporary_shells_removed_only_on_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "a.xlsx", Path(tmp) / "b.xlsx"
            make_workbook(src)
            tool.sanitize(src, dst, temporary=True)
            self.assertNotIn("Temporary View", zipfile.ZipFile(dst).read("xl/namedSheetViews/namedSheetView1.xml").decode())

    def test_a_clean_workbook_is_copied_unchanged_and_the_input_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, mid, dst = Path(tmp) / "a.xlsx", Path(tmp) / "b.xlsx", Path(tmp) / "c.xlsx"
            make_workbook(src)
            before = src.read_bytes()
            tool.sanitize(src, mid)
            self.assertEqual(tool.sanitize(mid, dst), [])
            self.assertEqual(src.read_bytes(), before)


@unittest.skipUnless(CHROME, "Chrome is not installed")
class GuardTests(unittest.TestCase):
    def run_page(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "p.html"
            page.write_text("<!doctype html><title>x</title><script>" + body + "</script>")
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=8000",
                                  "--dump-dom", page.as_uri()], capture_output=True, text=True, timeout=90).stdout
        return json.loads(re.search(r"<title>(\{.*?\})</title>", out).group(1).replace("&quot;", '"'))

    def harness(self):
        block = re.search(r"/\* SHEET-VIEW-FILTER-GUARD-BEGIN \*/(.*?)/\* SHEET-VIEW-FILTER-GUARD-END \*/", EJS, re.S).group(1)
        return ("var iframe={contentWindow:{Asc:{CT_NsvFilter:function(){this.wB=[]}}}};"
                "document.querySelector=function(){return iframe};"
                "var P=iframe.contentWindow.Asc.CT_NsvFilter.prototype;P.IU=" + ORIGINAL_IU + ";"
                + block + "cloudInstallViewFilterGuard();"
                "setTimeout(function(){var out={};"
                "var real={filter:{IU:function(){return true}}},none={filter:null},plain={filter:{IU:function(){return false}}};"
                "function run(entries){var v=new iframe.contentWindow.Asc.CT_NsvFilter();v.wB=entries;try{return String(v.IU())}catch(e){return 'THROWS '+e.message}}"
                "out.guarded=P.IU.cloudSafe===true;"
                "out.empty=run([none]);out.empty_then_real=run([none,real]);out.real=run([real]);out.plain=run([plain]);out.nothing=run([]);"
                "document.title=JSON.stringify(out)},1500);")

    def test_original_method_throws_and_the_guard_makes_it_safe_without_changing_real_results(self):
        result = self.run_page(self.harness())
        self.assertTrue(result["guarded"])
        self.assertEqual(result["empty"], "null")             # no crash: nothing applied
        self.assertEqual(result["empty_then_real"], "true")   # a real filter is still reported
        self.assertEqual(result["real"], "true")
        self.assertEqual(result["plain"], "null")
        self.assertEqual(result["nothing"], "null")

    def test_the_unguarded_original_really_throws_the_reported_error(self):
        body = ("var P={};P.IU=" + ORIGINAL_IU + ";var v={wB:[{filter:null}],IU:P.IU};var m='';"
                "try{v.IU()}catch(e){m=e.message}document.title=JSON.stringify({m:m});")
        self.assertEqual(self.run_page(body)["m"], "Cannot read properties of null (reading 'IU')")

    def test_the_guard_leaves_a_fixed_build_alone(self):
        body = self.harness().replace("P.IU=" + ORIGINAL_IU + ";", "P.IU=function(){return 'fixed upstream'};")
        out = self.run_page(body)
        self.assertFalse(out["guarded"])
        self.assertEqual(out["empty"], "fixed upstream")

    def test_guard_is_installed_when_the_app_is_ready(self):
        self.assertRegex(EJS, r'innerAlert\("App ready"\);\s*cloudInstallViewFilterGuard\(\);')


if __name__ == "__main__":
    unittest.main()
