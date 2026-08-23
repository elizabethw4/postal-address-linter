"""Structural and postal-format checks for a parsed AddressBlock.

Only US addresses are validated for now (ZIP code shape and state
abbreviation). Anything with a "country" field other than US is checked
for the fields every address needs and left alone otherwise, since postal
formats vary too much by country to guess at without real rules per
country.
"""

import re
from typing import List

from .parser import AddressBlock, Diagnostic

REQUIRED_FIELDS = ["name", "street", "city", "region", "postal_code"]

US_ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC", "PR", "VI", "GU", "AS", "MP",
}


def validate_block(block: AddressBlock, filename: str) -> List[Diagnostic]:
    diagnostics = []

    for name in REQUIRED_FIELDS:
        if not block.has(name):
            diagnostics.append(Diagnostic(
                severity="error",
                message=f'address is missing required field "{name}"',
                filename=filename,
                line=block.start_line,
                col=1,
                length=1,
                help=f'add a line like "{name}: ..." to this address block',
            ))

    country_field = block.get("country")
    country = country_field.value.upper() if country_field else "US"

    if country == "US":
        diagnostics.extend(_validate_us(block, filename))

    return diagnostics


def _validate_us(block: AddressBlock, filename: str) -> List[Diagnostic]:
    diagnostics = []

    postal = block.get("postal_code")
    if postal and not US_ZIP_RE.match(postal.value):
        diagnostics.append(Diagnostic(
            severity="error",
            message=f'invalid US postal code "{postal.value}"',
            filename=filename,
            line=postal.line,
            col=postal.value_col,
            length=len(postal.value),
            help='expected 5 digits, optionally followed by "-" and 4 digits, '
                 'e.g. "62704" or "62704-1234"',
        ))

    region = block.get("region")
    if region and region.value.upper() not in US_STATE_CODES:
        diagnostics.append(Diagnostic(
            severity="error",
            message=f'"{region.value}" is not a recognized US state or territory code',
            filename=filename,
            line=region.line,
            col=region.value_col,
            length=len(region.value),
            help='use a two-letter code, e.g. "IL" for Illinois',
        ))

    return diagnostics
