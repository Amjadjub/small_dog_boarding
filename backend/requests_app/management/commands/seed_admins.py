import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Creates or updates exactly two separately configured staff manager accounts."

    def handle(self, *args, **options):
        User = get_user_model()
        configured = []
        for number in (1, 2):
            username = os.getenv(f"ADMIN_{number}_USERNAME", "").strip()
            email = os.getenv(f"ADMIN_{number}_EMAIL", "").strip()
            password = os.getenv(f"ADMIN_{number}_PASSWORD", "")
            if not username or not password or password.startswith("replace-with"):
                raise CommandError(f"Set ADMIN_{number}_USERNAME and a real ADMIN_{number}_PASSWORD in backend/.env")
            try:
                validate_password(password)
            except ValidationError as exc:
                raise CommandError(f"ADMIN_{number}_PASSWORD: {'; '.join(exc.messages)}") from exc
            configured.append((username, email, password))
        if configured[0][0] == configured[1][0] or configured[0][2] == configured[1][2]:
            raise CommandError("The two manager accounts must use different usernames and passwords.")

        for username, email, password in configured:
            user, created = User.objects.get_or_create(username=username, defaults={"email": email})
            user.email = email
            user.is_staff = True
            user.is_active = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"{'Created' if created else 'Updated'} manager: {username}"))
