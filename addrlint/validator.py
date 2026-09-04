"""Structural and postal-format checks for a parsed AddressBlock.

US, Canadian, and UK addresses get format-specific checks (postal code
shape, and province/state code for US and CA). Anything with a "country"
field other than those is checked for the fields every address needs and
left alone otherwise, since postal formats vary too much by country to
guess at without real rules per country.
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

# Canada Post excludes D, F, I, O, Q, U from every letter position, and
# also excludes W and Z from the first position.
CA_POSTAL_RE = re.compile(
    r"^[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ] ?\d[ABCEGHJKLMNPRSTVWXYZ]\d$",
    re.IGNORECASE,
)

CA_PROVINCE_CODES = {
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT",
}

# Simplified version of the pattern gov.uk publishes for validating UK
# postcodes, including the one-off "GIR 0AA" (Girobank) postcode.
GB_POSTAL_RE = re.compile(
    r"^(GIR ?0AA|[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2})$",
    re.IGNORECASE,
)


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
    elif country == "CA":
        diagnostics.extend(_validate_ca(block, filename))
    elif country in ("GB", "UK"):
        diagnostics.extend(_validate_gb(block, filename))

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


def _validate_ca(block: AddressBlock, filename: str) -> List[Diagnostic]:
    diagnostics = []

    postal = block.get("postal_code")
    if postal and not CA_POSTAL_RE.match(postal.value):
        diagnostics.append(Diagnostic(
            severity="error",
            message=f'invalid Canadian postal code "{postal.value}"',
            filename=filename,
            line=postal.line,
            col=postal.value_col,
            length=len(postal.value),
            help='expected the form "A1A 1A1", e.g. "K1A 0B1"',
        ))

    region = block.get("region")
    if region and region.value.upper() not in CA_PROVINCE_CODES:
        diagnostics.append(Diagnostic(
            severity="error",
            message=f'"{region.value}" is not a recognized Canadian province or territory code',
            filename=filename,
            line=region.line,
            col=region.value_col,
            length=len(region.value),
            help='use a two-letter code, e.g. "ON" for Ontario',
        ))

    return diagnostics


def _validate_gb(block: AddressBlock, filename: str) -> List[Diagnostic]:
    diagnostics = []

    postal = block.get("postal_code")
    if postal and not GB_POSTAL_RE.match(postal.value):
        diagnostics.append(Diagnostic(
            severity="error",
            message=f'invalid UK postal code "{postal.value}"',
            filename=filename,
            line=postal.line,
            col=postal.value_col,
            length=len(postal.value),
            help='expected a UK postcode, e.g. "SW1A 1AA" or "EC1A 1BB"',
        ))

    return diagnostics
