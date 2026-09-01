import unittest

from addrlint.parser import ParseError, parse


class TestParseBlocks(unittest.TestCase):
    def test_single_block(self):
        text = (
            "name: Jane Doe\n"
            "street: 123 Main St\n"
            "city: Springfield\n"
            "region: IL\n"
            "postal_code: 62704"
        )
        blocks = parse(text)
        self.assertEqual(len(blocks), 1)

        block = blocks[0]
        self.assertEqual(block.start_line, 1)
        self.assertEqual(len(block.fields), 5)

        name = block.get("name")
        self.assertEqual(name.value, "Jane Doe")
        self.assertEqual(name.line, 1)
        self.assertEqual(name.key_col, 1)
        self.assertEqual(name.value_col, 7)

        street = block.get("street")
        self.assertEqual(street.value, "123 Main St")
        self.assertEqual(street.value_col, 9)

    def test_multiple_blocks_separated_by_blank_line(self):
        text = (
            "name: A\n"
            "street: S\n"
            "city: C\n"
            "region: IL\n"
            "postal_code: 60000\n"
            "\n"
            "name: B\n"
            "street: S2\n"
            "city: C2\n"
            "region: CA\n"
            "postal_code: 90000"
        )
        blocks = parse(text)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].start_line, 1)
        self.assertEqual(blocks[1].start_line, 7)

    def test_whitespace_only_line_separates_blocks(self):
        text = "name: A\nstreet: S\ncity: C\nregion: IL\npostal_code: 1\n   \nname: B\nstreet: S2\ncity: C2\nregion: IL\npostal_code: 2"
        blocks = parse(text)
        self.assertEqual(len(blocks), 2)

    def test_comment_line_is_skipped_but_does_not_break_block(self):
        text = "name: A\n# a note about this address\nstreet: S\ncity: C\nregion: IL\npostal_code: 60000"
        blocks = parse(text)
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        self.assertEqual(len(block.fields), 5)
        self.assertEqual(block.get("street").line, 3)

    def test_leading_whitespace_on_key_affects_key_col(self):
        blocks = parse("  city: Springfield")
        field = blocks[0].get("city")
        self.assertEqual(field.key_col, 3)

    def test_value_containing_colon_is_preserved_whole(self):
        blocks = parse("name: A\nstreet: S\ncity: C\nregion: IL\npostal_code: 1\nnote: http://example.com:8080")
        self.assertEqual(blocks[0].get("note").value, "http://example.com:8080")

    def test_no_trailing_blank_line_still_closes_final_block(self):
        blocks = parse("name: A\nstreet: S\ncity: C\nregion: IL\npostal_code: 1")
        self.assertEqual(len(blocks), 1)

    def test_empty_text_produces_no_blocks(self):
        self.assertEqual(parse(""), [])


class TestParseErrors(unittest.TestCase):
    def test_missing_colon(self):
        with self.assertRaises(ParseError) as ctx:
            parse("name: A\nregion IL")
        err = ctx.exception
        self.assertEqual(err.line, 2)
        self.assertEqual(err.col, 1)
        self.assertEqual(err.length, len("region IL"))

    def test_missing_colon_with_leading_whitespace(self):
        with self.assertRaises(ParseError) as ctx:
            parse("  region IL")
        err = ctx.exception
        self.assertEqual(err.col, 3)

    def test_empty_field_name(self):
        with self.assertRaises(ParseError) as ctx:
            parse(": value")
        err = ctx.exception
        self.assertEqual(err.line, 1)
        self.assertEqual(err.col, 1)
        self.assertEqual(err.length, 1)

    def test_field_with_no_value(self):
        with self.assertRaises(ParseError) as ctx:
            parse("city:")
        err = ctx.exception
        self.assertIn('"city"', err.message)
        self.assertEqual(err.line, 1)
        self.assertEqual(err.col, 1)
        self.assertEqual(err.length, len("city"))

    def test_field_with_only_whitespace_value(self):
        with self.assertRaises(ParseError):
            parse("city:   ")

    def test_error_on_second_block_reports_correct_line(self):
        text = "name: A\nstreet: S\ncity: C\nregion: IL\npostal_code: 1\n\nname: B\nregion IL"
        with self.assertRaises(ParseError) as ctx:
            parse(text)
        self.assertEqual(ctx.exception.line, 8)


if __name__ == "__main__":
    unittest.main()
