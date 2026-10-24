"""Run the opt-in retention cleanup without contacting external services."""

import json

from django.core.management.base import BaseCommand

from apps.users.retention import cleanup_expired_signup_verifications


class Command(BaseCommand):
    help = "Inspect or execute the configured, bounded retention cleanup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Delete eligible records; without this flag the command is a dry run.",
        )

    def handle(self, *args, **options):
        report = cleanup_expired_signup_verifications(dry_run=not options["execute"])
        self.stdout.write(json.dumps(report, sort_keys=True))
