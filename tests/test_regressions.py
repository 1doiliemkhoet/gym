import unittest
from unittest.mock import patch

import database
import body_metrics_service
import mail_service
import renew_member
import search_service


class _FakeCursor:
    def execute(self, *args, **kwargs):
        return None

    def fetchall(self):
        return []


class _FakeConnection:
    def __init__(self):
        self.closed = False

    def cursor(self):
        return _FakeCursor()

    def close(self):
        self.closed = True


class SecurityRegressionTests(unittest.TestCase):
    def test_cccd_encryption_fails_closed_without_key(self):
        with patch.object(database, "cipher_suite", None):
            with self.assertRaisesRegex(RuntimeError, "ENCRYPTION_KEY"):
                database.encrypt_cccd("123456789012")

    def test_blind_index_requires_explicit_pepper(self):
        with patch.object(database, "PEPPER", None):
            with self.assertRaisesRegex(RuntimeError, "DB_PEPPER"):
                database.generate_blind_index("123456789012")

    def test_lookup_audit_does_not_include_query_value(self):
        fake_connection = _FakeConnection()
        fake_cursor = fake_connection.cursor()
        fake_cursor.fetchall = lambda: []
        with patch.object(database, "PEPPER", "test-only-pepper"), \
             patch.object(search_service, "get_connection", return_value=fake_connection), \
             patch.object(search_service, "log_system_action") as log_action:
            result = search_service.search_member_logic("123456789012", search_type="cccd")
        self.assertEqual(result, (True, []))
        logged_text = log_action.call_args.args[0]
        self.assertNotIn("123456789012", logged_text)

    def test_invalid_expiry_date_is_rejected_before_database_access(self):
        with patch.object(search_service, "get_connection") as get_connection:
            success, message = search_service.update_member_info_logic(
                1, "Test Member", "0900000000", "2026-02-30"
            )
        self.assertFalse(success)
        self.assertIn("YYYY-MM-DD", message)
        get_connection.assert_not_called()


class DataValidationRegressionTests(unittest.TestCase):
    def test_zero_height_is_rejected_before_database_access(self):
        with patch.object(body_metrics_service, "get_connection") as get_connection:
            success, message = body_metrics_service.save_body_metrics(1, 0, 75)
        self.assertFalse(success)
        self.assertIn("lớn hơn 0", message)
        get_connection.assert_not_called()

    def test_non_finite_measurement_is_rejected(self):
        with patch.object(body_metrics_service, "get_connection") as get_connection:
            success, message = body_metrics_service.save_body_metrics(1, float("nan"), 75)
        self.assertFalse(success)
        self.assertIn("hữu hạn", message)
        get_connection.assert_not_called()

    def test_zero_month_renewal_is_rejected_before_database_access(self):
        with patch.object(renew_member, "get_connection") as get_connection:
            success, message = renew_member.renew_membership_logic("123456789012", 0, 100)
        self.assertFalse(success)
        self.assertIn("từ 1 đến 120", message)
        get_connection.assert_not_called()

    def test_non_finite_renewal_amount_is_rejected(self):
        with patch.object(renew_member, "get_connection") as get_connection:
            success, message = renew_member.renew_membership_logic("123456789012", 1, float("nan"))
        self.assertFalse(success)
        self.assertIn("không âm", message)
        get_connection.assert_not_called()

    def test_sqlite_metrics_connection_closes_without_mysql_api(self):
        fake_connection = _FakeConnection()
        with patch.object(body_metrics_service, "get_connection", return_value=fake_connection):
            result = body_metrics_service.get_metrics_history(1)
        self.assertEqual(result, [])
        self.assertTrue(fake_connection.closed)


class MailConfigurationRegressionTests(unittest.TestCase):
    def test_missing_smtp_config_does_not_break_import_or_trigger_network(self):
        with patch.object(mail_service, "SMTP_USER", ""), patch.object(mail_service, "SMTP_PASSWORD", None):
            self.assertIsNotNone(mail_service._smtp_configuration_error())
            self.assertFalse(mail_service.send_welcome_email_html(
                "member@example.test", "Test Member", "1 tháng", "01-01-2027"
            ))
            message = mail_service.auto_check_and_send_reminders()
            self.assertIn("SMTP_USER", message)

    def test_html_escape_encodes_untrusted_values(self):
        self.assertEqual(
            mail_service._html_escape('<script>alert("x")</script>'),
            "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;",
        )


if __name__ == "__main__":
    unittest.main()
