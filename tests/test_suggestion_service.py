import sqlite3
import unicodedata
import unittest
from unittest.mock import patch

import suggestion_service


class CheckinSuggestionSearchTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE members (
                id INTEGER PRIMARY KEY,
                ho_ten TEXT,
                so_dien_thoai TEXT,
                cccd TEXT
            )
        """)
        rows = [
            (f"Nguyễn Huy Đệm{i}", f"09000000{i:02d}", f"encrypted-{i}")
            for i in range(12)
        ]
        rows.extend([
            ("Lê Gia Huy", "0999999999", "encrypted-target"),
            ("Trần Ngọc Ánh", "0900000099", "encrypted-anh"),
            ("Nguyễn Văn Đạt", "0900000088", "encrypted-dat"),
        ])
        self.conn.executemany(
            "INSERT INTO members (ho_ten, so_dien_thoai, cccd) VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()

    def tearDown(self):
        try:
            self.conn.close()
        except sqlite3.ProgrammingError:
            pass

    def _search(self, query):
        with patch.object(
            suggestion_service, "get_connection", return_value=self.conn
        ), patch.object(
            suggestion_service, "decrypt_cccd", side_effect=lambda value: value
        ):
            return suggestion_service.get_checkin_suggestions(query)

    def test_given_name_only_is_found_even_after_more_than_ten_other_matches(self):
        suggestions = self._search("Huy")
        self.assertEqual(len(suggestions), 10)
        self.assertEqual(
            suggestions[0]["display"].split(" - SĐT:")[0],
            "Lê Gia Huy",
        )

    def test_lowercase_query_matches_accented_uppercase_given_name(self):
        suggestions = self._search("đạt")
        names = [item["display"].split(" - SĐT:")[0] for item in suggestions]
        self.assertIn("Nguyễn Văn Đạt", names)

    def test_unaccented_query_matches_accented_name(self):
        suggestions = self._search("anh")
        names = [item["display"].split(" - SĐT:")[0] for item in suggestions]
        self.assertIn("Trần Ngọc Ánh", names)

    def test_decomposed_unicode_query_matches_composed_database_name(self):
        query = unicodedata.normalize("NFD", "ĐẠT")
        suggestions = self._search(query)
        names = [item["display"].split(" - SĐT:")[0] for item in suggestions]
        self.assertIn("Nguyễn Văn Đạt", names)

    def test_partial_given_name_is_prioritized(self):
        suggestions = self._search("Hu")
        self.assertGreater(len(suggestions), 0)
        self.assertEqual(
            suggestions[0]["display"].split(" - SĐT:")[0],
            "Lê Gia Huy",
        )

    def test_blank_query_returns_no_results(self):
        self.assertEqual(self._search("   "), [])

    def test_connection_is_closed(self):
        self._search("Huy")
        with self.assertRaises(sqlite3.ProgrammingError):
            self.conn.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
