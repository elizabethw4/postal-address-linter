import contextlib
import io
import json
import os
import tempfile
import unittest

from addrlint.cli import main

VALID_US_BLOCK = (
    "name: Jane Doe\n"
    "street: 123 Main St\n"
    "city: Springfield\n"
    "region: IL\n"
    "postal_code: 62704\n"
)


class TempAddressFile:
    def __init__(self, text):
        self.text = text
        self.path = None

    def __enter__(self):
        fd, self.path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(self.text)
        return self.path

    def __exit__(self, *exc_info):
        os.remove(self.path)


def run_main(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


class TestJsonFormat(unittest.TestCase):
    def test_clean_file_reports_ok(self):
        with TempAddressFile(VALID_US_BLOCK) as path:
            code, out, err = run_main([path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["files"]), 1)
        file_result = payload["files"][0]
        self.assertEqual(file_result["blocks"], 1)
        self.assertEqual(file_result["diagnostics"], [])
        self.assertIsNone(file_result["error"])
        self.assertTrue(file_result["ok"])

    def test_validation_errors_are_reported_as_diagnostics(self):
        text = VALID_US_BLOCK.replace("region: IL", "region: XX")
        with TempAddressFile(text) as path:
            code, out, err = run_main([path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        file_result = payload["files"][0]
        self.assertFalse(file_result["ok"])
        self.assertEqual(len(file_result["diagnostics"]), 1)
        diag = file_result["diagnostics"][0]
        self.assertIn("XX", diag["message"])
        self.assertEqual(diag["severity"], "error")
        self.assertIn("line", diag)
        self.assertIn("col", diag)

    def test_parse_error_is_reported_as_a_single_diagnostic(self):
        with TempAddressFile("name Jane\n") as path:
            code, out, err = run_main([path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        file_result = payload["files"][0]
        self.assertEqual(file_result["blocks"], 0)
        self.assertEqual(len(file_result["diagnostics"]), 1)
        self.assertIn("colon", file_result["diagnostics"][0]["message"])

    def test_no_blocks_found_is_reported_with_no_diagnostics(self):
        with TempAddressFile("\n\n") as path:
            code, out, err = run_main([path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        file_result = payload["files"][0]
        self.assertEqual(file_result["blocks"], 0)
        self.assertEqual(file_result["diagnostics"], [])

    def test_multiple_files_each_get_their_own_entry(self):
        broken = VALID_US_BLOCK.replace("region: IL", "region: XX")
        with TempAddressFile(VALID_US_BLOCK) as clean_path, TempAddressFile(broken) as broken_path:
            code, out, err = run_main([clean_path, broken_path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(len(payload["files"]), 2)
        self.assertEqual(payload["files"][0]["file"], clean_path)
        self.assertTrue(payload["files"][0]["ok"])
        self.assertEqual(payload["files"][1]["file"], broken_path)
        self.assertFalse(payload["files"][1]["ok"])

    def test_unreadable_file_is_reported_without_aborting_the_rest(self):
        missing_path = os.path.join(tempfile.gettempdir(), "addrlint-does-not-exist.txt")
        with TempAddressFile(VALID_US_BLOCK) as clean_path:
            code, out, err = run_main([missing_path, clean_path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 2)
        self.assertFalse(payload["ok"])
        self.assertIsNotNone(payload["files"][0]["error"])
        self.assertIsNone(payload["files"][1]["error"])
        self.assertTrue(payload["files"][1]["ok"])


class TestTextFormat(unittest.TestCase):
    def test_is_the_default(self):
        with TempAddressFile(VALID_US_BLOCK) as path:
            code, out, err = run_main([path])
        self.assertEqual(code, 0)
        self.assertIn("no errors", out)

    def test_multiple_files_are_each_reported(self):
        broken = VALID_US_BLOCK.replace("region: IL", "region: XX")
        with TempAddressFile(VALID_US_BLOCK) as clean_path, TempAddressFile(broken) as broken_path:
            code, out, err = run_main([clean_path, broken_path])
        self.assertEqual(code, 1)
        self.assertIn(f"{clean_path}: 1 address block(s), no errors", out)
        self.assertIn(broken_path, err)
        self.assertIn("not a recognized US state", err)

    def test_unreadable_file_does_not_stop_the_rest(self):
        missing_path = os.path.join(tempfile.gettempdir(), "addrlint-does-not-exist.txt")
        with TempAddressFile(VALID_US_BLOCK) as clean_path:
            code, out, err = run_main([missing_path, clean_path])
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)
        self.assertIn(f"{clean_path}: 1 address block(s), no errors", out)


if __name__ == "__main__":
    unittest.main()
