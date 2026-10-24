import json
from datetime import datetime, timedelta, timezone
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase


class CeleryStatusCommandTests(SimpleTestCase):
    @staticmethod
    def broker_context(message_count=7):
        channel = MagicMock()
        channel.queue_declare.return_value = SimpleNamespace(message_count=message_count)
        connection = MagicMock()
        connection.channel.return_value = channel
        context = MagicMock()
        context.__enter__.return_value = connection
        return context, channel

    @staticmethod
    def inspector():
        now = datetime.now(timezone.utc)
        inspector = MagicMock()
        inspector.stats.return_value = {"worker-a": {}}
        inspector.active.return_value = {"worker-a": [{"id": "active-id"}]}
        inspector.reserved.return_value = {"worker-a": [{"id": "reserved-id"}]}
        inspector.scheduled.return_value = {
            "worker-a": [
                {"request": {"eta": (now - timedelta(seconds=90)).isoformat()}}
            ]
        }
        return inspector

    @patch("apps.core.management.commands.celery_status.celery_app.connection_for_read")
    @patch("apps.core.management.commands.celery_status.celery_app.control.inspect")
    def test_reports_worker_queue_and_scheduled_visibility(self, inspect_mock, connection_mock):
        inspect_mock.return_value = self.inspector()
        context, channel = self.broker_context()
        connection_mock.return_value = context
        output = StringIO()

        call_command("celery_status", "--json", stdout=output)

        report = json.loads(output.getvalue())
        self.assertEqual(report["workers"], 1)
        self.assertEqual(report["broker_message_count"], 7)
        self.assertEqual(report["active_tasks"], 1)
        self.assertEqual(report["reserved_tasks"], 1)
        self.assertEqual(report["scheduled_tasks"], 1)
        self.assertGreater(report["oldest_scheduled_task_age_seconds"], 0)
        self.assertIsNone(report["oldest_pending_task_age_seconds"])
        channel.queue_declare.assert_called_once_with(queue="celery", passive=True)

    @patch(
        "apps.core.management.commands.celery_status.celery_app.control.inspect",
        side_effect=RuntimeError("broker password must not be exposed"),
    )
    def test_broker_failure_is_safe_and_does_not_print_exception_text(self, inspect_mock):
        with self.assertRaises(CommandError) as caught:
            call_command("celery_status", stdout=StringIO())

        self.assertIn("failure_type=RuntimeError", str(caught.exception))
        self.assertNotIn("broker password", str(caught.exception))
