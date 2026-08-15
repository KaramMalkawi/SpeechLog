from django.core.management.base import BaseCommand

from apps.accounts.services import clear_django_access_for_non_superusers


class Command(BaseCommand):
    help = (
        "Clear is_staff and Django groups/user_permissions for all non-superusers. "
        "Product ACL uses User.role + DRF; only superusers keep Django admin access."
    )

    def handle(self, *args, **options):
        touched = clear_django_access_for_non_superusers()
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared Django access flags/permissions for non-superusers "
                f"({touched} updates)."
            )
        )
