# addrlint

A command-line tool that checks plain-text address files for missing
fields and bad postal formats, and points at the exact line and column
that's wrong instead of just telling you "invalid address."

I keep addresses for a mailing list in a plain text file because a
spreadsheet is overkill and a database is worse. The problem with plain
text is that typos don't announce themselves — a five-digit ZIP that's
actually four digits, a state field with a full name instead of a code,
a block missing "city" entirely. This tool catches that before the file
goes anywhere near a mail merge.

## Format

An address file is a sequence of blocks separated by blank lines. Each
block is a set of `key: value` lines:

```
name: Jane Doe
street: 123 Main St
city: Springfield
region: IL
postal_code: 62704
country: US

name: John Smith
street: 456 Oak Ave
city: Chicago
region: XX
postal_code: 6060
```

Required fields for every block: `name`, `street`, `city`, `region`,
`postal_code`. `country` is optional and defaults to `US`. Lines
starting with `#` are treated as comments.

## Usage

```
$ addrlint addresses.txt
```

For the file above, the second block has two problems — an invalid
state code and a ZIP that's short a digit:

```
error: "XX" is not a recognized US state or territory code
  --> addresses.txt:11:9
  |
11 | region: XX
  |         ^^
  |
  = help: use a two-letter code, e.g. "IL" for Illinois

error: invalid US postal code "6060"
  --> addresses.txt:12:14
  |
12 | postal_code: 6060
  |              ^^^^
  |
  = help: expected 5 digits, optionally followed by "-" and 4 digits, e.g. "62704" or "62704-1234"

2 error(s) found in addresses.txt
```

Structural problems in the file itself — a missing colon, an empty
field name — are reported the same way, before any validation runs. If
line 4 of a file accidentally drops the colon:

```
error: expected "key: value" but found no colon
  --> other.txt:4:1
  |
4 | region IL
  | ^^^^^^^^^
```

A clean file prints a one-line summary and exits with status 0:

```
$ addrlint addresses.txt
addrlint: addresses.txt: 2 address block(s), no errors
```

## Installing

No dependencies beyond the Python standard library. Run it directly:

```
$ python -m addrlint.cli addresses.txt
```

or install it locally so `addrlint` is on your PATH:

```
$ pip install -e .
$ addrlint addresses.txt
```

## Status

Only US address validation exists right now (ZIP shape, state
abbreviation). Every country's postal rules are different enough that
adding one means actually reading that country's postal authority docs,
not guessing from a regex.

## Development

Tests use only the standard library:

```
$ python -m unittest discover
```

## License

MIT, see LICENSE.
