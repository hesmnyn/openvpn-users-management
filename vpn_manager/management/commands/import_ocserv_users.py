import os
import sqlite3
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from vpn_manager.models import VPNUser

class Command(BaseCommand):
    help = (
        "Import or update VPNUser records from a legacy ocserv SQLite database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-path',
            help='Path to the legacy SQLite database file',
            required=True,
        )

    def handle(self, *args, **options):
        db_path = options['db_path']
        # Fixed date format for expire_date field
        date_fmt = '%Y-%m-%d'

        if not os.path.exists(db_path):
            self.stderr.write(
                self.style.ERROR(f"Database not found: {db_path}")
            )
            return

        # Connect to legacy SQLite
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            'SELECT username, password, active, expire_date FROM app_ocservuser'
        )

        count = 0
        for row in cur.fetchall():
            username = row['username']
            pw = row['password'] or ''
            is_active = bool(row['active'])
            expire_str = row['expire_date']  # e.g. '2029-04-30'

            # Parse the expire_date into a date object
            if expire_str:
                try:
                    exp_date = datetime.strptime(expire_str, date_fmt).date()
                except ValueError:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Unable to parse date '{expire_str}' for {username}, using today"
                        )
                    )
                    exp_date = timezone.localdate()
            else:
                exp_date = timezone.localdate()

            # Create or update the VPNUser
            VPNUser.objects.update_or_create(
                username=username,
                defaults={
                    'openvpn_password': pw,
                    'is_active': is_active,
                    'expiry_date': exp_date,
                }
            )
            self.stdout.write(
                self.style.NOTICE(
                    f"Imported/updated {username} VPNUser from DB"
                )
            )   
            count += 1

        conn.close()
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported/updated {count} VPNUser(s) from {db_path}"
            )
        )