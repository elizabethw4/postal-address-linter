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
        self.assertEqual(payload["blocks"], 1)
        self.assertEqual(payload["diagnostics"], [])
        self.assertTrue(payload["ok"])

    def test_validation_errors_are_reported_as_diagnostics(self):
        text = VALID_US_BLOCK.replace("region: IL", "region: XX")
        with TempAddressFile(text) as path:
            code, out, err = run_main([path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(len(payload["diagnostics"]), 1)
        diag = payload["diagnostics"][0]
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
        self.assertEqual(payload["blocks"], 0)
        self.assertEqual(len(payload["diagnostics"]), 1)
        self.assertIn("colon", payload["diagnostics"][0]["message"])

    def test_no_blocks_found_is_reported_with_no_diagnostics(self):
        with TempAddressFile("\n\n") as path:
            code, out, err = run_main([path, "--format", "json"])
        payload = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["blocks"], 0)
        self.assertEqual(payload["diagnostics"], [])


class TestTextFormat(unittest.TestCase):
    def test_is_the_default(self):
        with TempAddressFile(VALID_US_BLOCK) as path:
            code, out, err = run_main([path])
        self.assertEqual(code, 0)
        self.assertIn("no errors", out)


if __name__ == "__main__":
    unittest.main()
