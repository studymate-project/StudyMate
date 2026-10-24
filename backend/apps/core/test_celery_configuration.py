from pathlib import Path

from django.test import SimpleTestCase

from backend.celery import app as celery_app


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class CeleryStartupConfigurationTests(SimpleTestCase):
    @staticmethod
    def read_entrypoint(name: str) -> str:
        return (BACKEND_ROOT / name).read_text(encoding="utf-8")

    def test_celery_app_discovers_the_existing_signup_email_task(self):
        self.assertIn(
            "apps.users.tasks.send_signup_verification_email_task",
            celery_app.tasks,
        )
        self.assertIn(
            "apps.notifications.tasks.ensure_question_answer_notification_task",
            celery_app.tasks,
        )
        self.assertIn(
            "apps.users.tasks.cleanup_expired_signup_verifications_task",
            celery_app.tasks,
        )

    def test_celery_has_bounded_time_limits_and_task_events_enabled(self):
        self.assertGreater(celery_app.conf.task_soft_time_limit, 0)
        self.assertGreater(celery_app.conf.task_time_limit, celery_app.conf.task_soft_time_limit)
        self.assertTrue(celery_app.conf.task_track_started)
        self.assertTrue(celery_app.conf.worker_send_task_events)
        self.assertTrue(celery_app.conf.task_reject_on_worker_lost)

    def test_delivery_tasks_use_late_acknowledgement_and_ignore_results(self):
        for task_name in (
            "apps.users.tasks.send_signup_verification_email_task",
            "apps.notifications.tasks.ensure_question_answer_notification_task",
            "apps.users.tasks.cleanup_expired_signup_verifications_task",
        ):
            with self.subTest(task=task_name):
                task = celery_app.tasks[task_name]
                self.assertTrue(task.acks_late)
                self.assertTrue(task.ignore_result)

    def test_no_periodic_schedule_is_configured(self):
        self.assertEqual(celery_app.conf.beat_schedule, {})

    def test_worker_entrypoint_uses_backend_app_and_explicit_runtime_options(self):
        worker = self.read_entrypoint("worker.sh")

        self.assertIn('SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)', worker)
        self.assertIn('cd "$SCRIPT_DIR"', worker)
        self.assertIn("exec python -m celery -A backend.celery worker", worker)
        self.assertIn('--loglevel="${CELERY_LOG_LEVEL:-INFO}"', worker)
        self.assertIn('--hostname="${CELERY_WORKER_NAME:-studymate@%h}"', worker)
        self.assertNotIn("manage.py migrate", worker)

    def test_web_entrypoint_migrates_before_starting_gunicorn(self):
        start = self.read_entrypoint("start.sh")

        self.assertIn('SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)', start)
        self.assertIn('cd "$SCRIPT_DIR"', start)
        self.assertIn("python manage.py migrate --noinput", start)
        self.assertIn("exec gunicorn backend.wsgi:application", start)
        self.assertNotIn("celery", start)

    def test_render_documentation_keeps_web_and_worker_services_separate(self):
        readme = (BACKEND_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("Render web service", readme)
        self.assertIn("Render background worker", readme)
        self.assertIn("sh start.sh", readme)
        self.assertIn("sh worker.sh", readme)
        for name in (
            "CELERY_BROKER_URL",
            "REDIS_URL",
            "DATABASE_URL",
            "EMAIL_BACKEND",
            "EMAIL_HOST",
        ):
            self.assertIn(name, readme)
