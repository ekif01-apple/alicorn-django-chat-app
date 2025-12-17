from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Seed dummy users for local development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of users to create (default: 5)",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="pass1234",
            help="Default password for created users",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        password = options["password"]

        created = 0

        for i in range(1, count + 1):
            username = f"user{i}"

            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f"User '{username}' already exists, skipped")
                )
                continue

            User.objects.create_user(
                username=username,
                password=password,
            )
            created += 1

            self.stdout.write(self.style.SUCCESS(f"Created user: {username}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created} user(s) created. Default password: '{password}'"
            )
        )
