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
        }


def _lint_file(filename: str) -> FileResult:
    result = FileResult(filename)

    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        result.read_error = e.strerror or str(e)
        return result

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


def _print_text_result(result: FileResult) -> None:
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
    args = arg_parser.parse_args(argv)

    results = [_lint_file(filename) for filename in args.files]

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
