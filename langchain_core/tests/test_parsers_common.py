import unittest
from mia_core.parsers.common import (
    normalize_query_text,
    keyword_matches,
    any_keyword_matches,
    looks_multi_step,
    is_soft_followup_only,
    strip_prefixes,
    strip_conversational_fillers,
)

class TestParsersCommon(unittest.TestCase):
    def test_normalize_query_text(self):
        self.assertEqual(normalize_query_text("Đại học Quốc gia"), "dai hoc quoc gia")
        self.assertEqual(normalize_query_text("MIA-core 2026"), "mia-core 2026")
        self.assertEqual(normalize_query_text(""), "")

    def test_keyword_matches(self):
        self.assertTrue(keyword_matches("toi muon xem lich", "lich"))
        self.assertTrue(keyword_matches("check mail", "mail"))
        self.assertFalse(keyword_matches("gmail", "mail")) # matches word boundaries
        self.assertTrue(keyword_matches("google drive folder", "google drive"))

    def test_any_keyword_matches(self):
        self.assertTrue(any_keyword_matches("xem tin tuc", ("news", "tin tuc")))
        self.assertFalse(any_keyword_matches("thoi tiet", ("gold", "vang")))

    def test_looks_multi_step(self):
        self.assertTrue(looks_multi_step("xem lich xong thi gui mail"))
        self.assertTrue(looks_multi_step("xem tin tuc sau do tao note"))
        self.assertFalse(looks_multi_step("gui mail cho anh A"))

    def test_is_soft_followup_only(self):
        self.assertTrue(is_soft_followup_only("roi giup minh voi"))
        self.assertFalse(is_soft_followup_only("roi sau do lam cai khac"))

    def test_strip_prefixes(self):
        prefixes = ("mia oi", "mia ơi", "chào mia")
        self.assertEqual(strip_prefixes("mia ơi check mail", prefixes), "check mail")
        self.assertEqual(strip_prefixes("chao mia gui tin", prefixes), "gui tin")
        # Wait, if prefixes are ("mia oi", "mia ơi"):
        self.assertEqual(strip_prefixes("mia oi check mail", prefixes), "check mail")

    def test_strip_conversational_fillers(self):
        self.assertEqual(strip_conversational_fillers("giúp mình xem lịch nhé"), "xem lịch")
        self.assertEqual(strip_conversational_fillers("hãy gửi mail đi"), "gửi mail")

if __name__ == "__main__":
    unittest.main()
