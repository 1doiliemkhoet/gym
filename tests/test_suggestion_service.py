import unittest
from unittest.mock import patch

import suggestion_service


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.statement = ""
        self.parameters = None

    def execute(self, statement, parameters=None):
        self.statement = statement
        self.parameters = parameters

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


class CheckinSuggestionRankingTests(unittest.TestCase):
    def setUp(self):
        # Hàng loạt bản ghi khớp "Huy" ở họ/tên đệm đứng trước hội viên
        # có tên gọi là Huy. Kết quả cần tìm phải được ưu tiên lên đầu.
        self.rows = [
            {
                "ho_ten": f"Nguyễn Huy Đệm{i}",
                "so_dien_thoai": f"09000000{i:02d}",
                "cccd": f"encrypted-{i}",
            }
            for i in range(12)
        ]
        self.rows.append({
            "ho_ten": "Lê Gia Huy",
            "so_dien_thoai": "0999999999",
            "cccd": "encrypted-target",
        })
        self.connection = _FakeConnection(self.rows)

    def _search(self, query):
        with patch.object(
            suggestion_service, "get_connection", return_value=self.connection
        ), patch.object(
            suggestion_service, "decrypt_cccd", side_effect=lambda value: value
        ):
            return suggestion_service.get_checkin_suggestions(query)

    def test_exact_given_name_is_prioritized_over_earlier_substring_matches(self):
        suggestions = self._search("Huy")
        self.assertEqual(len(suggestions), 10)
        self.assertEqual(
            suggestions[0]["display"].split(" - SĐT:")[0],
            "Lê Gia Huy",
        )

    def test_partial_given_name_is_prioritized(self):
        suggestions = self._search("Hu")
        self.assertGreater(len(suggestions), 0)
        self.assertEqual(
            suggestions[0]["display"].split(" - SĐT:")[0],
            "Lê Gia Huy",
        )

    def test_sql_query_does_not_cut_candidates_before_ranking(self):
        self._search("Huy")
        self.assertNotIn("LIMIT 10", self.connection.fake_cursor.statement.upper())

    def test_blank_query_returns_no_results(self):
        self.assertEqual(self._search("   "), [])

    def test_connection_is_closed(self):
        self._search("Huy")
        self.assertTrue(self.connection.closed)


if __name__ == "__main__":
    unittest.main()
