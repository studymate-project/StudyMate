"""Show safe, lightweight Celery worker and queue status."""

import json
from datetime import datetime, timezone

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.celery import app as celery_app


def _task_count(worker_tasks: dict) -> int:
    return sum(len(tasks or ()) for tasks in worker_tasks.values())


def _parse_eta(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None


def _oldest_scheduled_age_seconds(scheduled: dict) -> float | None:
    now = datetime.now(timezone.utc)
    ages = []
    for worker_tasks in scheduled.values():
        for item in worker_tasks or ():
            request = item.get("request", {})
            eta = _parse_eta(item.get("eta") or request.get("eta"))
            if eta is not None:
                ages.append(max(0.0, (now - eta).total_seconds()))
    return round(max(ages), 2) if ages else None


def _broker_message_count(queue: str) -> int:
    with celery_app.connection_for_read() as connection:
        channel = connection.channel()
        try:
            declaration = channel.queue_declare(queue=queue, passive=True)
            return int(getattr(declaration, "message_count", 0))
        finally:
            channel.close()


class Command(BaseCommand):
    help = "Report Celery worker state and the configured broker queue depth."

    def add_arguments(self, parser):
        parser.add_argument(
            "--queue",
            default=getattr(settings, "CELERY_TASK_DEFAULT_QUEUE", "celery"),
            help="Broker queue to inspect (default: the configured Celery queue).",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=2.0,
            help="Worker inspection timeout in seconds.",
        )
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args, **options):
        queue = options["queue"]
        try:
            inspector = celery_app.control.inspect(timeout=options["timeout"])
            stats = inspector.stats() or {}
            active = inspector.active() or {}
            reserved = inspector.reserved() or {}
            scheduled = inspector.scheduled() or {}
            broker_messages = _broker_message_count(queue)
        except Exception as exc:
            raise CommandError(
                f"Celery status unavailable (failure_type={type(exc).__name__})."
            ) from None

        report = {
            "queue": queue,
            "workers": len(stats),
            "broker_message_count": broker_messages,
            "active_tasks": _task_count(active),
            "reserved_tasks": _task_count(reserved),
            "scheduled_tasks": _task_count(scheduled),
            "oldest_scheduled_task_age_seconds": _oldest_scheduled_age_seconds(scheduled),
            # Generic Celery inspection does not expose enqueue timestamps for
            # messages still waiting in the broker queue.
            "oldest_pending_task_age_seconds": None,
        }

        if options["as_json"]:
            self.stdout.write(json.dumps(report, sort_keys=True))
            return

        for key, value in report.items():
            self.stdout.write(f"{key}={value}")
        self.stdout.write(
            "oldest_pending_task_age_note=unavailable from generic Celery inspection; "
            "scheduled-task age is reported separately"
        )
