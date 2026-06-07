import unittest

from closer_app.utils import is_placeholder_url


class UtilsTests(unittest.TestCase):
    def test_placeholder_urls_are_detected(self):
        self.assertTrue(is_placeholder_url("https://example-nurse-coach.com"))
        self.assertTrue(is_placeholder_url("https://example.com/path"))
        self.assertTrue(is_placeholder_url("https://demo.invalid"))
        self.assertTrue(is_placeholder_url("https://nursecoach.example"))

    def test_real_urls_are_not_placeholder_urls(self):
        self.assertFalse(is_placeholder_url("https://www.instagram.com/nurse_preneur/"))
        self.assertFalse(is_placeholder_url("https://nursepreneurs.com"))
        self.assertFalse(is_placeholder_url(""))


if __name__ == "__main__":
    unittest.main()
