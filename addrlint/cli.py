"""Command-line entry point for addrlint."""

import argparse
import json
import sys
from typing import List, Optional

from .parser import Diagnostic, ParseError, parse
from .validator import validate_block


class FileResult:
    def __init__(self, filename: str):
        self.filename = filename
        self.read_error: Optional[str] = None
        self.diagnostics: List[Diagnostic] = []
        self.block_count = 0
        self.parse_failed = False
        self.source_lines: List[str] = []
        self.text = ""
        self.fixed_count = 0

    @property
    def no_blocks_found(self) -> bool:
        return not self.read_error and not self.parse_failed and self.block_count == 0

    @property
    def ok(self) -> bool:
        return not self.read_error and not self.parse_failed and not self.no_blocks_found and not self.diagnostics

    def to_dict(self) -> dict:
        return {
            "file": self.filename,
            "error": self.read_error,
            "blocks": self.block_count,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "ok": self.ok,
            "fixed": self.fixed_count,
        }


def _lint_file(filename: str) -> FileResult:
    result = FileResult(filename)

    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        result.read_error = e.strerror or str(e)
        return result

    result.text = text
    result.source_lines = text.splitlines()

    try:
        blocks = parse(text)
    except ParseError as e:
        result.parse_failed = True
        result.diagnostics.append(Diagnostic(
            severity="error",
            message=e.message,
            filename=filename,
            line=e.line,
            col=e.col,
            length=e.length,
        ))
    else:
        result.block_count = len(blocks)
        for block in blocks:
            result.diagnostics.extend(validate_block(block, filename))

    return result


def _apply_fixes(filename: str, text: str, diagnostics: List[Diagnostic]) -> int:
    """Rewrite `filename` with every fixable diagnostic applied in place.

    Each fixable diagnostic replaces the exact span it points at (line, col,
    length) with its `fix` text. Diagnostics are applied right-to-left within
    a line so earlier replacements don't shift the columns of later ones.
    Returns the number of fixes applied.
    """
    fixable = [d for d in diagnostics if d.fix is not None]
    if not fixable:
        return 0

    lines = text.splitlines(keepends=True)
    by_line: dict = {}
    for d in fixable:
        by_line.setdefault(d.line, []).append(d)

    for lineno, diags in by_line.items():
        line = lines[lineno - 1]
        for d in sorted(diags, key=lambda d: d.col, reverse=True):
            start = d.col - 1
            end = start + d.length
            line = line[:start] + d.fix + line[end:]
        lines[lineno - 1] = line

    with open(filename, "w", encoding="utf-8") as f:
        f.write("".join(lines))

    return len(fixable)


def _print_text_result(result: FileResult) -> None:
    if result.fixed_count:
        plural = "" if result.fixed_count == 1 else "s"
        print(f"addrlint: fixed {result.fixed_count} issue{plural} in {result.filename}")

    if result.read_error:
        print(f"addrlint: cannot read {result.filename}: {result.read_error}", file=sys.stderr)
    elif result.parse_failed:
        print(result.diagnostics[0].render(result.source_lines), file=sys.stderr)
    elif result.no_blocks_found:
        print(f"addrlint: {result.filename}: no address blocks found", file=sys.stderr)
    elif result.diagnostics:
        for diag in result.diagnostics:
            print(diag.render(result.source_lines), file=sys.stderr)
        print(f"\n{len(result.diagnostics)} error(s) found in {result.filename}", file=sys.stderr)
    else:
        print(f"addrlint: {result.filename}: {result.block_count} address block(s), no errors")


def main(argv: Optional[List[str]] = None) -> int:
    arg_parser = argparse.ArgumentParser(
        prog="addrlint",
        description="Check address blocks in a text file for structural and postal-format errors.",
    )
    arg_parser.add_argument("files", nargs="+", metavar="file", help="path to an address file")
    arg_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format for diagnostics (default: text)",
    )
    arg_parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite files in place to correct trivially fixable errors "
             "(currently: field names with the wrong case, and Canadian "
             "postal codes with the wrong case or spacing), then report "
             "whatever diagnostics remain",
    )
    args = arg_parser.parse_args(argv)

    results = []
    for filename in args.files:
        result = _lint_file(filename)
        if args.fix and not result.read_error and not result.parse_failed:
            fixed_count = _apply_fixes(filename, result.text, result.diagnostics)
            if fixed_count:
                result = _lint_file(filename)
                result.fixed_count = fixed_count
        results.append(result)

    if args.format == "json":
        payload = {
            "ok": all(r.ok for r in results),
            "files": [r.to_dict() for r in results],
        }
        print(json.dumps(payload, indent=2))
    else:
        for i, result in enumerate(results):
            if i > 0:
                print()
            _print_text_result(result)

    if any(r.read_error is not None for r in results):
        return 2
    if not all(r.ok for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
