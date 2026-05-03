import unittest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException


class TestGetLogsForDateEndpoint(unittest.TestCase):
    @patch("api.database")
    def test_returns_logs_for_date(self, mock_db):
        from api import read_logs_for_date

        mock_db.get_logs_for_date.return_value = [
            {"id": 1, "timestamp": "2026-03-10T08:00:00"},
            {"id": 2, "timestamp": "2026-03-10T14:30:00"},
        ]
        result = read_logs_for_date("2026-03-10")
        mock_db.get_logs_for_date.assert_called_once_with("2026-03-10")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)


class TestDeleteLogEndpoint(unittest.TestCase):
    @patch("api.database")
    def test_success(self, mock_db):
        from api import delete_log

        mock_db.delete_log.return_value = True
        result = delete_log(1)
        mock_db.delete_log.assert_called_once_with(1)
        self.assertEqual(result["status"], "success")

    @patch("api.database")
    def test_not_found(self, mock_db):
        from api import delete_log

        mock_db.delete_log.return_value = False
        with self.assertRaises(HTTPException) as ctx:
            delete_log(99999)
        self.assertEqual(ctx.exception.status_code, 404)


class TestAddLogWithTimestamp(unittest.TestCase):
    @patch("api.database")
    def test_with_timestamp(self, mock_db):
        from api import add_log, LogRequest

        mock_db.add_log.return_value = None
        body = LogRequest(timestamp="2026-03-10T12:00:00")
        result = add_log(body)
        mock_db.add_log.assert_called_once_with("2026-03-10T12:00:00")
        self.assertEqual(result["status"], "success")

    @patch("api.database")
    def test_without_timestamp(self, mock_db):
        from api import add_log

        mock_db.add_log.return_value = None
        result = add_log(None)
        mock_db.add_log.assert_called_once_with()
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
