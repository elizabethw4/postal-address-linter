"""Command-line entry point for addrlint."""

import argparse
import json
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
    arg_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format for diagnostics (default: text)",
    )
    args = arg_parser.parse_args(argv)

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"addrlint: cannot read {args.file}: {e.strerror}", file=sys.stderr)
        return 2

    source_lines = text.splitlines()
    diagnostics: List[Diagnostic] = []
    block_count = 0
    parse_failed = False

    try:
        blocks = parse(text)
    except ParseError as e:
        parse_failed = True
        diagnostics.append(Diagnostic(
            severity="error",
            message=e.message,
            filename=args.file,
            line=e.line,
            col=e.col,
            length=e.length,
        ))
    else:
        block_count = len(blocks)
        for block in blocks:
            diagnostics.extend(validate_block(block, args.file))

    no_blocks_found = not parse_failed and block_count == 0

    if args.format == "json":
        payload = {
            "file": args.file,
            "blocks": block_count,
            "diagnostics": [d.to_dict() for d in diagnostics],
            "ok": not parse_failed and not no_blocks_found and not diagnostics,
        }
        print(json.dumps(payload, indent=2))
    elif parse_failed:
        print(diagnostics[0].render(source_lines), file=sys.stderr)
    elif no_blocks_found:
        print(f"addrlint: {args.file}: no address blocks found", file=sys.stderr)
    elif diagnostics:
        for diag in diagnostics:
            print(diag.render(source_lines), file=sys.stderr)
        print(f"\n{len(diagnostics)} error(s) found in {args.file}", file=sys.stderr)
    else:
        print(f"addrlint: {args.file}: {block_count} address block(s), no errors")

    if parse_failed or no_blocks_found or diagnostics:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
