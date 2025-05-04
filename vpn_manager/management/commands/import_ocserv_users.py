import os
import sqlite3
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from vpn_manager.models import VPNUser

class Command(BaseCommand):
    help = (
        "Fast import/update of VPNUser records from a legacy ocserv SQLite DB."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-path',
            help='Path to the legacy SQLite database file',
            required=True,
        )

    def handle(self, *args, **options):
        db_path = options['db_path']
        date_fmt = '%Y-%m-%d'

        if not os.path.exists(db_path):
            self.stderr.write(self.style.ERROR(f"DB not found: {db_path}"))
            return

        # Step 1: Read legacy rows
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT username, password, active, expire_date FROM app_ocservuser')

        rows = list(cur)  # load all rows; SQLite fetch is fast in C
        conn.close()

        # Step 2: Map existing users
        existing = {
            u.username: u
            for u in VPNUser.objects.in_bulk(field_name='username').values()
        }

        to_create = []
        to_update = []

        # Step 3: Build objects
        for row in rows:
            uname = row['username']
            pw = row['password'] or ''
            active = bool(row['active'])
            exp_str = row['expire_date']

            # Parse expiry date into date
            try:
                exp_date = datetime.strptime(exp_str, date_fmt).date() if exp_str else timezone.localdate()
            except ValueError:
                exp_date = timezone.localdate()

            if uname in existing:
                usr = existing[uname]
                usr.openvpn_password = pw
                usr.is_active = active
                usr.expiry_date = exp_date
                to_update.append(usr)
            else:
                to_create.append(
                    VPNUser(
                        username=uname,
                        openvpn_password=pw,
                        is_active=active,
                        expiry_date=exp_date,
                    )
                )

        # Step 4: Bulk write inside a transaction
        with transaction.atomic():
            if to_update:
                VPNUser.objects.bulk_update(
                    to_update,
                    ['openvpn_password', 'is_active', 'expiry_date'],
                    batch_size=500
                )
            if to_create:
                VPNUser.objects.bulk_create(
                    to_create,
                    batch_size=500
                )

        total = len(to_update) + len(to_create)
        self.stdout.write(self.style.SUCCESS(f"Imported/updated {total} VPNUser(s) (created={len(to_create)}, updated={len(to_update)})"))