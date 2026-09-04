import unittest

from addrlint.parser import parse
from addrlint.validator import validate_block


def block_from(text):
    return parse(text)[0]


VALID_US_BLOCK = (
    "name: Jane Doe\n"
    "street: 123 Main St\n"
    "city: Springfield\n"
    "region: IL\n"
    "postal_code: 62704"
)


class TestRequiredFields(unittest.TestCase):
    def test_reports_each_missing_field(self):
        block = block_from("name: Jane\nstreet: Main St")
        diags = validate_block(block, "f.txt")
        messages = [d.message for d in diags]
        self.assertTrue(any('"city"' in m for m in messages))
        self.assertTrue(any('"region"' in m for m in messages))
        self.assertTrue(any('"postal_code"' in m for m in messages))
        self.assertEqual(len(messages), 3)

    def test_missing_field_diagnostic_points_at_block_start(self):
        block = block_from("name: Jane\nstreet: Main St\ncity: X\nregion: IL")
        diags = validate_block(block, "f.txt")
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0].line, block.start_line)
        self.assertEqual(diags[0].col, 1)
        self.assertEqual(diags[0].severity, "error")

    def test_complete_block_has_no_missing_field_diagnostics(self):
        block = block_from(VALID_US_BLOCK)
        diags = validate_block(block, "f.txt")
        self.assertEqual(diags, [])


class TestUSPostalCode(unittest.TestCase):
    def test_valid_five_digit(self):
        block = block_from(VALID_US_BLOCK)
        diags = validate_block(block, "f.txt")
        self.assertEqual(diags, [])

    def test_valid_zip_plus4(self):
        text = VALID_US_BLOCK.replace("62704", "62704-1234")
        block = block_from(text)
        self.assertEqual(validate_block(block, "f.txt"), [])

    def test_invalid_zip_variants(self):
        invalid = ["1234", "123456", "62704-123", "62704-12345", "abcde", "62704-"]
        for zip_code in invalid:
            with self.subTest(zip_code=zip_code):
                text = VALID_US_BLOCK.replace("62704", zip_code)
                block = block_from(text)
                diags = validate_block(block, "f.txt")
                self.assertEqual(len(diags), 1)
                self.assertIn(zip_code, diags[0].message)

    def test_invalid_zip_diagnostic_points_at_value(self):
        block = block_from(VALID_US_BLOCK.replace("62704", "6060"))
        diags = validate_block(block, "f.txt")
        postal = block.get("postal_code")
        self.assertEqual(diags[0].line, postal.line)
        self.assertEqual(diags[0].col, postal.value_col)
        self.assertEqual(diags[0].length, len("6060"))


class TestUSRegion(unittest.TestCase):
    def test_valid_state_code_is_case_insensitive(self):
        block = block_from(VALID_US_BLOCK.replace("region: IL", "region: il"))
        self.assertEqual(validate_block(block, "f.txt"), [])

    def test_invalid_state_names_and_codes(self):
        for region in ["Illinois", "I", "ILL", "12", "XX"]:
            with self.subTest(region=region):
                text = VALID_US_BLOCK.replace("region: IL", f"region: {region}")
                block = block_from(text)
                diags = validate_block(block, "f.txt")
                self.assertEqual(len(diags), 1)
                self.assertIn(region, diags[0].message)


class TestCAPostalCode(unittest.TestCase):
    def valid_ca_block(self, postal_code="K1A 0B1", region="ON"):
        return block_from(
            "name: Jane Doe\n"
            "street: 123 Fake St\n"
            "city: Ottawa\n"
            f"region: {region}\n"
            f"postal_code: {postal_code}\n"
            "country: CA"
        )

    def test_valid_postal_code(self):
        self.assertEqual(validate_block(self.valid_ca_block(), "f.txt"), [])

    def test_valid_postal_code_without_space_is_case_insensitive(self):
        block = self.valid_ca_block(postal_code="k1a0b1")
        self.assertEqual(validate_block(block, "f.txt"), [])

    def test_invalid_postal_code_variants(self):
        invalid = ["K1A0B", "K1A 0B12", "12A 3B4", "DAA 1A1", "K1A  0B1"]
        for postal_code in invalid:
            with self.subTest(postal_code=postal_code):
                block = self.valid_ca_block(postal_code=postal_code)
                diags = validate_block(block, "f.txt")
                self.assertEqual(len(diags), 1)
                self.assertIn(postal_code, diags[0].message)

    def test_invalid_province_code(self):
        block = self.valid_ca_block(region="XX")
        diags = validate_block(block, "f.txt")
        self.assertEqual(len(diags), 1)
        self.assertIn("XX", diags[0].message)


class TestGBPostalCode(unittest.TestCase):
    def valid_gb_block(self, postal_code="SW1A 1AA", country="GB"):
        return block_from(
            "name: Jane Doe\n"
            "street: 10 Downing St\n"
            "city: London\n"
            "region: London\n"
            f"postal_code: {postal_code}\n"
            f"country: {country}"
        )

    def test_valid_postal_code(self):
        self.assertEqual(validate_block(self.valid_gb_block(), "f.txt"), [])

    def test_uk_is_accepted_as_alias_for_gb(self):
        block = self.valid_gb_block(country="uk")
        self.assertEqual(validate_block(block, "f.txt"), [])

    def test_valid_short_postal_code(self):
        block = self.valid_gb_block(postal_code="EC1A 1BB")
        self.assertEqual(validate_block(block, "f.txt"), [])

    def test_girobank_postal_code(self):
        block = self.valid_gb_block(postal_code="GIR 0AA")
        self.assertEqual(validate_block(block, "f.txt"), [])

    def test_invalid_postal_code_variants(self):
        invalid = ["SW1A", "1AA SW1", "SW1A 1A", "12345"]
        for postal_code in invalid:
            with self.subTest(postal_code=postal_code):
                block = self.valid_gb_block(postal_code=postal_code)
                diags = validate_block(block, "f.txt")
                self.assertEqual(len(diags), 1)
                self.assertIn(postal_code, diags[0].message)


class TestOtherCountry(unittest.TestCase):
    def test_unhandled_country_skips_postal_and_region_checks(self):
        text = (
            "name: Jane Doe\n"
            "street: 12 Rue de Paris\n"
            "city: Paris\n"
            "region: IDF\n"
            "postal_code: 75001\n"
            "country: FR"
        )
        block = block_from(text)
        self.assertEqual(validate_block(block, "f.txt"), [])

    def test_country_is_case_insensitive(self):
        text = VALID_US_BLOCK.replace("62704", "1234") + "\ncountry: us"
        block = block_from(text)
        diags = validate_block(block, "f.txt")
        self.assertEqual(len(diags), 1)
        self.assertIn("1234", diags[0].message)

    def test_missing_fields_still_checked_for_non_us_country(self):
        text = "name: Jane Doe\nstreet: 123 Fake St\ncountry: CA"
        block = block_from(text)
        diags = validate_block(block, "f.txt")
        messages = [d.message for d in diags]
        self.assertTrue(any('"city"' in m for m in messages))
        self.assertTrue(any('"region"' in m for m in messages))
        self.assertTrue(any('"postal_code"' in m for m in messages))


if __name__ == "__main__":
    unittest.main()
