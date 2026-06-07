from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LANGCHAIN_ROOT = ROOT / "langchain_core"
if str(LANGCHAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(LANGCHAIN_ROOT))

from mia_core.time_utils import build_current_date_response


class TestTimeUtils(unittest.TestCase):
    def test_build_current_date_response_formats_vietnamese_date(self) -> None:
        response = build_current_date_response(
            "Asia/Ho_Chi_Minh",
            now=datetime(2026, 6, 7, 9, 30, 0),
        )

        self.assertEqual(response["text"], "Hôm nay là Chủ Nhật, ngày 7 tháng 6 năm 2026.")
        self.assertEqual(response["trace"]["timezone"], "Asia/Ho_Chi_Minh")
        self.assertEqual(response["trace"]["weekday"], "Chủ Nhật")
        self.assertEqual(response["trace"]["weekday_index"], 6)

    def test_build_current_date_response_falls_back_to_utc_for_invalid_timezone(self) -> None:
        response = build_current_date_response(
            "Invalid/Timezone",
            now=datetime(2026, 6, 7, 2, 0, 0),
        )

        self.assertEqual(response["trace"]["timezone"], "UTC")
        self.assertIn("2026", response["text"])
