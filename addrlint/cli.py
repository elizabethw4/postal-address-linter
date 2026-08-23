"""Command-line entry point for addrlint."""

import argparse
import sys
from typing import List, Optional

from .parser import Diagnostic, ParseError, parse
from .validator import validate_block


def main(argv: Optional[List[str]] = None) -> int:
    arg_parser = argparse.ArgumentParser(
        prog="addrlint",
        description="Check address blocks in a text file for structural and postal-format errors.",
    )
    arg_parser.add_argument("file", help="path to an address file")
    args = arg_parser.parse_args(argv)

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"addrlint: cannot read {args.file}: {e.strerror}", file=sys.stderr)
        return 2

    source_lines = text.splitlines()

    try:
        blocks = parse(text)
    except ParseError as e:
        diag = Diagnostic(
            severity="error",
            message=e.message,
            filename=args.file,
            line=e.line,
            col=e.col,
            length=e.length,
        )
        print(diag.render(source_lines), file=sys.stderr)
        return 1

    if not blocks:
        print(f"addrlint: {args.file}: no address blocks found", file=sys.stderr)
        return 1

    all_diagnostics = []
    for block in blocks:
        all_diagnostics.extend(validate_block(block, args.file))

    for diag in all_diagnostics:
        print(diag.render(source_lines), file=sys.stderr)

    if all_diagnostics:
        print(f"\n{len(all_diagnostics)} error(s) found in {args.file}", file=sys.stderr)
        return 1

    print(f"addrlint: {args.file}: {len(blocks)} address block(s), no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
