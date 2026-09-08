"""Parser for the addrlint address block format, plus the diagnostic type
both the parser and the validator use to report problems.

An address file is a sequence of address blocks separated by one or more
blank lines. Each block is a sequence of "key: value" lines, e.g.:

    name: Jane Doe
    street: 123 Main St
    city: Springfield
    region: IL
    postal_code: 62704

Every field remembers where it came from (line and column of both the key
and the value) so that later validation can point at the exact spot that's
wrong instead of just naming the block.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Field:
    key: str
    value: str
    line: int
    key_col: int
    value_col: int


@dataclass
class AddressBlock:
    fields: List[Field]
    start_line: int

    def get(self, key: str) -> Optional[Field]:
        for f in self.fields:
            if f.key == key:
                return f
        return None

    def has(self, key: str) -> bool:
        return self.get(key) is not None


class ParseError(Exception):
    def __init__(self, message: str, line: int, col: int, length: int = 1):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.length = length


@dataclass
class Diagnostic:
    severity: str  # "error" or "warning"
    message: str
    filename: str
    line: int
    col: int
    length: int = 1
    help: Optional[str] = None

    def render(self, source_lines: List[str]) -> str:
        gutter_width = len(str(self.line))
        pad = " " * gutter_width

        lines = [f"{self.severity}: {self.message}"]
        lines.append(f"{pad}--> {self.filename}:{self.line}:{self.col}")
        lines.append(f"{pad} |")

        source = source_lines[self.line - 1] if 1 <= self.line <= len(source_lines) else ""
        lines.append(f"{self.line} | {source}")

        caret = " " * (self.col - 1) + "^" * max(self.length, 1)
        lines.append(f"{pad} | {caret}")

        if self.help:
            lines.append(f"{pad} |")
            lines.append(f"{pad} = help: {self.help}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "col": self.col,
            "length": self.length,
            "help": self.help,
        }


def parse(text: str) -> List[AddressBlock]:
    """Parse address file contents into a list of AddressBlock.

    Raises ParseError on the first malformed line (missing colon, empty
    key, or a key with no value).
    """
    blocks: List[AddressBlock] = []
    current_fields: List[Field] = []
    block_start = None

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()

        if not stripped:
            if current_fields:
                blocks.append(AddressBlock(fields=current_fields, start_line=block_start))
                current_fields = []
                block_start = None
            continue

        if stripped.startswith("#"):
            continue

        colon = raw_line.find(":")
        if colon == -1:
            leading_ws = len(raw_line) - len(raw_line.lstrip())
            raise ParseError(
                'expected "key: value" but found no colon',
                line=lineno,
                col=leading_ws + 1,
                length=len(stripped),
            )

        key_part = raw_line[:colon]
        key = key_part.strip()
        key_col = len(key_part) - len(key_part.lstrip()) + 1

        if not key:
            raise ParseError(
                "empty field name before ':'",
                line=lineno,
                col=1,
                length=colon + 1,
            )

        value_part = raw_line[colon + 1:]
        value = value_part.strip()
        value_leading_ws = len(value_part) - len(value_part.lstrip())
        value_col = colon + 1 + value_leading_ws + 1

        if not value:
            raise ParseError(
                f'field "{key}" has no value',
                line=lineno,
                col=key_col,
                length=len(key),
            )

        if block_start is None:
            block_start = lineno

        current_fields.append(
            Field(key=key, value=value, line=lineno, key_col=key_col, value_col=value_col)
        )

    if current_fields:
        blocks.append(AddressBlock(fields=current_fields, start_line=block_start))

    return blocks
