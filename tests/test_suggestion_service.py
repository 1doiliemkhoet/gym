import unittest
from unittest.mock import patch

import suggestion_service


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    def execute(self, statement):
        self.statement = statement

    def fetchall(self):
        return self.rows


class _FakeConnection:
    def __init__(self, rows):
        self.fake_cursor = _FakeCursor(rows)
        self.closed = False

    def cursor(self):
        return self.fake_cursor

    def close(self):
        self.closed = True


class CheckinSuggestionSearchTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {
                "ho_ten": "Nguyễn Văn Đạt",
                "so_dien_thoai": "0900000001",
                "cccd": "encrypted-dat",
            },
            {
                "ho_ten": "Trần Ngọc Ánh",
                "so_dien_thoai": "0900000002",
                "cccd": "encrypted-anh",
            },
            {
                "ho_ten": "Lê Gia Huy",
                "so_dien_thoai": "0900000003",
                "cccd": "encrypted-huy",
            },
        ]
        self.connection = _FakeConnection(self.rows)

    def _search(self, query):
        with patch.object(
            suggestion_service, "get_connection", return_value=self.connection
        ), patch.object(
            suggestion_service,
            "decrypt_cccd",
            side_effect=lambda value: value.replace("encrypted-", ""),
        ):
            return suggestion_service.get_checkin_suggestions(query)

    def test_search_by_given_name_only(self):
        suggestions = self._search("Huy")
        self.assertEqual(len(suggestions), 1)
        self.assertIn("Lê Gia Huy", suggestions[0]["display"])
        self.assertEqual(suggestions[0]["real_value"], "huy")

    def test_vietnamese_diacritic_case_is_ignored(self):
        suggestions = self._search("đạt")
        self.assertEqual(len(suggestions), 1)
        self.assertIn("Nguyễn Văn Đạt", suggestions[0]["display"])

    def test_search_without_diacritics_finds_vietnamese_name(self):
        suggestions = self._search("anh")
        self.assertEqual(len(suggestions), 1)
        self.assertIn("Trần Ngọc Ánh", suggestions[0]["display"])

    def test_search_matches_middle_name_or_partial_text(self):
        suggestions = self._search("vAn")
        self.assertEqual(len(suggestions), 1)
        self.assertIn("Nguyễn Văn Đạt", suggestions[0]["display"])

    def test_blank_query_returns_no_suggestions(self):
        self.assertEqual(self._search("   "), [])

    def test_connection_is_closed(self):
        self._search("Huy")
        self.assertTrue(self.connection.closed)


if __name__ == "__main__":
    unittest.main()
